"""
The audit trail for "what did the agent actually do about this case".

Hooks into LangChain's own callback system (`on_tool_start` / `on_tool_end` /
`on_tool_error`) instead of instrumenting each tool by hand - so every tool
call is recorded generically, including the ~40 Razorpay MCP tools loaded
dynamically per business (`src.agent.mcp`) that we don't author and can't
easily edit. Nothing to update here (or in any tool) when a new tool shows up.
"""

import typing
import uuid

import loguru
from langchain_core.callbacks import AsyncCallbackHandler

from src.repository.crud.case_action import CaseActionCRUDRepository
from src.workers.runtime import worker_session


class CaseActionAuditHandler(AsyncCallbackHandler):
    """Pass one of these (bound to a `case_id`) via `config={"callbacks": [...]}`
    on an `agent.ainvoke(...)` call to persist a `CaseAction` row per tool call."""

    def __init__(self, case_id: int) -> None:
        self._case_id = case_id
        # tool run_id -> {tool_name, tool_input}, filled in on_tool_start and
        # consumed on_tool_end/on_tool_error (which don't repeat the input).
        self._pending: dict[uuid.UUID, dict[str, typing.Any]] = {}

    async def on_tool_start(
        self,
        serialized: dict[str, typing.Any],
        input_str: str,
        *,
        run_id: uuid.UUID,
        inputs: dict[str, typing.Any] | None = None,
        **kwargs: typing.Any,
    ) -> None:
        self._pending[run_id] = {
            "tool_name": serialized.get("name") or "unknown_tool",
            # `inputs` is the structured call args (injected state already
            # excluded by LangGraph); falls back to the raw string for tools
            # that don't provide it.
            "tool_input": inputs if inputs is not None else {"input": input_str},
        }

    async def on_tool_end(self, output: typing.Any, *, run_id: uuid.UUID, **kwargs: typing.Any) -> None:
        await self._record(run_id, output=output, status="success")

    async def on_tool_error(self, error: BaseException, *, run_id: uuid.UUID, **kwargs: typing.Any) -> None:
        await self._record(run_id, output=repr(error), status="error")

    async def _record(self, run_id: uuid.UUID, *, output: typing.Any, status: str) -> None:
        pending = self._pending.pop(run_id, None)
        if pending is None:
            return

        # `output` is usually a `ToolMessage`; unwrap to its text content.
        content = getattr(output, "content", output)
        tool_output = content if isinstance(content, str) else str(content) if content is not None else None

        try:
            async with worker_session() as session:
                repo = CaseActionCRUDRepository(async_session=session)
                await repo.record_action(
                    case_id=self._case_id,
                    tool_name=pending["tool_name"],
                    tool_input=pending["tool_input"],
                    tool_output=tool_output,
                    status=status,
                )
        except Exception as exc:  # noqa: BLE001 - audit logging must never break the agent run
            loguru.logger.error(
                f"failed to record audit action for case {self._case_id} tool {pending['tool_name']}: {exc!r}"
            )

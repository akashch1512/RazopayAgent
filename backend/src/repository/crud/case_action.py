import typing

import sqlalchemy

from src.models.db.case_action import CaseAction
from src.repository.crud.base import BaseCRUDRepository


class CaseActionCRUDRepository(BaseCRUDRepository):
    async def record_action(
        self,
        *,
        case_id: int,
        tool_name: str,
        tool_input: dict[str, typing.Any],
        tool_output: str | None,
        status: str,
    ) -> CaseAction:
        action = CaseAction(
            case_id=case_id,
            tool_name=tool_name,
            tool_input=tool_input,
            tool_output=tool_output,
            status=status,
        )
        self.async_session.add(instance=action)
        await self.async_session.commit()
        await self.async_session.refresh(instance=action)
        return action

    async def list_actions_by_case(self, *, case_id: int, limit: int = 200) -> typing.Sequence[CaseAction]:
        """Oldest first - a chronological "what happened" trail."""
        stmt = (
            sqlalchemy.select(CaseAction)
            .where(CaseAction.case_id == case_id)
            .order_by(CaseAction.created_at.asc())
            .limit(limit)
        )
        return (await self.async_session.execute(stmt)).scalars().all()

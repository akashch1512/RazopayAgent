"""
The shared Celery application.

Design choices (all aimed at "every case gets processed by exactly one worker,
in priority order, and nothing is silently lost - however many workers we run"):

* **Redis broker with priority.** `priority_steps` + `sep` make Kombu fan the
  queue into per-priority lists; `send_task(priority=N)` then picks the band.
  0 = most urgent.
* **`acks_late` + `reject_on_worker_lost` + `prefetch_multiplier=1`.** A message
  is only acked after the task returns, and a crash re-queues it instead of
  losing it. Each worker process only ever holds one unacked message at a time
  (no head-of-line blocking from prefetching a batch), so scaling throughput is
  just `celery worker --concurrency=N` - see `CELERY_WORKER_CONCURRENCY` in
  docker-compose / `.env`. Safety against *double*-processing the same case
  comes from `RecoveryCaseCRUDRepository.claim_for_processing`'s atomic
  conditional UPDATE, not from limiting concurrency.
* **Results ignored by default.** The `recovery_case` row is the source of
  truth; we don't need a result backend unless one is explicitly configured.
* **Beat runs the reconciler** which is what actually prevents starvation and
  recovers lost / stuck cases.
"""

from celery import Celery

from src.config.manager import settings
from src.workers import names

celery_app = Celery(
    "razopay_agent",
    include=[
        "src.workers.tasks.recovery_cases",
        "src.workers.tasks.reconciliation",
        "src.workers.tasks.dropoff_detection",
    ],
)

celery_app.conf.update(
    broker_url=settings.CELERY_BROKER_URL,
    result_backend=settings.CELERY_RESULT_BACKEND,
    task_ignore_result=settings.CELERY_RESULT_BACKEND is None,
    # Reliability.
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_track_started=True,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=200,
    # Routing: everything lands on the single agent queue unless overridden.
    task_default_queue=settings.WEBHOOK_QUEUE_NAME,
    task_default_priority=settings.WEBHOOK_PRIORITY_STEPS // 2,
    task_queue_max_priority=settings.WEBHOOK_PRIORITY_STEPS - 1,
    # Guardrails for the (future) agent run.
    task_soft_time_limit=settings.WEBHOOK_TASK_SOFT_TIME_LIMIT_SECONDS,
    task_time_limit=settings.WEBHOOK_TASK_TIME_LIMIT_SECONDS,
    # Redis priority wiring.
    broker_transport_options={
        "priority_steps": list(range(settings.WEBHOOK_PRIORITY_STEPS)),
        "sep": ":",
        "queue_order_strategy": "priority",
        # A claimed-but-unacked message reappears after this long (lost worker).
        "visibility_timeout": settings.WEBHOOK_STUCK_AFTER_SECONDS,
    },
    # Local/testing escape hatch.
    task_always_eager=settings.CELERY_TASK_ALWAYS_EAGER,
    task_eager_propagates=settings.CELERY_TASK_ALWAYS_EAGER,
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        "recovery-cases-reconcile": {
            "task": names.RECOVERY_CASE_RECONCILE_TASK,
            "schedule": float(settings.WEBHOOK_RECONCILE_INTERVAL_SECONDS),
            "options": {"queue": settings.WEBHOOK_QUEUE_NAME, "priority": 0},
        },
        "dropoff-poll-businesses": {
            "task": names.DROPOFF_POLL_BUSINESSES_TASK,
            "schedule": float(settings.DROPOFF_SWEEP_INTERVAL_SECONDS),
            "options": {"queue": settings.WEBHOOK_QUEUE_NAME, "priority": 3},
        },
    },
)

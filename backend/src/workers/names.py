"""
Canonical Celery task names.

Producers enqueue by *name* (`celery_app.send_task`) so the FastAPI process never
has to import task code (or its heavier dependencies). Keep these stable - they
are effectively a wire contract with the broker.
"""

RECOVERY_CASE_PROCESS_TASK = "recovery.process_case"
RECOVERY_CASE_RECONCILE_TASK = "recovery.reconcile"

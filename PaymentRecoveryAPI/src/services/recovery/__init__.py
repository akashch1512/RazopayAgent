"""
Recovery-case pipeline: turn a normalized event (from a Razorpay webhook, the
drop-off poller, customer feedback, or a manual request) into recovery-case
work - merge/group, priority-score, persist, and dispatch to the agent worker.
Independent of Razorpay's API; it only consumes the normalized event shape.
"""

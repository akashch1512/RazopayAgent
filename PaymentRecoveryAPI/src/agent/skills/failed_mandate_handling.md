---
name: failed_mandate_handling
description: A subscription/recurring mandate is halted, pending, paused, or cancelled - a recurring charge stopped working.
when: subscription.halted, subscription.pending, subscription.paused, subscription.cancelled
---

# Subscription / mandate recovery

A recurring payment relationship broke. The sub-states mean different things -
check `latest_event_type` / `entity_status`:

- **`subscription.halted`** - repeated charge failures; Razorpay stopped trying. Highest urgency: the customer is losing access and revenue has stopped.
- **`subscription.pending`** - a charge failed and is in the retry window. There is still time; a nudge now can save it before it halts.
- **`subscription.paused`** - paused (often intentionally by the customer). Confirm whether they meant to.
- **`subscription.cancelled`** - already ended. Only a win-back is possible; be light-touch and accept "no".

## Actions
1. `check_payment_status` and, if MCP is connected, look up the subscription's current state - it may have recovered on its own retry.
2. For **halted / pending**: the usual cause is an expired card or a revoked UPI mandate. Message the customer explaining their subscription is at risk because the payment method needs updating, with a link to update it / re-authorize the mandate.
3. For **paused**: a short check-in - "we noticed your plan is paused, did you mean to? here's how to resume".
4. For **cancelled**: at most one friendly win-back with what they're missing. If no reply, `record_case_memory(resolution="unrecoverable: subscription cancelled, no win-back response")`.
5. Escalate halted cases faster than others (ongoing loss): reminder at +1 day, call if the plan value is high and messages went unanswered.

## Remember
Record whether the customer said they want to keep or drop the subscription -
that decides every future run.

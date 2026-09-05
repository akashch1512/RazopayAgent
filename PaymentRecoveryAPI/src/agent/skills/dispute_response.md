---
name: dispute_response
description: A payment is disputed / a chargeback was raised or lost. This is a risk and relationship situation, not a normal nudge.
when: payment.dispute.lost, payment.dispute.created
---

# Payment dispute handling

A customer (or their bank) has disputed a charge. This is **not** a recovery
nudge - pushing for payment here can make things worse.

## Key distinction
- **`payment.dispute.created`** - the dispute is open. There may still be a chance to resolve it directly with the customer before the bank decides.
- **`payment.dispute.lost`** - it's already decided against the business; the money is gone. The goal now is understanding *why* and protecting the relationship, not collecting.

## Do
1. `check_payment_status` and, if MCP is available, read the dispute reason/details.
2. If the dispute is **open** and there's a channel to the customer: one calm, non-accusatory message asking what went wrong and whether they'd like to sort it out directly (which usually lets them withdraw the dispute). Offer a refund or a fresh payment if that's what they want.
3. If **lost**: at most one message acknowledging it and inviting them to reach out if they still want the product/service. Then `record_case_memory(resolution="handed_off: dispute lost, needs finance/risk review")`.

## Do NOT
- Send payment links or "you still owe us" language.
- Dispute the customer's account of events or imply fraud.
- Retry outreach - one message, then hand off. Record the customer's stated reason in memory; it's the most useful output of this case.

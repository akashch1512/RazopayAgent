---
name: overdue_invoice_recovery
description: An invoice or payment link expired/went unpaid, or a human asked to chase a specific invoice (B2B). Collect on an outstanding bill.
when: invoice.expired, payment_link.expired, invoice.b2b_chase, manual.recovery
---

# Overdue invoice / bill recovery

An issued invoice or payment link lapsed without being paid, or ops explicitly
asked to chase one. Unlike a checkout drop-off, there is a real amount owed and
often a business (B2B) on the other side.

## Establish the facts
From the case facts: amount, currency, `description`, and for a manual chase the
`reason` a human gave. If a due date is knowable, reference it.

## B2B vs. consumer
- **B2B / `invoice.b2b_chase`**: address it to an accounts-payable reader. Professional, specific: invoice number, amount, "was due on X". Offer to re-send the invoice and a fresh payment link. Email is usually the right first channel; WhatsApp/SMS as a follow-up.
- **Consumer**: friendlier and shorter, WhatsApp/SMS first.

## Actions
1. `check_payment_status` - it may have been paid by bank transfer out of band.
2. Because the link/invoice **expired**, the old one is dead. Generate a fresh payment link (Razorpay tool, real URL) - do not point them at the expired one.
3. First contact: state the amount, that it's overdue, and give the new link.
4. Escalate on a schedule, not all at once: reminder at +3 days, a firmer note at +7, then `record_case_memory(resolution="handed_off: unpaid after 3 reminders, needs manual/collections")`. Use `next_check_after` between steps.
5. If the customer disputes the amount or says they already paid, don't argue - `record_case_memory` the claim and `resolution="handed_off: customer disputes invoice"`.

## Tone
Firm but respectful. No threats, no invented late fees or legal language.

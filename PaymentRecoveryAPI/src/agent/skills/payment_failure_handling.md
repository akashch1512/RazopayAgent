---
name: payment_failure_handling
description: A payment attempt failed (card declined, UPI timeout, insufficient funds, bank down). Recover a customer who tried to pay and couldn't.
when: payment.failed
---

# Payment failure recovery

The customer *wanted* to pay and the transaction failed. Intent is high - this
is the most recoverable situation. Move quickly while it's fresh.

## Read the failure reason first
The case facts usually carry `error_reason` / `error_description` / `method`.
Tailor the message to it:

- **`payment_failed` / bank/gateway error, `international_transaction_not_allowed`, `gateway_error`** - transient. Ask them to simply try again; offer a fresh payment link.
- **`insufficient_funds`** - do not say "insufficient funds" bluntly. Say the payment "didn't go through" and suggest trying another card / UPI / a bit later.
- **`payment_method_blocked`, `card_disabled`, `expired_card`, `incorrect_cvv`** - suggest a different card or UPI.
- **UPI `collect_request_expired` / timeout** - the request just lapsed; send a new link and mention UPI collect requests expire in a few minutes.

## Actions
1. `check_payment_status` - a retry may already have succeeded.
2. Send **one** clear message on the customer's most-engaged channel (WhatsApp/SMS first), acknowledging the failed attempt and giving a one-tap way to complete it (create a payment link via the Razorpay tool, paste the real URL).
3. If `event_count` is high (many failed retries on the same method), explicitly suggest switching method - repeating the same one won't help.
4. If they went quiet after a nudge, wait a day, send one gentle follow-up, then `record_case_memory(resolution="unrecoverable: no response after 2 nudges")`.

## Do not
- Send more than one message per run.
- Nudge again within 24h of the last contact unless the customer replied.

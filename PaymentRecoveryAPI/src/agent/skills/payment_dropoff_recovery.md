---
name: payment_dropoff_recovery
description: Customer started checkout (an order was created) but never attempted payment. Detected by polling, not a real webhook.
when: order.dropoff
---

# Checkout drop-off recovery

An order exists but no payment was ever attempted. This is synthesized by the
drop-off poller (`order.dropoff`), not a Razorpay webhook - so it is quieter
signal than a failed payment. The customer may have been distracted, comparing
prices, waiting for payday, or lost the tab.

## Tone
Assume good intent and low urgency. This is a *reminder*, not a "you owe us".
One friendly, low-pressure nudge - "you left something in your cart / your
order is waiting" - with a one-tap link to finish.

## Actions
1. `check_payment_status` first - a drop-off is the case type most likely to have quietly resolved (they came back and paid).
2. Pick the least intrusive channel with contact info: app notification or WhatsApp/SMS. **Never call** for a drop-off unless the amount is large and other channels failed.
3. Send one message with the order value and a payment link (real URL from the Razorpay tool).
4. If there's no response, one more reminder after ~48h, then stop: `record_case_memory(resolution="unrecoverable: abandoned cart, no response")`.
5. If the customer replies that they changed their mind, respect it - `resolution="unrecoverable: customer no longer wants the order"`.

## Cadence
Drop-offs are not urgent. Prefer `next_check_after` a day or two out over
back-to-back messages. Two total contacts is the ceiling.

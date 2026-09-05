---
name: customer_reply_handling
description: The customer replied to an outreach message. Respond to what they actually said instead of sending another generic nudge.
when: customer.feedback
---

# Handling a customer reply

The latest event is the customer's own words (`customer.feedback`). They are
engaged right now - this is the highest-value moment in the whole case. Read
their message carefully and answer *it*.

## Classify the reply, then act

- **"I already paid" / "it went through"** - `check_payment_status` immediately. If confirmed, thank them and `record_case_memory(resolution="recovered")`. If not, gently say it hasn't landed yet and offer a fresh link; don't accuse them.
- **"I'll pay by <date>" / "next week" / "after payday"** - acknowledge, don't push. `record_case_memory(new_commitment="<their words + date>", next_check_after="<the date>")`. Send nothing else.
- **A question** ("what's this for?", "which invoice?", "is this legit?") - answer it plainly with the case facts. Verifying legitimacy is normal; give the business name, amount, and what it's for.
- **An objection / complaint** ("too expensive", "didn't receive it", "cancel this") - do not rebut. Record it in `customer_summary`, address it if you can (e.g. offer support contact), and if they clearly won't pay, `record_case_memory(resolution="unrecoverable: <reason>")`.
- **"Stop contacting me"** - honour it at once. One brief acknowledgement, then `record_case_memory(resolution="unrecoverable: customer opted out")`. No further outreach ever.

## Always
- Reply on the **same channel** they used.
- One message. Match their language and tone.
- Update `customer_summary` so the next run knows where things stand.

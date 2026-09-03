# detection of timeout/checkoutdropoff
use 2 webhooks
1. order.created
2. order.captured

put created orders into set, with processing , and then pop and remove the case if order captures else put it into dropoff

processing: validate → extract order_id + metadata → store with TTL.

Use a delayed queue / Redis sorted set, not iteration.

For example with Redis:

order.created
    ↓
ZADD pending_orders <expiry_timestamp> <order_id>

payment.captured
    ↓
ZREM pending_orders <order_id>

A worker then efficiently fetches:

ZRANGEBYSCORE pending_orders -inf <now>
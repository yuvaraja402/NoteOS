# Notes storage

DynamoDB is the document store for this project. It supports key-value and
document models, which fit bounded per-device note workspaces. It is not a
drop-in Firestore SDK: FastAPI provides access control and the browser polls
sync status. See [AWS's document model](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/HowItWorks.CoreComponents.html).

## Write timing

An edit immediately updates React state and `sessionStorage`. The browser
keeps a per-note outbox, sends after 750ms without edits, and limits continuous
browser-side batching to two seconds. Requests are serialized; a response to
an older edit never replaces newer text. Client-generated UUIDs make retries
idempotent. Deletions are sent first to allow recovery from workspace limits.

FastAPI applies each mutation to a Redis workspace snapshot using WATCH/MULTI.
The snapshot revision and its sorted-set flush deadline change atomically.
The deadline is `min(last_edit + 60s, first_unflushed_edit + 300s)`.
These intervals are configurable. A worker polls every five seconds, so normal
persistence can occur up to one polling interval after the deadline. Outages
extend the delay; this is a scheduling target, not a durability SLA.

## Flush safety

- Dirty snapshots have no TTL and are never evicted by the configured Redis policy.
- Clean snapshots expire after 24 hours and reload from a consistent DynamoDB read.
- A per-workspace Redis lease prevents routine duplicate work across API tasks.
- DynamoDB conditional puts reject older revisions.
- A worker acknowledges only the revision it wrote. A newer edit keeps the workspace queued.
- Failed writes stay queued; the next poll retries. The worker runs independently of browser activity.
- Empty workspaces persist, so deleting the last note does not recreate starter notes.

Each DynamoDB item has `workspace_id`, `notes`, `revision`, and `persisted_at`.
The partition key is the HMAC-derived anonymous workspace ID; note documents
contain UUID, title, text, tags, color, pin state, and timestamps. Workspaces
are limited to 100 notes and 200 KiB of serialized note content, below the
[DynamoDB item limit](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Constraints.html).
Large collections would need per-note items and a different flush design.

The browser retains acknowledged-but-unpersisted mutations until DynamoDB's
persisted revision catches up. If a Redis snapshot regresses while that tab is
open, it replays the recovery copy. Concurrent tabs editing the same note use
last-write-wins; this is not a collaborative editor.

## Anonymous device access

A random UUID and HMAC signature are placed in an HttpOnly, SameSite cookie.
Production uses secure cookies and HTTPS. The API derives the workspace key
from the verified UUID; clients never submit a workspace key to CRUD endpoints.

IP addresses are HMAC-hashed for short-lived rate-limit buckets, not used as
identity. This avoids combining devices behind the same NAT or losing access
when a device's IP changes. There is no hardware fingerprinting or signup.
Separate browsers are separate anonymous devices. Clearing the cookie loses
access, and changing the signing key also requires an identity migration.

## Durability boundary

Redis is a buffer. Its replica and snapshots improve recovery but do not make
every acknowledged write a durable DynamoDB write. A Redis failure before
flush can lose buffered data, especially if the browser recovery tab is gone.
See [AWS's durability guidance](https://docs.aws.amazon.com/AmazonElastiCache/latest/dg/Durability.Options.html).

Session-only drafts disappear when the tab closes. Changes accepted by Redis
continue toward DynamoDB without the browser, provided the queue survives.
The UI labels all three stages. If zero loss before flush is required, add a
durable write journal or use a managed durable buffer; retain the distinction
between accepted and persisted in the product.

There is no automatic anonymous-workspace expiry or account recovery yet.
Before launch, define a retention/deletion policy, cookie recovery strategy,
Redis capacity alarms, queue-lag metrics, backup restoration tests, and scaling
limits. No SQL database, embedded database, or self-hosted cache is used.

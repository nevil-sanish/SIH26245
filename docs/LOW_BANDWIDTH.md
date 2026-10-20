# Low-bandwidth deployment mode (D5)

Rural centres may have 2G-class or intermittent links. SAKSHI never streams video: the edge sends one small signed
packet per camera per minute, keeps everything in a local SQLite outbox, and drains it in order when the link
returns.

## Tiers

| Tier | Contents | When | Size |
|---|---|---|---|
| **Whisper** | counts, entry/exit second offsets, occupancy (6 samples), asset seconds, clock drift, integrity flags, evidence, seq, prev hash, Ed25519 sig | every 60 s | **245 B** typical minute (`python -m edge.packet`); measured per camera below |
| **Normal** | Whisper + one 96×54 face-blurred JPEG per anomalous minute + keyframe pHash | anomalies only | + ~2–4 KB per anomaly |
| **Audit** | sealed raw clips from the edge ring buffer | only on a formal audit request, overnight, resumable | MB-scale |

Measured bytes per hour per camera (from the real edge outbox of the Colab run) are in
[`ACCURACY_REPORT.md` → Bandwidth](ACCURACY_REPORT.md#bandwidth-measured-from-the-edge-outbox).
Whisper at 245 B/min (self-check), **251 B/min measured** on the Colab door-camera run ≈ **15 KB per hour per camera**, ≈ 115 KB per 8-hour training day for a door + room pair.

## Store-and-forward

- `edge/outbox.py`: every packet is written to SQLite **before** any send; chain state (seq, prev hash) is persisted
  so a reboot never reuses a sequence number.
- Delivery oldest-first in batches of 200 (`POST /v1/ingest/packets` or MQTT QoS 1 to `sakshi/packets`); a packet
  is marked sent only when the cloud acks it (accepted or duplicate).
- The cloud verifies signature + chain + sequence, detects duplicates and reordering, and opens a `data_gap` for
  any hole, which closes automatically when the missing packets arrive.
- Every ack carries a server-signed time, used by the edge clock check.

**2-hour disconnection test** (`tests/test_chaos.py::test_two_hour_outage_no_data_loss`): 120 one-minute packets are
produced with the uplink down; then the cloud comes up and the outbox drains. Asserted: all 120 delivered in order,
every signature and chain link valid, zero unresolved gaps. **Passed in Colab (25/25 tests), 2026-10-20.**

## SMS fallback

If the link is down for more than 6 h, `edge/outbox.py::sms_summary()` builds one compressed daily summary per centre (≈ 140 chars:
centre, date, per-batch peak occupancy and entries, integrity flag bitmap, last seq) through any SMS gateway; the
signed packets still follow when the link returns, so the SMS is a heads-up, never the evidence. *Gateway
integration is a stub (no SMS provider is bundled).*

## Bandwidth knobs

`sample_fps` (door 5, room 1), packet interval (60 s), tier (`--tier whisper|normal`), keyframe interval (5 min),
asset scan interval (15 min) — all per camera.

# Privacy-preserving design note (D3)

SAKSHI verifies that **training happened** (people physically present, equipment used) without knowing
**who** was there. The attendance system the scheme already runs (Aadhaar-enabled biometric / face authentication)
remains the only place identity exists; SAKSHI only receives its check-in **timestamps** and asks whether each one
is explained by an anonymous physical door entry.

## 1. What is processed where

| Data | Processed on the edge (inside the centre) | Leaves the centre? | Stored in the cloud |
|---|---|---|---|
| Raw video frames | detection, tracking, zones, integrity checks | **Never** (except Audit tier, below) | — |
| Person / head boxes | per frame, in memory | No | — |
| Track IDs | ByteTrack, **reset every session** | No | — |
| Door crossings | timestamp + direction only | Yes (Whisper: second offsets) | `door_events` (no ID, no image) |
| Occupancy | count every 10 s | Yes (Whisper) | `occupancy_samples` (counts) |
| Asset use | seconds of person-in-zone + motion | Yes (Whisper) | `asset_observations` |
| Asset identity | DINOv2 embedding of **equipment** crops | Only the similarity score | `asset_observations.identity_score` |
| DVR clock | OCR of the timestamp box | Drift in seconds | `integrity_events` |
| Keyframe hash | 64-bit pHash of people-present frames, timestamp box masked | Yes (hash only) | `keyframe_hashes` |
| Thumbnails | 96×54 JPEG, **faces blurred first**, only on anomalies, Normal tier only | Yes | `packets.body.thumb`, purged after 90 days |
| Raw clips (Audit tier) | encrypted with the state nodal officer's public key (libsodium sealed box) | Only on a formal audit request | not in the analytics DB |
| Check-in log | — (comes from the scheme's attendance system) | — | `checkins`: batch + timestamp, **no names / Aadhaar** |

## 2. What is never done

- No face recognition, no face or person embeddings, no re-identification (`edge/` contains no such model).
- No cross-session or cross-day tracking: tracker state is recreated per session (`edge/track.py`).
- No behaviour, engagement or emotion scoring.
- No automatic penalties: the system flags, explains and ranks; an officer decides (`cloud/cases.py`).
- No raw video streaming to the cloud.

## 3. Face-blur pipeline

`edge/privacy.py`: CenterFace face detector (shipped with `deface`, MIT) on the full-resolution frame → enlarged
elliptical Gaussian blur on every face, **plus** the top 30 % of every person box we were given (far faces are
often too small for the face detector) → only then downscale to 96×54 and JPEG-encode (OpenCV writes no EXIF).
If the face detector is unavailable the module reports `faceblur` unavailable and **no thumbnail is produced**:
packets degrade to Whisper (fail closed). Measured miss rate on our footage: *pending — measured on the user's
own footage once provided (MEVA actors are not suitable to publish a face-level metric).*

## 4. Retention

| Data | Retention | Mechanism |
|---|---|---|
| Whisper aggregates (counts, events, flags) | scheme duration | — |
| Face-blurred thumbnails | 90 days | hourly purge in `cloud/api.py::purge_and_analyze` |
| Encrypted clips (edge) | 7–30 days (configurable) | `ClipRing.expire()`; no officer key configured = no clips kept at all |
| Audit log | scheme duration | `audit_log` |

## 5. Access control and the centre's right to respond

Roles (JWT): `admin`, `state_monitor`, `district_officer`, `inspector`, `centre_operator`. Centre operators see
only their own centre and can **respond** to or **appeal** any flag on it; officers confirm / mark false alarm /
request a response. Every view of a centre, reconciliation or flag, and every review action, is written to
`audit_log` (dashboard: Privacy & audit). Device enrolment (public key registration) is admin-only.

## 6. DPDP Act 2023 / DPDP Rules 2025 alignment

| Principle | How SAKSHI meets it |
|---|---|
| Notice | camera-notice board template below; states purpose, what is (not) collected, retention, contact |
| Purpose limitation | data used only to verify training delivery and infrastructure availability under the scheme |
| Data minimisation | aggregates and anonymous events only; images only blurred, tiny, on anomalies |
| Storage limitation | retention timers above, enforced in code |
| Security safeguards | Ed25519-signed, hash-chained packets; JWT roles; sealed-box clips; audit log |
| Accuracy & correction | centre response / appeal on every flag; evidence level shown; abstain when evidence is weak |
| Breach procedure | revoke device key (re-enrol), rotate JWT secret, notify the Data Protection Board and affected centres per the Rules' timelines; the analytics store holds no personal identifiers, limiting impact |
| Children | trainees may be 15–18: no identification, no profiling, which is what the Act requires for children's data |

**Notice board template (EN/HI on site):** "CCTV in this training centre is analysed automatically to count how many
people are present and whether equipment is in use. No one is identified. Faces are blurred before any image leaves
the centre. Recordings stay inside the centre and are deleted after 30 days unless a formal audit requests them.
Contact: <state nodal officer>."

## 7. Threat model

| Threat | Example | Mitigation |
|---|---|---|
| Centre operator (fraud) | bulk/proxy check-ins, replayed or frozen footage, rented equipment, performing for audits | H1 event matching, H2 clock/loop/duplicate/tamper checks, S2 identity, H3 shadow detector; silence = data gap |
| Centre operator (edge tampering) | edit or delete packets in the outbox | Ed25519 signature per packet, hash chain, sequence numbers → `chain_break` / `seq_gap` |
| Insider misuse (official) | browsing centres without cause | role scoping, audit log of every view, no images beyond blurred thumbnails |
| Network attacker | forge, replay, reorder packets | signatures, chain, server-side duplicate detection; signed server time in acks |
| Data leak | DB dump | no names, faces, IDs or embeddings of people in the cloud; thumbnails blurred and purged |
| Model error | false accusation | abstain on weak evidence, evidence level + confidence on every flag, human decision, centre response |

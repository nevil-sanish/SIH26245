# Demo script (≈ 5 minutes)

Setup: `docker compose up` (first start seeds the story) → http://localhost:3000. Accounts: `data/demo/users.yaml`.
Labels on screen: **measured** (real model output on real footage), **simulated** (red-team), **mock** (stand-in
government data). Say this once at the start and point at the tags.

| # | Screen | Say | Shows |
|---|---|---|---|
| 1 | Login `state` → Risk queue | "Officers don't watch video. They get a ranked list of where to go, with reasons." | ranking, evidence badges, ₹-at-risk, top-3 reasons |
| 2 | TC0880 (Ranchi) → batch → reconciliation | "25 check-ins in 40 seconds, room empty. Every check-in must be explained by a door entry — none are." | **H1**: hollow unmatched markers, burst, ghost session, Integrity Score |
| 3 | TC0777 (Patna) → flag `clock_drift` → evidence | "Looks like a normal busy entrance. But the DVR clock reads yesterday, and this crowd already appeared on another day." | **H2**: OCR drift −24 h, pHash loop match, signed packets — measured on real MEVA footage |
| 4 | TC0555 (Jaipur) → `cross_centre_duplicate` | "Same frame submitted by two centres — the CAG finding, caught automatically." | fleet-wide registry |
| 5 | TC0915 (Guwahati) → case file trend | "Scores jump exactly around inspection dates." | **H3**: change points + permutation p-value |
| 6 | TC0307 (Coimbatore) → equipment | "The lathe is present for inspectors — and unused on 14 of 14 practical days." | **S1** OAI; wording: no use observed |
| 7 | TC0421 (Pune) → case file | "An honest centre stays clean, on the same real footage the replay centre faked." | honest control, FULL evidence |
| 8 | TC0612 → `data_gap` | "A frozen camera never counts as compliant: we abstain and say why." | INSUFFICIENT evidence |
| 9 | Flag → Confirm / Request response; log in as `tc0880` → respond | "No automatic penalty. The centre can answer; everything is audit-logged." | review workflow, audit log |
| 10 | Red-team & accuracy | "Our numbers include failures: subtle fraud below threshold is missed — on purpose, to keep false alarms at zero." | confusion matrices, robustness, bandwidth |
| 11 | हिन्दी toggle; Inspector on a phone | "Hindi throughout; the inspector checklist works offline." | i18n, offline cache |

Backup if the network fails: everything runs offline after setup.

"""Human-in-the-loop case workflow (PROMPT §1.4, §15). The system never penalises: officers decide.

flag (open) ──review──▶ confirmed | false_alarm | awaiting_centre
awaiting_centre ──centre_response──▶ open (back to the officer, with the centre's explanation)
confirmed ──appeal (centre)──▶ open
any ──close (officer)──▶ closed
Every step is a CaseAction row plus an AuditLog row.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from cloud.db import AuditLog, Case, CaseAction, Flag

OFFICER_ACTIONS = {"confirm": "confirmed", "false_alarm": "false_alarm",
                   "request_response": "awaiting_centre", "close": "closed", "assign": None,
                   "site_check": None}   # inspector ticked the item on site: logged, no status change
CENTRE_ACTIONS = {"centre_response": "open", "appeal": "open"}


class Forbidden(Exception):
    pass


def case_for(db: Session, flag: Flag) -> Case:
    c = db.query(Case).filter_by(flag_id=flag.id).first()
    if c is None:
        c = Case(flag_id=flag.id, centre_id=flag.centre_id)
        db.add(c); db.flush()
    return c


def act(db: Session, flag: Flag, user: dict, action: str, note: str | None = None, assignee: str | None = None) -> Case:
    role = user["role"]
    if role == "centre_operator":
        if action not in CENTRE_ACTIONS or user.get("centre_id") != flag.centre_id:
            raise Forbidden("centre operators can only respond to flags on their own centre")
        new = CENTRE_ACTIONS[action]
    else:
        if action not in OFFICER_ACTIONS or role not in ("admin", "state_monitor", "district_officer", "inspector"):
            raise Forbidden(f"{role} cannot {action}")
        new = OFFICER_ACTIONS[action]
    c = case_for(db, flag)
    if action == "assign":
        c.assigned_to = assignee
    if new:
        flag.status = new
        c.status = new
    db.add(CaseAction(case_id=c.id, actor=user["sub"], role=role, action=action, note=note))
    db.add(AuditLog(user=user["sub"], role=role, action=action, target=f"flag:{flag.id}"))
    db.commit()
    return c

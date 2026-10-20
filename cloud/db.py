"""Database schema (PROMPT §9) — SQLAlchemy 2.0 ORM.

Postgres + TimescaleDB in docker compose (occupancy_samples becomes a hypertable); SQLite for tests and
fully-offline laptop runs. `DATABASE_URL` selects; default is SQLite at data/sakshi.db.

Every analytic row carries `label` ∈ {measured, simulated, mock} (PROMPT §1.5) so the dashboard
never mixes real model output with red-team or stand-in data silently.
No table stores names, faces or identity embeddings of people.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import (JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint,
                        create_engine, event, text)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

ROOT = Path(__file__).resolve().parents[1]
URL = os.environ.get("DATABASE_URL", f"sqlite:///{ROOT / 'data' / 'sakshi.db'}")


def now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


# --- programme data (from the mock SIDH adapter) ------------------------------------------------
class Centre(Base):
    __tablename__ = "centres"
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    state: Mapped[str] = mapped_column(String(64))
    district: Mapped[str] = mapped_column(String(64))
    lat: Mapped[float] = mapped_column(Float)
    lon: Mapped[float] = mapped_column(Float)
    public_key: Mapped[str | None] = mapped_column(String(64))       # edge device Ed25519 key (base64)
    label: Mapped[str] = mapped_column(String(12), default="mock")
    story: Mapped[str | None] = mapped_column(String(64))            # demo scenario tag (simulated centres)


class Camera(Base):
    __tablename__ = "cameras"
    id: Mapped[str] = mapped_column(String(80), primary_key=True)    # "<centre>:<cam>"
    centre_id: Mapped[str] = mapped_column(ForeignKey("centres.id"))
    cam: Mapped[str] = mapped_column(String(40))
    role: Mapped[str] = mapped_column(String(16))                    # door | room | workshop
    last_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_t: Mapped[int | None] = mapped_column(Integer)
    fps: Mapped[float | None] = mapped_column(Float)
    unavailable: Mapped[list | None] = mapped_column(JSON)           # modules reported unavailable by edge
    config: Mapped[dict | None] = mapped_column(JSON)                # calibration (door line, zones, ROI)


class Batch(Base):
    __tablename__ = "batches"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    centre_id: Mapped[str] = mapped_column(ForeignKey("centres.id"))
    job_role: Mapped[str] = mapped_column(String(120))
    qp_code: Mapped[str] = mapped_column(String(32))
    room: Mapped[str] = mapped_column(String(40))
    door_cam: Mapped[str | None] = mapped_column(String(40))
    room_cam: Mapped[str | None] = mapped_column(String(40))
    label: Mapped[str] = mapped_column(String(12), default="mock")


class TimetableSlot(Base):
    __tablename__ = "timetable_slots"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    batch_id: Mapped[str] = mapped_column(ForeignKey("batches.id"))
    room: Mapped[str] = mapped_column(String(40))
    start: Mapped[int] = mapped_column(Integer)                      # unix seconds
    end: Mapped[int] = mapped_column(Integer)
    kind: Mapped[str] = mapped_column(String(12))                    # theory | practical | break


class Enrolment(Base):
    __tablename__ = "enrolments"
    batch_id: Mapped[str] = mapped_column(ForeignKey("batches.id"), primary_key=True)
    count: Mapped[int] = mapped_column(Integer)                      # counts only — no names


class TrainerSchedule(Base):
    __tablename__ = "trainers_schedule"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    batch_id: Mapped[str] = mapped_column(ForeignKey("batches.id"))
    date: Mapped[str] = mapped_column(String(10))
    count: Mapped[int] = mapped_column(Integer, default=1)


class Checkin(Base):
    __tablename__ = "checkins"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    batch_id: Mapped[str] = mapped_column(ForeignKey("batches.id"), index=True)
    ts: Mapped[int] = mapped_column(Integer, index=True)             # no names in the analytics store
    label: Mapped[str] = mapped_column(String(12), default="mock")


# --- edge-derived observations ---------------------------------------------------------------
class Packet(Base):
    __tablename__ = "packets"
    centre_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    cam: Mapped[str] = mapped_column(String(40), primary_key=True)
    seq: Mapped[int] = mapped_column(Integer, primary_key=True)
    t: Mapped[int] = mapped_column(Integer, index=True)
    prev_hash: Mapped[str] = mapped_column(String(16))
    hash: Mapped[str] = mapped_column(String(16))
    sig: Mapped[str] = mapped_column(String(100))
    sig_ok: Mapped[bool] = mapped_column(Boolean)
    chain_ok: Mapped[bool | None] = mapped_column(Boolean)           # None until neighbour arrives
    bytes: Mapped[int] = mapped_column(Integer)
    tier: Mapped[str] = mapped_column(String(1))
    body: Mapped[dict] = mapped_column(JSON)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    label: Mapped[str] = mapped_column(String(12), default="measured")


class DoorEvent(Base):
    __tablename__ = "door_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    centre_id: Mapped[str] = mapped_column(String(32), index=True)
    cam: Mapped[str] = mapped_column(String(40))
    ts: Mapped[int] = mapped_column(Integer, index=True)
    direction: Mapped[str] = mapped_column(String(3))               # in | out
    label: Mapped[str] = mapped_column(String(12), default="measured")


class OccupancySample(Base):
    __tablename__ = "occupancy_samples"                              # TimescaleDB hypertable on Postgres
    centre_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    cam: Mapped[str] = mapped_column(String(40), primary_key=True)
    ts: Mapped[int] = mapped_column(Integer, primary_key=True)
    occ: Mapped[int] = mapped_column(Integer)
    trainers: Mapped[int | None] = mapped_column(Integer)
    label: Mapped[str] = mapped_column(String(12), default="measured")


class AssetRegistry(Base):
    __tablename__ = "asset_registry"
    asset_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    centre_id: Mapped[str] = mapped_column(ForeignKey("centres.id"))
    label: Mapped[str] = mapped_column(String(80))
    zone: Mapped[list | None] = mapped_column(JSON)
    embedding_ref: Mapped[str | None] = mapped_column(String(200))   # embedding stays on the edge
    source: Mapped[str] = mapped_column(String(200))


class SanctionedInventory(Base):
    __tablename__ = "sanctioned_inventory"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    qp_code: Mapped[str] = mapped_column(String(32), index=True)
    job_role: Mapped[str] = mapped_column(String(120))
    item: Mapped[str] = mapped_column(String(120))
    qty: Mapped[int] = mapped_column(Integer)
    per: Mapped[str] = mapped_column(String(16))                     # batch | trainee
    source_note: Mapped[str] = mapped_column(Text)


class AssetObservation(Base):
    __tablename__ = "asset_observations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    centre_id: Mapped[str] = mapped_column(String(32), index=True)
    asset_id: Mapped[str] = mapped_column(String(40))
    date: Mapped[str] = mapped_column(String(10))
    present: Mapped[bool] = mapped_column(Boolean, default=True)
    interaction_s: Mapped[float] = mapped_column(Float, default=0)
    scheduled_practical_s: Mapped[float] = mapped_column(Float, default=0)
    identity_score: Mapped[float | None] = mapped_column(Float)
    label: Mapped[str] = mapped_column(String(12), default="measured")
    __table_args__ = (UniqueConstraint("centre_id", "asset_id", "date"),)


class IntegrityEvent(Base):
    __tablename__ = "integrity_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    centre_id: Mapped[str] = mapped_column(String(32), index=True)
    cam: Mapped[str] = mapped_column(String(40))
    ts: Mapped[int] = mapped_column(Integer)
    kind: Mapped[str] = mapped_column(String(32))
    value: Mapped[dict | None] = mapped_column(JSON)
    label: Mapped[str] = mapped_column(String(12), default="measured")


class KeyframeHash(Base):
    __tablename__ = "keyframe_hashes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    centre_id: Mapped[str] = mapped_column(String(32), index=True)
    cam: Mapped[str] = mapped_column(String(40))
    ts: Mapped[int] = mapped_column(Integer)
    phash: Mapped[str] = mapped_column(String(16), index=True)


class DataGap(Base):
    __tablename__ = "data_gaps"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    centre_id: Mapped[str] = mapped_column(String(32), index=True)
    cam: Mapped[str] = mapped_column(String(40))
    start: Mapped[int] = mapped_column(Integer)
    end: Mapped[int | None] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(String(40))                  # seq_gap | offline | chain_break
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)


class Inspection(Base):
    __tablename__ = "inspections"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    centre_id: Mapped[str] = mapped_column(ForeignKey("centres.id"))
    date: Mapped[str] = mapped_column(String(10))
    outcome: Mapped[str] = mapped_column(String(40))
    label: Mapped[str] = mapped_column(String(12), default="mock")


class Reconciliation(Base):
    """H1 output per batch per date (daily Integrity Score series feeds H3)."""
    __tablename__ = "reconciliations"
    batch_id: Mapped[str] = mapped_column(ForeignKey("batches.id"), primary_key=True)
    date: Mapped[str] = mapped_column(String(10), primary_key=True)
    centre_id: Mapped[str] = mapped_column(String(32), index=True)
    score: Mapped[float | None] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(24))
    evidence_level: Mapped[str] = mapped_column(String(12))
    unverified_trainee_hours: Mapped[float | None] = mapped_column(Float)
    result: Mapped[dict] = mapped_column(JSON)
    label: Mapped[str] = mapped_column(String(12))


# --- review workflow ----------------------------------------------------------------------------
class Flag(Base):
    __tablename__ = "flags"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    centre_id: Mapped[str] = mapped_column(String(32), index=True)
    batch_id: Mapped[str | None] = mapped_column(String(40))
    date: Mapped[str] = mapped_column(String(10))
    type: Mapped[str] = mapped_column(String(32))
    severity: Mapped[float] = mapped_column(Float)
    confidence: Mapped[str] = mapped_column(String(8))               # high | medium | low
    evidence_level: Mapped[str] = mapped_column(String(12))
    explanation: Mapped[str] = mapped_column(Text)
    next_step: Mapped[str] = mapped_column(Text)
    links: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(20), default="open")  # open | confirmed | false_alarm | awaiting_centre | closed
    label: Mapped[str] = mapped_column(String(12))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    __table_args__ = (UniqueConstraint("centre_id", "batch_id", "date", "type"),)


class Case(Base):
    __tablename__ = "cases"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    flag_id: Mapped[int] = mapped_column(ForeignKey("flags.id"), unique=True)
    centre_id: Mapped[str] = mapped_column(String(32), index=True)
    status: Mapped[str] = mapped_column(String(20), default="open")
    assigned_to: Mapped[str | None] = mapped_column(String(64))


class CaseAction(Base):
    __tablename__ = "case_actions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"), index=True)
    actor: Mapped[str] = mapped_column(String(64))
    role: Mapped[str] = mapped_column(String(24))
    action: Mapped[str] = mapped_column(String(32))                  # confirm | false_alarm | request_response | centre_response | assign | appeal | close
    note: Mapped[str | None] = mapped_column(Text)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class AuditLog(Base):
    __tablename__ = "audit_log"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    user: Mapped[str] = mapped_column(String(64))
    role: Mapped[str] = mapped_column(String(24))
    action: Mapped[str] = mapped_column(String(32))                  # view | review | export | login ...
    target: Mapped[str] = mapped_column(String(120))


class User(Base):
    __tablename__ = "users"
    username: Mapped[str] = mapped_column(String(64), primary_key=True)
    role: Mapped[str] = mapped_column(String(24))                    # admin | state_monitor | district_officer | inspector | centre_operator
    centre_id: Mapped[str | None] = mapped_column(String(32))        # centre operators only
    state: Mapped[str | None] = mapped_column(String(64))
    password_hash: Mapped[str] = mapped_column(String(200))


engine = create_engine(URL, future=True)
if URL.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def _wal(conn, _):
        conn.execute("PRAGMA journal_mode=WAL")

SessionLocal = sessionmaker(engine, expire_on_commit=False)


def init_db(drop: bool = False):
    if URL.startswith("sqlite"):
        Path(URL.removeprefix("sqlite:///")).parent.mkdir(parents=True, exist_ok=True)
    if drop:
        Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    if engine.dialect.name == "postgresql":
        with engine.begin() as c:
            c.execute(text("CREATE EXTENSION IF NOT EXISTS timescaledb"))
            c.execute(text("SELECT create_hypertable('occupancy_samples', by_range('ts', 86400), "
                           "if_not_exists => TRUE, migrate_data => TRUE)"))

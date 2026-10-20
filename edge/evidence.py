"""Evidence level per camera per packet window (PROMPT §5.3).

Per camera the edge can only say OK or INSUFFICIENT; the cloud combines cameras into
FULL (door + room OK) / REDUCED (room only) / INSUFFICIENT for each batch.
"""
from __future__ import annotations

TAMPER = ("frozen", "covered", "moved", "clock_drift", "clock_non_monotonic", "loop")


def camera_level(flags: set[str], frames_seen: int, frames_expected: int, sharpness: float | None,
                 lap_min: float = 22.0) -> str:
    if any(f in flags for f in TAMPER):
        return "INSUFFICIENT"
    if frames_expected and frames_seen < 0.5 * frames_expected:
        return "INSUFFICIENT"       # dropped frames / stream stalls
    if sharpness is not None and sharpness < lap_min:
        return "INSUFFICIENT"
    return "OK"


def batch_level(door_ok: bool | None, room_ok: bool | None) -> str:
    """door_ok/room_ok: None = camera not installed, False = installed but not OK in this window."""
    if room_ok is not True:
        return "INSUFFICIENT"
    if door_ok is True:
        return "FULL"
    return "REDUCED"


if __name__ == "__main__":
    assert camera_level({"frozen"}, 60, 60, 100) == "INSUFFICIENT"
    assert camera_level(set(), 20, 60, 100) == "INSUFFICIENT"
    assert camera_level(set(), 60, 60, 100) == "OK"
    assert batch_level(True, True) == "FULL" and batch_level(None, True) == "REDUCED"
    assert batch_level(True, False) == "INSUFFICIENT"
    print("evidence self-check ok")

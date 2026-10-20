"""SAKSHI edge package. IST is the single timezone for wall-clock values (DVR overlays, dates, timetables):
centres are in India and Colab/demo machines run in other zones, so nothing may rely on the host's local time."""
from datetime import timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30), "IST")

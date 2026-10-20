# SAKSHI — one-command targets. Heavy work (training, inference, eval) runs in Colab: see README "Running".
PY ?= python

setup:            ## models + data (needs network once; offline afterwards)
	$(PY) -m pip install -r edge/requirements.txt
	$(PY) data/download.py
	$(PY) models/download.py
	$(PY) scripts/check_licenses.py

edge-demo:        ## red-team clips → edge pipeline on every video scenario → packets to the cloud
	$(PY) -m redteam.runner prepare
	$(PY) -m redteam.runner video --uplink http://localhost:8000

redteam:          ## simulated scenarios through the engines
	$(PY) -m redteam.runner sims --seeds 20

eval:             ## robustness + accuracy (writes data/work/*.json)
	$(PY) -m eval.robustness
	$(PY) -m eval.metrics --seeds 20

report: eval      ## docs/ACCURACY_REPORT.md
	$(PY) -m eval.report

seed:             ## demo story into the DB (also runs automatically on first `docker compose up`)
	$(PY) -m cloud.demo_seed --fresh

test:
	$(PY) -m pytest -q tests

licences:
	$(PY) scripts/check_licenses.py

.PHONY: setup edge-demo redteam eval report seed test licences

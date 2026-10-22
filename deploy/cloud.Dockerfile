FROM python:3.12.8-slim
WORKDIR /app
COPY cloud/requirements.txt cloud/requirements.txt
RUN pip install --no-cache-dir -r cloud/requirements.txt
COPY cloud cloud
COPY edge/__init__.py edge/packet.py edge/evidence.py edge/
COPY redteam redteam
COPY eval/__init__.py eval/metrics.py eval/
COPY data/sanctioned_inventory data/sanctioned_inventory
COPY data/demo data/demo
COPY models/checksums.txt models/checksums.txt
# Seed the demo story on first start (empty DB), then serve.
CMD ["sh", "-c", "python -m cloud.demo_seed --if-empty && uvicorn cloud.api:app --host 0.0.0.0 --port 8000"]

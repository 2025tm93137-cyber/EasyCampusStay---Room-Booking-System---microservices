FROM python:3.12-slim-bookworm
WORKDIR /app
COPY requirements.lock.txt .
RUN pip install --no-cache-dir -r requirements.lock.txt
COPY scripts ./scripts
COPY deploy/run_checks.py ./deploy/run_checks.py
CMD ["python", "deploy/run_checks.py"]

FROM python:3.12-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 HOST=0.0.0.0 PORT=8080 WORKERS=2
WORKDIR /app/services/reservation
COPY services/reservation/requirements.lock.txt ./requirements.lock.txt
RUN pip install --no-cache-dir -r requirements.lock.txt && useradd --create-home app
COPY --chown=app:app services/reservation/src ./src
COPY --chown=app:app services/reservation/run.py ./run.py
RUN mkdir logs && chown app:app logs
USER app
EXPOSE 8080
HEALTHCHECK --interval=10s --timeout=4s --start-period=30s --retries=6 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health',timeout=3)"
CMD ["python", "run.py"]

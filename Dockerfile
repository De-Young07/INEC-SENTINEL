FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src/ src/
COPY web/ web/
COPY data/sentinel_evidence.csv data/sentinel_evidence.geojson data/
COPY data/facilities.csv data/facilities_audit.json data/sentinel_sources.json data/
EXPOSE 8600
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8600/api/health', timeout=4)"
CMD ["python", "-m", "uvicorn", "src.web_api:app", "--host", "0.0.0.0", "--port", "8600", "--workers", "2"]

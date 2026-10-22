# Image som serverar den godkända churnmodellen via ett API.
#
# Imagen tränar ingenting. Den kopierar in outputs/ som train-jobbet har tagit fram
# och utvardera-jobbet har godkänt (laddas ner som artefakt innan bygget).
# Bygg lokalt:  python -m churn.model && docker build -t churn .
# Kör:          docker run -p 8000:8000 churn   →  http://localhost:8000/health

# Samma Python-version som servern och som train-jobbet i CI.
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    MODELLFIL=/app/outputs/modell.joblib

WORKDIR /app

# Beroendena först och koden sist: ändras bara koden återanvänder Docker
# installationslagret från förra bygget.
COPY pyproject.toml ./
COPY src ./src
RUN pip install ".[api]"

# Den godkända modellen och dess mätvärden (commit, data_sha256, roc_auc).
COPY outputs/modell.joblib outputs/matvarden.json ./outputs/

# Kör inte som root i containern.
RUN useradd --create-home app
USER app

EXPOSE 8000

# Docker markerar containern som unhealthy om /health slutar svara.
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

CMD ["uvicorn", "churn.app:app", "--host", "0.0.0.0", "--port", "8000"]

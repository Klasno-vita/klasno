FROM python:3.12-slim

WORKDIR /app

COPY services/ingestion/transform/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY services ./services

CMD ["python", "-m", "services.ingestion.transform.job"]

FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY salus ./salus
COPY web ./web
COPY schema ./schema
COPY cypher ./cypher
COPY README.md .

ENV FALKOR_HOST=falkordb
ENV FALKOR_PORT=6379
ENV SALUS_TENANT=acme

EXPOSE 8080

CMD ["python", "-m", "uvicorn", "salus.api:app", "--host", "0.0.0.0", "--port", "8080"]

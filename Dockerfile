FROM python:3.12-alpine

WORKDIR /app
COPY server.py index.html admin.html ./
COPY samples ./samples

RUN mkdir -p /app/data

ENV BIGTV_PORT=8080 \
    BIGTV_DB=/app/data/bigtv.db \
    PYTHONUNBUFFERED=1

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=4s --start-period=5s \
  CMD python3 -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8080/api/ping')" || exit 1

CMD ["python3", "server.py"]

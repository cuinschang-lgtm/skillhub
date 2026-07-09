FROM python:3.11-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
    poppler-utils qpdf && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY apps/api/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY apps/api /app
COPY skeleton /skeleton
COPY prompts /prompts

COPY apps/api/start.sh /start.sh
RUN chmod +x /start.sh

EXPOSE 8000
ENV PYTHONPATH=/app:/skeleton
CMD ["/start.sh"]

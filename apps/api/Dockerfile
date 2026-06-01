FROM node:20-slim AS frontend-build
WORKDIR /app
COPY apps/web/package.json apps/web/package-lock.json ./
RUN npm ci
COPY apps/web/ ./
RUN npm run build

FROM python:3.11-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
    poppler-utils qpdf curl && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY apps/api/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY apps/api /app
COPY skeleton /skeleton
COPY prompts /prompts

COPY --from=frontend-build /app/.next/standalone ./web
COPY --from=frontend-build /app/.next/static ./web/.next/static
COPY --from=frontend-build /app/public ./web/public

COPY apps/api/start.sh /start.sh
RUN chmod +x /start.sh

EXPOSE 8000
ENV PYTHONPATH=/app:/skeleton
ENV NODE_ENV=production
CMD ["/start.sh"]

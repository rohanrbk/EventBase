FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=8000
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN useradd --system --uid 10001 --create-home eventbase && mkdir -p /app/data /app/staticfiles && chown -R eventbase:eventbase /app && chmod +x /app/entrypoint.sh
USER eventbase
EXPOSE 8000
CMD ["/app/entrypoint.sh"]



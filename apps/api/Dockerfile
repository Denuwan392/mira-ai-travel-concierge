FROM python:3.13-slim
WORKDIR /app
ENV LOG_FORMAT=json PYTHONUNBUFFERED=1
COPY apps/api/requirements.lock .
RUN pip install --no-cache-dir -r requirements.lock
COPY apps/api/mira ./mira
CMD ["python", "-m", "mira.serve", "--host", "0.0.0.0", "--port", "8000"]

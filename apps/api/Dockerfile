FROM python:3.13-slim
WORKDIR /app
COPY apps/api/requirements.lock .
RUN pip install --no-cache-dir -r requirements.lock
COPY apps/api/mira ./mira
CMD ["python", "-m", "uvicorn", "mira.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]

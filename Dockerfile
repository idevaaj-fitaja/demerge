FROM python:3.11-slim

RUN useradd -m -u 1000 user

WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir --upgrade -r requirements.txt

COPY app/ app/

ENV PYTHONPATH=/app
ENV SUPABASE_URL=""
ENV SUPABASE_KEY=""
ENV SUPABASE_STORAGE_BUCKET="documents"
ENV CORS_ORIGINS="*"

EXPOSE 7860

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]

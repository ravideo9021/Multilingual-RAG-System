# Frontend Dockerfile — standalone HTML/JS UI for multilingual-rag

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY app.py index.html ./

EXPOSE 7860

CMD ["python", "app.py"]

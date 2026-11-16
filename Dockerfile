# 1. set the base image
FROM python:3.13-slim

# Sensible Python defaults for containers
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# install dependencies in the first layer
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# copy the application
COPY ./app ./app

# the port that app uses
EXPOSE 8000

# 0.0.0.0 port for traffic outside, not only inside the container
# uvicorn is a serever
# module:variable -> take "app" variable from app.main = app/main.py module
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
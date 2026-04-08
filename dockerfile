FROM python:3.11-slim-bullseye

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    libfreetype6-dev \
    libpng-dev \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /app/instance

COPY requirements.txt .

# Используем HTTP зеркало (без SSL) для обхода проблем с сертификатами
RUN pip install --no-cache-dir --timeout 300 -i http://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com -r requirements.txt

COPY . .

RUN python -c "from app.init_db import init_db; init_db()"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
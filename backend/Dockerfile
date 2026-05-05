FROM python:3.12-slim


WORKDIR /app
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

COPY . .


RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 5000

CMD ["gunicorn", "app:app", "-w", "2", "-b", "0.0.0.0:5000", "--timeout", "120"]
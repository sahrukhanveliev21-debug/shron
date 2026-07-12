FROM python:3.9-alpine
WORKDIR /app
RUN apk add --no-cache gcc musl-dev
COPY requirements.txt .
RUN pip install --no-cache-dir telethon
COPY bot.py .
CMD ["python", "bot.py"]

FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY rpg ./rpg
COPY app.py .
ENV RPG_DB_PATH=/data/rpg.db
VOLUME /data
CMD ["python", "app.py"]

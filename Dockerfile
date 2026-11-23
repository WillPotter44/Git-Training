FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY rpg ./rpg
COPY app.py discord_bot.py ./
# Default runs the Slack bot; use `python discord_bot.py` as the command for Discord.
ENV RPG_DB_PATH=/data/rpg.db
VOLUME /data
CMD ["python", "app.py"]

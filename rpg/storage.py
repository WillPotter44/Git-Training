"""SQLite persistence for player saves. One row per (team, user)."""

import json
import sqlite3
import threading


class Store:
    def __init__(self, path: str = "rpg.db"):
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._lock = threading.RLock()
        with self._lock:
            self._conn.execute(
                "CREATE TABLE IF NOT EXISTS players ("
                " team TEXT NOT NULL, user TEXT NOT NULL, data TEXT NOT NULL,"
                " PRIMARY KEY (team, user))"
            )
            self._conn.commit()

    @property
    def lock(self) -> threading.RLock:
        return self._lock

    def load(self, team: str, user: str) -> dict | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT data FROM players WHERE team=? AND user=?", (team, user)
            ).fetchone()
        return json.loads(row[0]) if row else None

    def save(self, team: str, user: str, data: dict) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT INTO players (team, user, data) VALUES (?, ?, ?) "
                "ON CONFLICT(team, user) DO UPDATE SET data=excluded.data",
                (team, user, json.dumps(data)),
            )
            self._conn.commit()

    def delete(self, team: str, user: str) -> None:
        with self._lock:
            self._conn.execute("DELETE FROM players WHERE team=? AND user=?", (team, user))
            self._conn.commit()

    def all_players(self, team: str) -> list[dict]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT data FROM players WHERE team=?", (team,)
            ).fetchall()
        return [json.loads(r[0]) for r in rows]

#!/usr/bin/env .venv/bin/python3

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
import tracerouteanalysis as ta
logger = ta.get_logger(__name__)

import argparse
import json
import os
import signal
import sqlite3
import threading
import httpx
from datetime import datetime, timezone


CREATE_SQL = """
PRAGMA journal_mode = OFF;
PRAGMA synchronous = OFF;
PRAGMA locking_mode = EXCLUSIVE;
PRAGMA temp_store = MEMORY;
PRAGMA cache_size = -200000;
PRAGMA mmap_size = 1073741824;

CREATE TABLE IF NOT EXISTS fies (
    agent_id                TEXT        NOT NULL,
    probing_directive_id    INTEGER     NOT NULL,
    sequence_number         INTEGER     NOT NULL,
    ip_version              INTEGER     NOT NULL,
    protocol                INTEGER     NOT NULL,
    source_address          TEXT        NOT NULL,
    destination_address     TEXT        NOT NULL,
    near_probe_ttl          INTEGER,
    near_reply_address      TEXT,
    near_sent_timestamp     INTEGER,
    near_received_timestamp INTEGER,
    far_probe_ttl           INTEGER,
    far_reply_address       TEXT,
    far_sent_timestamp      INTEGER,
    far_received_timestamp  INTEGER,
    production_timestamp    INTEGER     NOT NULL
);
"""

INDEX_SQL = """
CREATE INDEX idx_fies_time ON fies(production_timestamp);
CREATE INDEX idx_fies_pdid_seq ON fies(probing_directive_id, sequence_number);
"""

INSERT_SQL = """
INSERT INTO fies VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
"""


def parse_duration(s: str) -> int:
    """Parse human readable duration to seconds: 10s, 5m, 1h, 2d, 1w"""
    units = {"s": 1, "m": 60, "h": 3600, "d": 24 * 3600, "w": 7 * 24 * 3600}
    if s[-1] in units:
        return int(s[:-1]) * units[s[-1]]
    return int(s)


def parse_timestamp(s: str) -> int:
    if not s:
        return 0
    return int(datetime.fromisoformat(s).replace(tzinfo=timezone.utc).timestamp())


def parse_record(obj: dict) -> tuple:
    near = obj.get("near_info") or {}
    far = obj.get("far_info") or {}
    return (
        obj.get("agent", {}).get("agent_id") or "",
        obj.get("probing_directive_id"),
        obj.get("sequence_number"),
        obj.get("ip_version"),
        obj.get("protocol"),
        obj.get("source_address") or "",
        obj.get("destination_address") or "",
        near.get("probe_ttl") or 0,
        near.get("reply_address") or "",
        parse_timestamp(near.get("sent_timestamp") or ""),
        parse_timestamp(near.get("received_timestamp") or ""),
        far.get("probe_ttl") or 0,
        far.get("reply_address") or "",
        parse_timestamp(far.get("sent_timestamp") or ""),
        parse_timestamp(far.get("received_timestamp") or ""),
        parse_timestamp(obj.get("production_timestamp") or ""),
    )


def stream(duration: int, batch_size: int, db_file: Path, url: str) -> None:
    logger.info("Streaming to %s (batch size: %d)...", db_file, batch_size)

    con = sqlite3.connect(db_file)
    con.executescript(CREATE_SQL)

    batch: list[tuple] = []
    stop = threading.Event()

    def flush():
        if batch:
            con.executemany(INSERT_SQL, batch)
            con.commit()
            batch.clear()

    def _signal(sig, frame):
        stop.set()

    signal.signal(signal.SIGTERM, _signal)
    signal.signal(signal.SIGINT, _signal)

    timer = threading.Timer(duration, stop.set)
    timer.start()

    try:
        with httpx.stream("GET", url, timeout=None) as resp:
            buf = ""
            for chunk in resp.iter_bytes():
                if stop.is_set():
                    break
                buf += chunk.decode("utf-8", errors="replace")
                while "\n" in buf:
                    line, buf = buf.split("\n", 1)
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    batch.append(parse_record(obj))
                    if len(batch) >= batch_size:
                        flush()
    except (httpx.TimeoutException, httpx.ReadTimeout):
        pass
    finally:
        timer.cancel()

    flush()
    con.close()


def build_indexes(db_file: Path) -> None:
    logger.info("Building indexes...")
    con = sqlite3.connect(db_file)
    con.executescript(INDEX_SQL)
    con.close()
    logger.info("Indexes created.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch retina data from a stream.")
    parser.add_argument("duration", type=parse_duration, help="Stream duration (e.g. 10s, 5m, 1h, 2d, 1w)")
    parser.add_argument("--url", required=True, help="Stream endpoint URL")
    parser.add_argument("--db", required=True, type=Path, help="Output SQLite database file path")
    parser.add_argument("--batch-size", required=True, type=int, help="Number of rows per insert batch")
    args = parser.parse_args()

    args.db.parent.mkdir(parents=True, exist_ok=True)
    stream(args.duration, args.batch_size, args.db, args.url)
    logger.info("Streaming ended: %s", args.db)
    build_indexes(args.db)

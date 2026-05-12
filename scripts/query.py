#!/usr/bin/env .venv/bin/python3

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
import tracerouteanalysis as ta
logger = ta.get_logger(__name__)

import argparse
import sqlite3
import csv

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run a SQLite query and output results as CSV.")
    parser.add_argument("db", type=Path, help="Path to the SQLite database file")
    parser.add_argument("query", type=str, help="SQL query to run")
    args = parser.parse_args()

    if not args.db.exists():
        logger.error("Database file not found: %s", args.db)
        sys.exit(1)

    con = sqlite3.connect(args.db)
    cur = con.execute(args.query)

    writer = csv.writer(sys.stdout)
    writer.writerow([desc[0] for desc in cur.description])
    writer.writerows(cur.fetchall())

    con.close()

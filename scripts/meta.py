#!/usr/bin/env .venv/bin/python3

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
import tracerouteanalysis as ta
logger = ta.get_logger(__name__)

import argparse
import sqlite3
from datetime import datetime, timezone


def detect_platform(db: Path) -> ta.Platform:
    name = db.name.lower()
    if "retina" in name:
        return ta.Platform.RETINA
    elif "ark" in name:
        return ta.Platform.ARK
    elif "iris" in name:
        return ta.Platform.IRIS
    return ta.Platform.RETINA  # default


def generate_experiment(db: Path) -> ta.ExperimentMeta:
    platform = detect_platform(db)
    date_range = ("", "")
    timespan = 0.0
    num_elements = 0
    distinct_ipv4_addresses = 0
    distinct_ipv6_addresses = 0
    distinct_probing_directives = 0
    agent_ids = []
    table_type = ta.TableType.FIES  # default

    con = sqlite3.connect(db)

    # detect table type
    tables = {row[0] for row in con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    if "results" in tables:
        table_type = ta.TableType.RESULTS
    elif "fies" in tables:
        table_type = ta.TableType.FIES

    table = table_type.value

    if platform == ta.Platform.RETINA:
        row = con.execute(f"SELECT MIN(production_timestamp), MAX(production_timestamp) FROM {table}").fetchone()
        if row and row[0] and row[1]:
            t_min = datetime.fromisoformat(row[0])
            t_max = datetime.fromisoformat(row[1])
            date_range = (t_min.isoformat(), t_max.isoformat())
            timespan = float((t_max - t_min).total_seconds())

    num_elements = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]

    distinct_ipv4_addresses = con.execute(
        f"""SELECT COUNT(DISTINCT addr) FROM (
            SELECT near_reply_address AS addr FROM {table} WHERE ip_version = 4
            UNION
            SELECT far_reply_address AS addr FROM {table} WHERE ip_version = 4
        )"""
    ).fetchone()[0]

    distinct_ipv6_addresses = con.execute(
        f"""SELECT COUNT(DISTINCT addr) FROM (
            SELECT near_reply_address AS addr FROM {table} WHERE ip_version = 6
            UNION
            SELECT far_reply_address AS addr FROM {table} WHERE ip_version = 6
        )"""
    ).fetchone()[0]

    distinct_probing_directives = con.execute(
        f"SELECT COUNT(DISTINCT probing_directive_id) FROM {table}"
    ).fetchone()[0]

    agent_ids = [row[0] for row in con.execute(f"SELECT DISTINCT agent_id FROM {table}").fetchall()]

    con.close()

    return ta.ExperimentMeta(
        id=ta.Meta.new_id(),
        data_file=str(db),
        platform=platform,
        table_type=table_type,
        created_at=datetime.now(timezone.utc).isoformat(),
        date_range=date_range,
        timespan=timespan,
        num_elements=num_elements,
        distinct_ipv4_addresses=distinct_ipv4_addresses,
        distinct_ipv6_addresses=distinct_ipv6_addresses,
        distinct_probing_directives=distinct_probing_directives,
        agent_ids=agent_ids,
    )


def cmd_ls(args):
    meta = ta.Meta()
    experiments = meta.list_experiments()
    if not experiments:
        logger.info("No experiments found.")
        return

    header = f"{'ID':<36}  {'PLATFORM':<10}  {'TABLE':<10}  {'ELEMENTS':>10}  {'TIMESPAN':>10}  {'IPV4':>8}  {'IPV6':>8}  {'CREATED':<34}  {'FILE'}"
    print(header)
    print("-" * len(header))
    for exp in experiments:
        print(
            f"{exp.id:<36}  "
            f"{exp.platform.value:<10}  "
            f"{exp.table_type.value:<10}  "
            f"{exp.num_elements:>10}  "
            f"{exp.timespan:>10.1f}  "
            f"{exp.distinct_ipv4_addresses:>8}  "
            f"{exp.distinct_ipv6_addresses:>8}  "
            f"{exp.created_at:<34}  "
            f"{exp.data_file}"
        )

def cmd_add(args):
    db = Path(args.db)
    if not db.exists():
        logger.error("Database file not found: %s", db)
        sys.exit(1)

    meta = ta.Meta()
    exp = generate_experiment(db)

    if args.platform:
        exp.platform = ta.Platform(args.platform)
    if args.from_date:
        exp.date_range = (args.from_date, exp.date_range[1])
    if args.to_date:
        exp.date_range = (exp.date_range[0], args.to_date)

    meta.add_experiment(exp)
    logger.info("Added experiment %s (%s)", exp.id, db)


def cmd_reconcile(args):
    meta = ta.Meta()

    if args.force:
        old_ids = {exp.data_file: exp.id for exp in meta.list_experiments()}
        meta.experiments.clear()
        meta.save()
        logger.info("Cleared all existing experiments.")
    else:
        old_ids = {}

    db_files = {str(db) for db in Path("data").glob("*.db")}

    # remove experiments whose files no longer exist
    removed = 0
    for exp in meta.list_experiments():
        if exp.data_file not in db_files:
            meta.remove_experiment(exp.id)
            logger.info("Removed stale experiment %s (%s)", exp.id, exp.data_file)
            removed += 1

    known = {exp.data_file for exp in meta.list_experiments()}

    added = 0
    for db_str in db_files:
        if db_str in known:
            continue
        exp = generate_experiment(Path(db_str))
        if db_str in old_ids:
            exp.id = old_ids[db_str]
        meta.add_experiment(exp)
        logger.info("Reconciled: %s -> %s", db_str, exp.id)
        added += 1

    if added == 0 and removed == 0:
        logger.info("Nothing to reconcile.")
    else:
        logger.info("Reconciled %d new, removed %d stale database(s).", added, removed)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Interact with the traceroute analysis metadata.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # ls
    subparsers.add_parser("ls", help="List existing experiments")

    # add
    add_parser = subparsers.add_parser("add", help="Add a new experiment from a database file")
    add_parser.add_argument("db", type=str, help="Path to the SQLite database file")
    add_parser.add_argument("--platform", choices=["ark", "iris", "retina"], help="Override detected platform")

    # reconcile
    reconcile_parser = subparsers.add_parser("reconcile", help="Find untracked databases in data/ and add them")
    reconcile_parser.add_argument("--force", action="store_true", help="Clear all existing experiments and re-reconcile")

    args = parser.parse_args()

    if args.command == "ls":
        cmd_ls(args)
    elif args.command == "add":
        cmd_add(args)
    elif args.command == "reconcile":
        cmd_reconcile(args)

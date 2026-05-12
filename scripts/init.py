#!/usr/bin/env .venv/bin/python3

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
import tracerouteanalysis as ts

logger = ts.get_logger(__name__)

def main():
    # Initialize meta.json
    if not ts.DEFAULT_META_FILE.exists():
        logger.info("Creating %s...", ts.DEFAULT_META_FILE)
        ts.Meta()  # __post_init__ creates the file automatically
        logger.info("Created %s.", ts.DEFAULT_META_FILE)
    else:
        logger.info("%s already exists.", ts.DEFAULT_META_FILE)

    # Initialize ./data directory
    data_dir = Path("./data")
    if not data_dir.exists():
        data_dir.mkdir(parents=True)
        logger.info("Created data directory.")
    else:
        logger.info("data directory already exists.")


if __name__ == "__main__":
    main()

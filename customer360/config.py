from pathlib import Path
import os

ROOT = Path(__file__).resolve().parent.parent
DATA = Path(os.environ.get("C360_DATA_DIR", ROOT / "data"))
WAREHOUSE = DATA / "warehouse.duckdb"
OUTPUT = ROOT / "output"
COUNTRIES = ["US", "GB", "DE", "FR", "CA", "AU", "AE", "PK"]


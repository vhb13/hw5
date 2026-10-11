"""Reset the working database from the untouched original (for re-running tests)."""
import shutil
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
shutil.copyfile(DATA / "campus_customs.db", DATA / "campus_customs_new.db")
print("Reset data/campus_customs_new.db from data/campus_customs.db")

import subprocess
from pathlib import Path

DB_PATH = Path("nugamoto.sqlite")


def delete_database():
    if DB_PATH.exists():
        print(f"Deleting existing database: {DB_PATH}")
        DB_PATH.unlink()
    else:
        print("No existing database found. Skipping delete step.")


def run_initialization():
    print("Running database initialization...")
    subprocess.run(["python", "-m", "backend.db.init_db", "--reset"], check=True)


def run_seeding():
    print("Running seed script...")
    subprocess.run(["python", "-m", "backend.db.seed_db"], check=True)


if __name__ == "__main__":
    delete_database()
    run_initialization()
    run_seeding()
    print("✅ Done! Database reset, initialized, and seeded.")

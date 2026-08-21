from pathlib import Path
import sqlite3


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATABASE_PATH = PROJECT_ROOT / "instance" / "netflix_del_temu.sqlite3"


def main():
    connection = sqlite3.connect(DATABASE_PATH)

    connection.execute("PRAGMA foreign_keys = ON")

    tables = connection.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name NOT LIKE 'sqlite_%'
        ORDER BY name
        """
    ).fetchall()

    foreign_keys = connection.execute(
        "PRAGMA foreign_keys"
    ).fetchone()[0]

    integrity = connection.execute(
        "PRAGMA integrity_check"
    ).fetchone()[0]

    print(f"Base de datos: {DATABASE_PATH}")
    print(f"\nTablas encontradas: {len(tables)}")

    for table in tables:
        print(f" - {table[0]}")

    print(f"\nForeign Keys: {foreign_keys}")
    print(f"Integridad: {integrity}")

    connection.close()


if __name__ == "__main__":
    main()
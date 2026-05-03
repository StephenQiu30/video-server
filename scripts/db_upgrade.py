from app.db.session import engine
from app.db.upgrade import run_database_upgrades


def main() -> None:
    run_database_upgrades(engine)
    print("Database upgrade completed")


if __name__ == "__main__":
    main()

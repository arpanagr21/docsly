from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import create_app, seed_builtin_data
from app.extensions import db
from app.services.component_registry import rebuild_component_registry


def main() -> None:
    app = create_app()

    with app.app_context():
        db.drop_all()
        db.create_all()
        seed_builtin_data()
        rebuild_component_registry()
        print("Database reset complete. Built-in themes/components re-seeded.")


if __name__ == "__main__":
    main()

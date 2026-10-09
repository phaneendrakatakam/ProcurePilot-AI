from app.core.database import SessionLocal
from app.services.automation import run_automations


if __name__ == "__main__":
    with SessionLocal() as db:
        result = run_automations(db)
    print(result)

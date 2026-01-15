from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

def create_session(db_path: str):
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    engine = create_engine(f"sqlite:///{db_path}")
    Session = sessionmaker(bind=engine)

    return Session(), engine

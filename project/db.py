

from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import sessionmaker

from sqlmodel import SQLModel, create_engine
from models import Blacklist
from datetime import datetime
from sqlalchemy import update

engine = create_engine(
    'postgresql://postgres:postgres@db:5432/foo', convert_unicode=True,
    pool_recycle=1800, pool_size=12)
db_session = scoped_session(sessionmaker(
    autocommit=False, autoflush=False, bind=engine))


def init_db():
    trying=True
    while trying:
        if engine:
            try:
                SQLModel.metadata.create_all(engine)
                trying=False
            except Exception as e:
                print(e)

def commit_or_rollback(session, new_obj):
    try:
        session.add(new_obj)
        session.commit()
        session.refresh(new_obj)
    except Exception as e:
        print(e, "rolling back")
        session.rollback()
        return None
    return new_obj

def update_reason(session, to_update: Blacklist):
    try:
        stmt = update(Blacklist).where(Blacklist.wallet == to_update.wallet).values(reason=to_update.reason, added=datetime.utcnow().isoformat()).execution_options(synchronize_session="fetch")
        session.execute(stmt)
        session.commit()
    except Exception as e:
        print(e, "rolling back")
        session.rollback()
        return None
    return True

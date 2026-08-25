import os
import sqlalchemy as sa
engine = sa.create_engine(os.environ['DATABASE_URL'])
with engine.connect() as conn:
    res = conn.execute(sa.text("SELECT column_name FROM information_schema.columns WHERE table_name = 'cars' AND column_name = 'status'")).fetchall()
    print("status column:", res)

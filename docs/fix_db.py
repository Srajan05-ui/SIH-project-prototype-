import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()
engine = create_engine(os.environ["DATABASE_URL"])

with engine.connect() as conn:
    # 1. Delete all corrupt USD rows (price < 500) from both tables
    r1 = conn.execute(text("DELETE FROM fare_observations       WHERE price < 500;"))
    r2 = conn.execute(text("DELETE FROM fare_observations_clean WHERE price < 500;"))
    print(f"Deleted {r1.rowcount} raw + {r2.rowcount} clean corrupt USD rows")

    # 2. Add CHECK constraint so the database itself rejects any future USD insert
    # Use IF NOT EXISTS pattern (wrapped in a DO block to avoid error if already exists)
    conn.execute(text("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'price_minimum_inr'
            ) THEN
                ALTER TABLE fare_observations
                ADD CONSTRAINT price_minimum_inr CHECK (price IS NULL OR price >= 500);
            END IF;
        END $$;
    """))
    print("CHECK constraint 'price_minimum_inr' ensured on fare_observations")

    conn.commit()
    print("Done.")

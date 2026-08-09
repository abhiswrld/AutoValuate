"""
One-time script to re-derive make/model for every row from `name`,
using the shared vocab.py extractor. Run once, then re-run the training
notebook.
"""

import os
from sqlalchemy import create_engine, text
import pandas as pd
from dotenv import load_dotenv

from vocab import extract_make, extract_model

load_dotenv()


def repair_make_model(dry_run=True):
    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        print("Error: DATABASE_URL not set.")
        return

    engine = create_engine(DATABASE_URL)

    print("Pulling url/name/make/model for every row...")
    df = pd.read_sql("SELECT url, name, make, model FROM cars", engine)
    print(f"Loaded {len(df)} rows.")

    df['new_make'] = df['name'].apply(extract_make)
    df['new_model'] = df.apply(lambda r: extract_model(r['name'], r['new_make']), axis=1)

    # rows where the current value doesn't match what the extractor would produce
    changed = df[(df['make'] != df['new_make']) | (df['model'] != df['new_model'])].copy()
    changed = changed.dropna(subset=['new_make'])

    print(f"{len(changed)} / {len(df)} rows have make/model that disagree with the canonical vocab.")
    print(changed[['name', 'make', 'new_make', 'model', 'new_model']].head(15).to_string())

    if dry_run:
        print("\nDRY RUN -- no changes written. Re-run with dry_run=False to apply.")
        return

    print("\nWriting corrected make/model back to Supabase...")
    with engine.begin() as conn:
        for _, row in changed.iterrows():
            conn.execute(
                text("UPDATE cars SET make = :make, model = :model WHERE url = :url"),
                {"make": row['new_make'], "model": row['new_model'], "url": row['url']},
            )
    print(f"Repaired {len(changed)} rows.")


if __name__ == "__main__":
    # Flip to False once the printed diff above looks right.
    repair_make_model(dry_run=True)
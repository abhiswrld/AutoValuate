import os
import re
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

def get_known_models(project_root):
    try:
        avg_prices = pd.read_csv(os.path.join(project_root, 'api', 'avg_prices.csv'))
        return set(avg_prices['model'].dropna().str.lower().unique())
    except Exception as e:
        print(f"Error loading known models: {e}")
        return set()

def clean_model_string(raw_model):
    if not raw_model:
        return "unspecified"
    
    # Common misspellings and punctuation fixes
    clean_str = raw_model.lower().strip()
    
    # Remove random punctuation at the end (like 'ACCORD.')
    clean_str = re.sub(r'[,.\-]+$', '', clean_str)
    
    # Map common known bad strings
    mapping = {
        'crv': 'cr-v',
        'hrv': 'hr-v',
        'odessey': 'odyssey',
        'oddysey': 'odyssey',
        'odysey': 'odyssey',
    }
    
    if clean_str in mapping:
        return mapping[clean_str]
        
    return clean_str

def bulk_clean():
    print("Starting Bulk Clean of Model Strings...")
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    load_dotenv(os.path.join(project_root, '.env'))
    
    known_models = get_known_models(project_root)
    if not known_models:
        print("Could not load known models. Aborting.")
        return
        
    DATABASE_URL = os.getenv("DATABASE_URL")
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as conn:
        result = conn.execute(text("SELECT url, model FROM cars WHERE model IS NOT NULL"))
        all_cars = result.fetchall()
        
    print(f"Analyzing {len(all_cars)} total cars...")
    
    updates = []
    deleted_count = 0
    
    for url, original_model in all_cars:
        if not original_model:
            continue
            
        clean_model = clean_model_string(original_model)
        
        # If it's still extremely messy or long, let's try to extract the first word
        if len(clean_model) > 20 or ' ' in clean_model or '.' in clean_model:
            parts = clean_model.replace(',', ' ').replace('.', ' ').split()
            if parts:
                clean_model = parts[0]
        
        if clean_model != original_model.lower():
            if clean_model in known_models:
                # We can salvage it!
                updates.append((clean_model, url))
            else:
                # It's complete garbage and not in our known list
                deleted_count += 1
                with engine.begin() as conn:
                    conn.execute(text("DELETE FROM cars WHERE url = :url"), {"url": url})
                    
    print(f"Found {len(updates)} cars to clean.")
    print(f"Deleting {deleted_count} cars with unrecoverable alien models.")
    
    if updates:
        with engine.begin() as conn:
            for clean_m, u in updates:
                conn.execute(text("UPDATE cars SET model = :m, predicted_price = NULL WHERE url = :url"), {"m": clean_m, "url": u})
                
        print("Successfully updated database. Run `update_ai_prices()` to recalculate ML predictions.")

if __name__ == "__main__":
    bulk_clean()

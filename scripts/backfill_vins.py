import os
import sys
import time
import random
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Add parent directory to path so we can import scraper logic
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scraper.detail_scraper import get_car_details

def main():
    load_dotenv()
    engine = create_engine(os.getenv('DATABASE_URL'))
    
    print("Fetching cars with missing trim or vin...")
    with engine.connect() as conn:
        df = pd.read_sql("SELECT url FROM cars WHERE trim IS NULL OR vin IS NULL ORDER BY created_at DESC", conn)
        
    total_cars = len(df)
    print(f"Found {total_cars} cars to update.")
    
    if total_cars == 0:
        return
        
    for i, row in df.iterrows():
        url = row['url']
        print(f"[{i+1}/{total_cars}] Fetching {url}")
        
        try:
            res = get_car_details(url)
            if res:
                condition, title_status, factory_specs = res
                
                update_query = text("""
                    UPDATE cars 
                    SET condition = :condition, 
                        title_status = :title_status,
                        vin = :vin,
                        trim = :trim,
                        drive = :drive_type,
                        cylinders = :cylinders,
                        fuel = :fuel_type,
                        engine_size = :engine_size
                    WHERE url = :url
                """)
                
                params = {
                    'condition': condition,
                    'title_status': title_status,
                    'vin': factory_specs.get('vin'),
                    'trim': factory_specs.get('trim'),
                    'drive_type': factory_specs.get('drive_type'),
                    'cylinders': factory_specs.get('cylinders'),
                    'fuel_type': factory_specs.get('fuel_type'),
                    'engine_size': factory_specs.get('engine_size'),
                    'url': url
                }
                
                with engine.begin() as conn:
                    conn.execute(update_query, params)
                    
                print(f"  -> Success! VIN: {factory_specs.get('vin')} | Trim: {factory_specs.get('trim')}")
            else:
                print("  -> Failed to fetch details or listing was deleted. Marking as DELETED.")
                delete_query = text("UPDATE cars SET vin = 'DELETED', trim = 'DELETED' WHERE url = :url")
                with engine.begin() as conn:
                    conn.execute(delete_query, {'url': url})
                
        except Exception as e:
            print(f"  -> Error: {e}")
            if '404' in str(e) or '410' in str(e):
                print("  -> Marking as DELETED due to HTTP error.")
                delete_query = text("UPDATE cars SET vin = 'DELETED', trim = 'DELETED' WHERE url = :url")
                with engine.begin() as conn:
                    conn.execute(delete_query, {'url': url})
            
        # Avoid Craigslist IP ban by sleeping a random "human-like" amount
        jitter = random.uniform(1.5, 4.5)
        time.sleep(jitter)

if __name__ == "__main__":
    main()

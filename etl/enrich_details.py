import os
import pandas as pd
import time
import requests
from bs4 import BeautifulSoup
from sqlalchemy import create_engine, text

def get_car_details(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 403:
            return "BANNED"
        if response.status_code in [404, 410]:
            return "sold"
            
        response.raise_for_status()
    except Exception:
        return "sold"

    soup = BeautifulSoup(response.text, 'html.parser')

    # Check if deleted by author
    if soup.find('div', id='has_been_removed') or soup.find('h2', class_='removed'):
        return "sold", "sold"

    data = {
        'condition': None, 'title_status': None, 'cylinders': None,
        'drive': None, 'fuel': None, 'transmission': None, 'type': None
    }

    valid_makes = ['toyota', 'honda', 'ford', 'chevrolet', 'chevy', 'nissan', 'bmw', 'mercedes', 'benz', 'mercedes-benz', 'audi', 'lexus', 'subaru', 'volkswagen', 
                       'vw', 'hyundai', 'kia', 'mazda', 'acura', 'jeep', 'dodge', 'ram', 'gmc', 'cadillac', 'infiniti', 'volvo', 'mitsubishi', 'mini', 
                       'porsche', 'tesla', 'land', 'jaguar', 'chrysler', 'buick', 'pontiac', 'saturn', 'bentley', 'fiat']

    # 1. Scrape all attributes from the details page
    attr_divs = soup.find_all('div', class_='attr')
    for div in attr_divs:
        labl = div.find('span', class_='labl')
        valu = div.find('span', class_='valu')
        
        if labl and valu:
            key = labl.text.strip().lower().replace(':', '').strip()
            val = valu.text.strip().lower()
            
            if key == 'condition': data['condition'] = val
            elif key == 'title status': data['title_status'] = val
            elif key == 'cylinders': data['cylinders'] = val
            elif key == 'drive': data['drive'] = val
            elif key == 'fuel': data['fuel'] = val
            elif key == 'transmission': data['transmission'] = val
            elif key == 'type': data['type'] = val

    # 2. Scrape the perfect Make/Model/Trim (Checks for <a> tag or <span> text)
    makemodel_text = None
    
    # Try to find the <a> tag inside the span first
    makemodel_a = soup.select_one('span.valu.makemodel a')
    if makemodel_a:
        makemodel_text = makemodel_a.text.strip()
    else:
        # Fallback: Just grab the text from the span directly
        makemodel_span = soup.find('span', class_='valu makemodel')
        if makemodel_span:
            makemodel_text = makemodel_span.text.strip()
            
    # Parse the text if we found it
    if makemodel_text:
        parts = makemodel_text.split()
        
        # VALIDATION: Check if the first word is a real make
        if len(parts) > 0 and parts[0].lower() in valid_makes:
            data['make'] = parts[0].lower()
            data['model'] = parts[1].lower() if len(parts) > 1 else 'unspecified'
            
            if len(parts) > 2:
                data['trim'] = parts[2].lower()
            else:
                data['trim'] = 'unspecified'
        else:
            data['make'] = None
            data['model'] = None
            data['trim'] = 'unspecified'
    else:
        data['make'] = None
        data['model'] = None
        data['trim'] = 'unspecified'

    # 3. Extract City from the URL (Stops at year OR car make!)
    try:
        url_path = url.split('/view/d/')[1]
        parts = url_path.split('-')
        
        clean_city_parts = []
        for part in parts:
            if any(char.isdigit() for char in part):
                break
            if part.lower() in valid_makes:
                break
            clean_city_parts.append(part)
            
        if clean_city_parts:
            clean_city = ' '.join(clean_city_parts)
            data['location'] = clean_city.lower()
    except:
        pass

    return data

def enrich_database():
    print("Starting Database Enrichment Process")
    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        print("Error: DATABASE_URL environment variable is not set.")
        return

    engine = create_engine(DATABASE_URL)

    # Automatically add ALL columns if they don't exist yet
    with engine.connect() as conn:
        conn.execute(text("ALTER TABLE cars ADD COLUMN IF NOT EXISTS condition TEXT;"))
        conn.execute(text("ALTER TABLE cars ADD COLUMN IF NOT EXISTS title_status TEXT;"))
        conn.execute(text("ALTER TABLE cars ADD COLUMN IF NOT EXISTS cylinders TEXT;"))
        conn.execute(text("ALTER TABLE cars ADD COLUMN IF NOT EXISTS drive TEXT;"))
        conn.execute(text("ALTER TABLE cars ADD COLUMN IF NOT EXISTS fuel TEXT;"))
        conn.execute(text("ALTER TABLE cars ADD COLUMN IF NOT EXISTS transmission TEXT;"))
        conn.execute(text("ALTER TABLE cars ADD COLUMN IF NOT EXISTS type TEXT;"))
        conn.execute(text("ALTER TABLE cars ADD COLUMN IF NOT EXISTS trim TEXT;"))
        conn.commit()

    # Grab cars where the new deep-scrape features are missing
    with engine.connect() as connection:
        query = text("SELECT url FROM cars WHERE cylinders IS NULL ORDER BY url DESC LIMIT 1000")
        result = connection.execute(query)
        cars_to_update = result.fetchall()

    total_cars = len(cars_to_update)
    print(f"Found {total_cars} cars to enrich. Estimated time: {total_cars * 1 / 60} minutes.")

    updated_count = 0
    for i, car in enumerate(cars_to_update):
        url = car[0]
        print(f"[{i+1}/{total_cars}] Scraping: {url}")

        details = get_car_details(url)

        if details == "BANNED":
            print(" -> 403 Forbidden detected. Stopping script to protect data.")
            break
        elif details == "sold":
            print(" -> Sold/Deleted")
            with engine.begin() as conn:
                conn.execute(text("UPDATE cars SET condition = 'sold', title_status = 'sold' WHERE url = :url"), {"url": url})
        else:
            print(f" -> Success: {details.get('make')} {details.get('model')} {details.get('trim')}")
            with engine.begin() as conn:
                update_query = text("""
                    UPDATE cars 
                    SET condition = :cond, title_status = :title, 
                        cylinders = :cyl, drive = :drive, fuel = :fuel, 
                        transmission = :trans, type = :type,
                        make = :make, model = :model, trim = :trim
                    WHERE url = :url
                """)
                conn.execute(update_query, {
                    "cond": details.get('condition'),
                    "title": details.get('title_status'),
                    "cyl": details.get('cylinders'),
                    "drive": details.get('drive'),
                    "fuel": details.get('fuel'),
                    "trans": details.get('transmission'),
                    "type": details.get('type'),
                    "make": details.get('make'),
                    "model": details.get('model'),
                    "trim": details.get('trim'),
                    "url": url
                })
                updated_count += 1

        time.sleep(1)
    
    # Clean up dead listings to keep the database fast and accurate
    print("\nCleaning up sold/deleted listings...")
    with engine.begin() as conn:
        result = conn.execute(text("DELETE FROM cars WHERE condition = 'sold'"))
        print(f"Deleted {result.rowcount} sold/deleted listings from the database.")

    print(f"Enrichment process completed. Updated {updated_count} out of {total_cars} cars.")

if __name__ == "__main__":
    enrich_database()
import os
import pandas as pd
import time
import requests
from bs4 import BeautifulSoup
from sqlalchemy import create_engine, text

def get_car_details(url):
    """
    Scrapes the car details from a given Craigslist listing URL.
    
    Args:
        url (str): The URL of the Craigslist car listing."""

    # Set a User-Agent so Craigslist thinks we are a real browser
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 403:
            return "BANNED", "BANNED"
        if response.status_code in [404, 410]:
            return "sold", "sold"
            
        response.raise_for_status()
    except Exception:
        return "sold", "sold"
            
        response.raise_for_status()
    except Exception:
        return "sold", "sold"

    soup = BeautifulSoup(response.text, 'html.parser')

    # Check if deleted by author
    if soup.find('div', id='has_been_removed') or soup.find('h2', class_='removed'):
        return "sold", "sold"

    data = {
        'condition': None, 'title_status': None, 'cylinders': None,
        'drive': None, 'fuel': None, 'transmission': None, 'type': None
    }

    # 1. Scrape all attributes from the details page
    attr_groups = soup.find_all('p', class_='attrgroup')
    for group in attr_groups:
        spans = group.find_all('span')
        for span in spans:
            text = span.text.strip().lower()
            if ':' in text:
                key, val = text.split(':', 1)
                key = key.strip()
                val = val.strip()
                
                # Map the text to our database columns
                if key == 'condition': data['condition'] = val
                elif key == 'title status': data['title_status'] = val
                elif key == 'cylinders': data['cylinders'] = val
                elif key == 'drive': data['drive'] = val
                elif key == 'fuel': data['fuel'] = val
                elif key == 'transmission': data['transmission'] = val
                elif key == 'type': data['type'] = val

    # 2. Scrape the perfect Make/Model/Trim from the span
    makemodel_tag = soup.find('span', class_='valu makemodel')
    if makemodel_tag:
        makemodel_text = makemodel_tag.text.strip()
        # Split into parts: Make, Model, Trim
        parts = makemodel_text.split()
        
        # FORCE LOWERCASE for perfect consistency!
        data['make'] = parts[0].lower() if len(parts) > 0 else None
        data['model'] = parts[1].lower() if len(parts) > 1 else None
        
        # If there's a 3rd word, treat it as the trim. Otherwise, 'unspecified'
        if len(parts) > 2:
            data['trim'] = parts[2].lower()
        else:
            data['trim'] = 'unspecified'
    else:
        data['make'] = None
        data['model'] = None
        data['trim'] = 'unspecified'

    # If condition is missing, mark as unspecified
    if not data['condition']:
        data['condition'] = 'unspecified'
    if not data['title_status']:
        data['title_status'] = 'unspecified'

    return data

def enrich_database():
    """
    Enriches the database by scraping car details for each listing in the 'listings' table.
    Updates the 'condition' and 'title_status' fields in the database.
    """

    print("Starting Database Enrichment Process")
    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        print("Error: DATABASE_URL environment variable is not set.")
        return

    engine = create_engine(DATABASE_URL)

    # Automatically add the columns if they were wiped out by a fresh upload
    with engine.connect() as conn:
        conn.execute(text("ALTER TABLE cars ADD COLUMN IF NOT EXISTS condition TEXT;"))
        conn.execute(text("ALTER TABLE cars ADD COLUMN IF NOT EXISTS title_status TEXT;"))
        conn.commit()

    # Grab 500 listings from the database
    with engine.connect() as connection:
        query = text("SELECT url FROM cars WHERE condition IS NULL ORDER BY url DESC LIMIT 500")
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
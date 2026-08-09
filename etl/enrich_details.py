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
        # If we get a 403, we are banned! Return a special flag.
        if response.status_code == 403:
            return "BANNED", "BANNED"
        # If it's a 404 or 410, the car is sold
        if response.status_code in [404, 410]:
            return "sold", "sold"
            
        response.raise_for_status()
    except Exception:
        return "sold", "sold"

    soup = BeautifulSoup(response.text, 'html.parser')

    # Default values if we can't find the data
    condition = None
    title_stats = None

    # Extract condition
    condition_tag = soup.find('div', class_='attr condition')
    if condition_tag:
        condition = condition_tag.find('span', class_='valu')
        if condition:
            condition = condition.text.strip()

    # Extract title status
    title_stats_tag = soup.find('div', class_='attr auto_title_status')
    if title_stats_tag:
        title_stats = title_stats_tag.find('span', class_='valu')
        if title_stats:
            title_stats = title_stats.text.strip()

    # If the page loaded fine but seller didn't fill out the condition, mark as 'unspecified'
    # This prevents the main loop from marking live cars as 'sold'
    final_cond = condition if condition else "unspecified"
    final_title = title_stats if title_stats else "unspecified"

    return final_cond, final_title

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

        condition, title_status = get_car_details(url)

        # Print what we found
        if condition == "BANNED":
            print(" -> 403 Forbidden detected. Stopping script to protect data.")
            break
        elif condition == "sold":
            print(" -> Sold/Deleted")
        else:
            print(f" -> Success: Condition: {condition}, Title: {title_status}")

        # Update specific car entry in the database
        with engine.begin() as conn:
            update_query = text("""
                UPDATE cars 
                SET condition = :cond, title_status = :title 
                WHERE url = :url
            """)
            conn.execute(update_query, {"cond": condition, "title": title_status, "url": url})
            
            if condition != "sold":
                updated_count += 1

        # Sleep for 1 second to avoid overwhelming the server
        time.sleep(1)
    
    # Clean up dead listings to keep the database fast and accurate
    print("\nCleaning up sold/deleted listings...")
    with engine.begin() as conn:
        result = conn.execute(text("DELETE FROM cars WHERE condition = 'sold'"))
        print(f"Deleted {result.rowcount} sold/deleted listings from the database.")

    print(f"Enrichment process completed. Updated {updated_count} out of {total_cars} cars.")

if __name__ == "__main__":
    enrich_database()
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import pandas as pd
import time
import os

def scrape_craigslist():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        page.set_extra_http_headers({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
        })
        
        # Top 10 US Craigslist Regions
        regions = [
            'sfbay', 'losangeles', 'newyork', 'seattle', 'chicago', 
            'dallas', 'miami', 'atlanta', 'boston', 'phoenix'
        ]
        
        all_cars_data = []
        
        for region in regions:
            print(f"\nNavigating to Craigslist {region.upper()}...")
            url = f"https://{region}.craigslist.org/search/cto"
            
            try:
                page.goto(url, timeout=15000)
                page.wait_for_selector(".cl-search-result", timeout=10000)
                print(f"Initial listings loaded for {region.upper()}. Starting scroll loop...")
            except Exception as e:
                print(f"Failed to load {region.upper()}. Skipping. Error: {e}")
                continue
            
            # 15 loops per region to get ~300-500 cars each without taking all day
            for i in range(15):
                print(f"Scrolling {region.upper()}... (Iteration {i + 1}/15)")
                
                # 1. Grab the HTML currently on the screen
                html = page.content()
                soup = BeautifulSoup(html, "html.parser")
                listings = soup.find_all("div", class_="cl-search-result cl-search-view-mode-gallery")
                
                # 2. Extract data from these visible listings
                for listing in listings:
                    data = extract_listing_data(listing)
                    if data:
                        data['region'] = region
                        all_cars_data.append(data)
                
                # 3. Scroll down using the MOUSE WHEEL
                page.mouse.wheel(0, 10000)
                
                # 4. Wait 3 seconds for the new batch to load
                time.sleep(3)
                
            # Need to wait a bit before moving to the next region to avoid being flagged as a bot
            time.sleep(2)
        
        print("\nDone scrolling all regions. Saving data...\n")
        browser.close()
        
        # Deduplicate the data
        df = pd.DataFrame(all_cars_data)
        df = df.drop_duplicates(subset=['url'])

        save_to_csv(df.to_dict('records'), "data/raw_listings.csv")

def extract_listing_data(listing):
    # 1. Find the title of the vehicle
    title_tag = listing.find("span", class_="label")
    if not title_tag:
        return None  # Skip if no title
    title_text = title_tag.text.strip().title()
    
    # 2. Find the link of the vehicle
    link_tag = listing.find("a", href=True)
    if not link_tag:
        return None  # Skip if no link
    url = link_tag.get('href')

    # 3. Find the price of the vehicle
    price_tag = listing.find("span", class_="priceinfo")
    if not price_tag:
        return None  # Skip if no price tag
    
    price_text = price_tag.text
    price_text = price_text.replace("$", "").replace(",", "").strip()
    
    try:
        price = int(price_text)
    except ValueError:
        return None  # Skip if the price isn't a valid number

    # 4. Get the miles driven on the vehicle
    mileage = None
    meta_div = listing.find("div", class_="meta")
    if meta_div:
        for content in meta_div.contents:
            # bare text nodes come through as NavigableString, not Tag
            if isinstance(content, str):
                text = content.strip()
                if text.lower().endswith("mi"):
                    has_k = 'k' in text.lower()
                    clean_text = ''.join(char for char in text if char.isdigit())
                    
                    if clean_text:
                        mileage = int(clean_text)
                        if has_k:
                            mileage = mileage * 1000
                    break

    # 5. Get the location the car is being sold in
    location_tag = listing.find("span", class_="result-location")
    if not location_tag:
        return None

    # Clean up the sub-city (e.g., "san jose downtown" -> "San Jose Downtown")
    location = location_tag.text.strip().lower()

    # 6. Create and return dictionary
    vehicle_stats = {
        "name": title_text,
        "url": url,
        "price": price,
        "mileage": mileage,
        "location": location
    }

    return vehicle_stats

def save_to_csv(data, filename):
    # 1. Convert the newly scraped data into a DataFrame
    new_df = pd.DataFrame(data)
    
    # 2. Try to read the existing CSV
    if os.path.exists(filename):
        old_df = pd.read_csv(filename)
        print(f"Found {len(old_df)} existing cars in the database.")
        
        # 3. Glue the old data and new data together
        combined_df = pd.concat([old_df, new_df], ignore_index=True)
        
        # 4. Drop duplicates based on the URL (keeps the first occurrence)
        combined_df = combined_df.drop_duplicates(subset=['url'])
        
        print(f"Added {len(combined_df) - len(old_df)} new unique cars today!")
    else:
        # If the file doesn't exist yet, just use the new data
        print("No existing database found. Creating a new one.")
        combined_df = new_df.drop_duplicates(subset=['url'])
        
    # 5. Save the final combined database back to the CSV
    combined_df.to_csv(filename, index=False)
    print(f"Total unique cars in database: {len(combined_df)}")
    
if __name__ == "__main__":
    scrape_craigslist()
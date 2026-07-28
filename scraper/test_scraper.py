from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import pandas as pd
import time

def scrape_craigslist():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        page.set_extra_http_headers({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
        })
        
        print("Navigating to Craigslist...")
        page.goto("https://sfbay.craigslist.org/search/cto")
        page.wait_for_selector(".cl-search-result")
        print("Initial listings loaded. Starting scroll loop...")
        
        all_cars_data = []
        
        for i in range(30):
            print(f"Scrolling... (Iteration {i + 1}/30)")
            
            # 1. Grab the HTML currently on the screen
            html = page.content()
            soup = BeautifulSoup(html, "html.parser")
            listings = soup.find_all("div", class_="cl-search-result cl-search-view-mode-gallery")
            
            # 2. Extract data from these visible listings
            for listing in listings:
                data = extract_listing_data(listing)
                if data:
                    all_cars_data.append(data)
            
            # 3. Scroll down using the MOUSE WHEEL (Much more reliable!)
            page.mouse.wheel(0, 10000)
            
            # 4. Wait 3 seconds for the new batch to load
            time.sleep(3)
        
        print("Done scrolling. Saving data...\n")
        
        # Deduplicate the data
        df = pd.DataFrame(all_cars_data)
        df = df.drop_duplicates(subset=['url'])

        save_to_csv(df.to_dict('records'), "data/raw_listings.csv")

        browser.close()

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

    # 4. Create and return dictionary
    vehicle_stats = {
        "name": title_text,
        "url": url,
        "price": price
    }

    return vehicle_stats

def save_to_csv(data, filename):
    df = pd.DataFrame(data)
    df.to_csv(filename, index=False)
    print(f"Saved {len(df)} unique cars to {filename}")
    print(df.head())

if __name__ == "__main__":
    scrape_craigslist()
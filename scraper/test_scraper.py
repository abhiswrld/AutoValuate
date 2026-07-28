from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import pandas as pd

def scrape_craigslist():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        page.set_extra_http_headers({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
        })
        
        print("Navigating to Craigslist...")
        page.goto("https://sfbay.craigslist.org/search/cto")
        
        # Wait for the listings to load
        page.wait_for_selector(".cl-search-result")
        
        html = page.content()
        soup = BeautifulSoup(html, "html.parser")
        
        # Find the span tags with class "cl-search-result cl-search-view-mode-gallery" based on Craigslist website.
        listings = soup.find_all("div", class_="cl-search-result cl-search-view-mode-gallery")
        
        print(f"\nFound {len(listings)} listings! Here are the first 5:")
        print("-" * 41)

        all_cars_data = []
        
        for listing in listings:
            # Catch the dictionary returned by the function
            data = extract_listing_data(listing)

            if data:
                all_cars_data.append(data)

        save_to_csv(all_cars_data, "data/raw_listings.csv")

        browser.close()

def extract_listing_data(listing):
    # 1. Find the title of the vehicle
    title_tag = listing.find("span", class_="label")
    title_text = title_tag.text.strip().title()
    
    # 2. Find the link of the vehicle
    link_tag = listing.find("a", href=True)
    url = link_tag.get('href')

    # 3. Find the price of the vehicle
    price_tag = listing.find("span", class_="priceinfo")
    price_text = price_tag.text
    
    price_text = price_text.replace("$", "").replace(",", "").strip()
    try:
        price = int(price_text)
    except ValueError:
        return None

    # 4. Create and return dictionary with all the information.
    vehicle_stats = {
        "name": title_text,
        "url": url,
        "price": price
    }

    return vehicle_stats

def save_to_csv(data, filename):
    df = pd.DataFrame(data)
    df.to_csv(filename, index=False)
    print(df.head())


if __name__ == "__main__":
    scrape_craigslist()
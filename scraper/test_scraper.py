from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

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
        print("-" * 30)
        
        for listing in listings[:5]:
            # 1. Find the title of the car using the specific class "label"
            title_tag = listing.find("span", class_="label")
            title_text = title_tag.text.strip().title()
            print(f"Title: {title_text}")

            # 2. Find the link of the car using the specific class ""
            link_tag = listing.find("a", href=True)
            print(f"URL: {link_tag.get('href')}")
            
            print("-" * 30)
            
        browser.close()

if __name__ == "__main__":
    scrape_craigslist()
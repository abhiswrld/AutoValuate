import requests
from bs4 import BeautifulSoup
import time
import re
import random

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/113.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1"
]

def get_car_details(url):
    """
    Scrapes the car details from a given Craigslist listing URL.
    
    Args:
        url (str): The URL of the Craigslist car listing."""

    headers = {
        "User-Agent": random.choice(USER_AGENTS)
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status() # Raise an error for bad responses, hopefully getting information about removed posts.
    except requests.RequestException as e:
        print(f"Error fetching details for {url}: {e}")
        return None

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

    # Fallback to attrgroup search for title status if needed
    if not title_stats:
        for span in soup.select('.attrgroup span'):
            if 'title status:' in span.text.lower():
                b_tag = span.find('b')
                if b_tag:
                    title_stats = b_tag.text.strip()

    # Extract VIN using regex (17 characters, excluding I, O, Q)
    vin = None
    vin_match = re.search(r'\b([A-HJ-NPR-Z0-9]{17})\b', soup.text)
    if vin_match:
        vin = vin_match.group(1)

    factory_specs = {
        'vin': vin,
        'trim': None,
        'drive_type': None,
        'cylinders': None,
        'fuel_type': None,
        'engine_size': None
    }

    # Decode VIN using NHTSA API
    if vin:
        try:
            vin_url = f"https://vpic.nhtsa.dot.gov/api/vehicles/DecodeVin/{vin}?format=json"
            vin_resp = requests.get(vin_url, timeout=5)
            if vin_resp.status_code == 200:
                vin_data = vin_resp.json().get('Results', [])
                for item in vin_data:
                    var = item.get('Variable')
                    val = item.get('Value')
                    if val and str(val).lower() != 'not applicable':
                        if var == 'Trim':
                            factory_specs['trim'] = val
                        elif var == 'Drive Type':
                            factory_specs['drive_type'] = val
                        elif var == 'Engine Number of Cylinders':
                            factory_specs['cylinders'] = val
                        elif var == 'Fuel Type - Primary':
                            factory_specs['fuel_type'] = val
                        elif var == 'Displacement (L)':
                            factory_specs['engine_size'] = val
        except Exception as e:
            print(f"Failed to decode VIN {vin}: {e}")

    return condition, title_stats, factory_specs

if __name__ == "__main__":
    import sys
    # Allow passing a URL via command line argument to test a specific car easily
    test_url = sys.argv[1] if len(sys.argv) > 1 else "https://sfbay.craigslist.org/sfc/cto/d/san-francisco-2015-toyota-camry-xle/7864388107.html"
    
    print(f"Fetching details for: {test_url}")
    res = get_car_details(test_url)
    if res:
        condition, title_status, factory_specs = res
        print(f"\nExtracted from Page:")
        print(f"Condition: {condition}")
        print(f"Title Status: {title_status}")
        print(f"\nDecoded from NHTSA VIN API:")
        for k, v in factory_specs.items():
            print(f"{k.capitalize()}: {v}")
    else:
        print("Failed to fetch car details or listing was deleted.")
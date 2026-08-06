import requests
from bs4 import BeautifulSoup
import time

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

    return condition, title_stats

if __name__ == "__main__":
    # Example usage
    test_url = "https://www.craigslist.org/view/d/palo-alto-2006-dodge-ram-x4-diesel/2RLmprDQrsbtULxKB6CeBr"
    print(f"Fetching details for: {test_url}")
    condition, title_status = get_car_details(test_url)
    print(f"Condition: {condition}")
    print(f"Title Status: {title_status}")
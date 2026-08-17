import os
import time
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))

DATABASE_URL = os.getenv("DATABASE_URL")
RESEND_API_KEY = os.getenv("RESEND_API_KEY")

if not DATABASE_URL:
    print("DATABASE_URL is not set.")
    exit(1)

engine = create_engine(DATABASE_URL)

def get_watched_cars():
    """Fetch unique URLs currently in watchlists, joined with their DB prices."""
    query = """
        SELECT DISTINCT w.car_url, c.price, c.make, c.model, c.year 
        FROM watchlist w
        JOIN cars c ON w.car_url = c.url
        WHERE c.price IS NOT NULL
    """
    with engine.connect() as conn:
        result = conn.execute(text(query))
        return [dict(row._mapping) for row in result]

def get_live_price(url):
    """Fetch the Craigslist page and extract the live price."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
    }
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 404:
            return -1 # Deleted/Sold
        
        soup = BeautifulSoup(r.text, "html.parser")
        price_span = soup.find("span", class_="price")
        if price_span:
            price_text = price_span.text.replace("$", "").replace(",", "").strip()
            if price_text.isdigit():
                return int(price_text)
    except Exception as e:
        print(f"Error fetching {url}: {e}")
    return None

def get_users_watching(url):
    """Fetch email addresses of users watching this specific URL."""
    # Supabase auth.users is in a separate schema (auth)
    # We join public.watchlist with auth.users
    query = """
        SELECT au.email 
        FROM public.watchlist w
        JOIN auth.users au ON w.user_id = au.id
        WHERE w.car_url = :url
    """
    with engine.connect() as conn:
        result = conn.execute(text(query), {"url": url})
        return [row[0] for row in result]

def send_price_drop_email(email, car_details, old_price, new_price):
    """Send HTML email using Resend API."""
    if not RESEND_API_KEY:
        print("RESEND_API_KEY not found. Skipping email to:", email)
        return

    drop_amount = old_price - new_price
    car_title = f"{car_details['year']} {car_details['make'].title()} {car_details['model'].title()}"
    
    html_content = f"""
    <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e5e7eb; border-radius: 12px;">
        <h2 style="color: #111827; margin-bottom: 20px;">Price Drop Alert!</h2>
        <p style="color: #374151; font-size: 16px;">Great news! A car on your AutoValuate watchlist just dropped in price.</p>
        
        <div style="background-color: #f3f4f6; padding: 20px; border-radius: 8px; margin: 20px 0;">
            <h3 style="margin: 0 0 10px 0; color: #111827;">{car_title}</h3>
            <p style="margin: 5px 0; color: #4b5563; text-decoration: line-through;">Old Price: ${old_price:,}</p>
            <p style="margin: 5px 0; color: #10b981; font-size: 20px; font-weight: bold;">New Price: ${new_price:,}</p>
            <p style="margin: 10px 0 0 0; color: #374151; font-weight: bold;">Total Drop: ${drop_amount:,}</p>
        </div>
        
        <a href="{car_details['car_url']}" style="display: inline-block; background-color: #4f46e5; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold; margin-top: 10px;">View Listing on Craigslist</a>
        
        <p style="margin-top: 30px; font-size: 12px; color: #9ca3af;">You are receiving this because you saved this car on AutoValuate.</p>
    </div>
    """

    payload = {
        "from": "AutoValuate Alerts <onboarding@resend.dev>",
        "to": [email],
        "subject": f"Price Drop: {car_title} down by ${drop_amount:,}!",
        "html": html_content
    }
    
    headers = {
        "Authorization": f"Bearer {RESEND_API_KEY}",
        "Content-Type": "application/json"
    }
    
    response = requests.post("https://api.resend.com/emails", json=payload, headers=headers)
    if response.status_code in [200, 201]:
        print(f"Successfully sent alert to {email}")
    else:
        print(f"Failed to send email to {email}: {response.text}")

def update_db_price(url, new_price):
    query = "UPDATE cars SET price = :price WHERE url = :url"
    with engine.begin() as conn:
        conn.execute(text(query), {"price": new_price, "url": url})
        
def process_watchlist():
    print("Starting Watchlist Price Drop Worker...")
    watched_cars = get_watched_cars()
    print(f"Found {len(watched_cars)} unique cars being watched.")
    
    for car in watched_cars:
        url = car['car_url']
        db_price = car['price']
        print(f"Checking {url} (DB Price: ${db_price})")
        
        live_price = get_live_price(url)
        time.sleep(1.5) # Rate limit respect
        
        if live_price == -1:
            print("  -> Car was deleted/sold (404). Handled by sweeper.")
            continue
            
        if live_price is None:
            print("  -> Could not extract price. Skipping.")
            continue
            
        if live_price < db_price:
            print(f"  -> PRICE DROP DETECTED! ${db_price} -> ${live_price}")
            
            # 1. Update the database
            update_db_price(url, live_price)
            
            # 2. Notify users
            users = get_users_watching(url)
            for email in users:
                send_price_drop_email(email, car, db_price, live_price)
                time.sleep(0.5) # Limit email send rate
        else:
            print(f"  -> No drop. Live Price: ${live_price}")

if __name__ == "__main__":
    process_watchlist()

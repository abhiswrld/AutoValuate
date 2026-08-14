from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
import pandas as pd
import joblib
import re
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from fastapi.middleware.cors import CORSMiddleware
import datetime
import os
from fastapi import Response
from sqlalchemy import create_engine, text
import uuid
from typing import List

# 1. Initialize the App
app = FastAPI(title="AutoValuate API")

@app.get("/")
def read_root():
    return {"status": "AutoValuate API is running!"}

@app.api_route("/health", methods=["GET", "HEAD"])
def health_check():
    return Response(status_code=200)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. Load the ML Artifacts
print("Loading ML models...")
model = joblib.load('api/model.pkl')
ohe = joblib.load('api/ohe.pkl')
model_columns = joblib.load('api/model_columns.pkl')
print("Models loaded successfully!")

# 3. Initialize Database Connection
DATABASE_URL = os.getenv("DATABASE_URL")
db_engine = create_engine(DATABASE_URL) if DATABASE_URL else None
print("Database engine created!")

# 4. In-Memory Job Queue for Async Tasks
jobs = {}

# 5. Define Input Schemas
class URLData(BaseModel):
    url: str

valid_makes = ['toyota', 'honda', 'ford', 'chevrolet', 'chevy', 'nissan', 'bmw', 'mercedes', 'benz', 'audi', 'lexus', 'subaru', 'volkswagen', 'vw', 
               'hyundai', 'kia', 'mazda', 'acura', 'jeep', 'dodge', 'ram', 'gmc', 'cadillac', 'infiniti', 'volvo', 'mitsubishi', 'mini', 'porsche', 
               'tesla', 'land', 'jaguar', 'chrysler', 'buick', 'pontiac', 'saturn', 'bentley', 'fiat']

# Region cities whitelist removed; locations are now cleanly stored in the database.

# Helper to format car names nicely (e.g., "toyota rav4" -> "Toyota RAV4")
def format_car_name(year, make, model, trim=None):
    y = str(year).strip() if year else ""
    m = make.title() if make else ""
    mo = model.title() if model else ""
    t = trim.title() if trim and trim != 'unspecified' else ""
    
    # List of models/trims that should be fully uppercase
    uppercase_acronyms = [
        "Rav4", "Cr-V", "Crv", "Hr-V", "Hrv", "Cr-Z", "Crz", 
        "Nx", "Rx", "Gs", "Is", "Gx", "Lx", "Ls", "Es", "Ux", "Rc", 
        "Mdx", "Rdx", "Tlx", "Ilx", "Tsx", "Rsx", "Rlx", "Zdx", "Nsx",
        "Gti", "Amg", "Se", "Le", "Xle", "Ex", "Sxt", "Rt", "Gt", "Gts",
        "Srt", "Suv", "Awg", "4wd", "2wd", "Rwd", "Fwd", "Trd"
    ]
    
    # Replace acronyms in model and trim
    for acr in uppercase_acronyms:
        if mo == acr:
            mo = acr.upper()
        if t == acr:
            t = acr.upper()
            
    name = f"{y} {m} {mo}".strip()
    if t:
        name += f" {t}"
        
    return name.strip()

def extract_specs_from_soup(soup):
    """Extracts all perfect features from the Craigslist details page HTML."""
    data = {
        'condition': 'unspecified', 'title_status': 'unspecified', 'cylinders': 'unspecified',
        'drive': 'unspecified', 'fuel': 'unspecified', 'transmission': 'unspecified', 'type': 'unspecified'
    }
    
    attr_divs = soup.find_all('div', class_='attr')
    for div in attr_divs:
        labl = div.find('span', class_='labl')
        valu = div.find('span', class_='valu')
        if labl and valu:
            key = labl.text.strip().lower().replace(':', '').strip()
            val = valu.text.strip().lower()
            if key in data:
                data[key] = val

    # Make/Model/Trim
    data['make'] = None
    data['model'] = None
    data['trim'] = 'unspecified'
    
    makemodel_tag = soup.find('span', class_='valu makemodel')
    if makemodel_tag:
        parts = makemodel_tag.text.strip().split()
        if len(parts) > 0 and parts[0].lower() in valid_makes:
            data['make'] = parts[0].lower()
            data['model'] = parts[1].lower() if len(parts) > 1 else 'unspecified'
            if len(parts) > 2:
                data['trim'] = parts[2].lower()
                
    return data

# --- ENDPOINTS ---

@app.post("/evaluate_url")
def evaluate_url(url_data: URLData, background_tasks: BackgroundTasks):
    url = url_data.url
    job_id = str(uuid.uuid4())
    jobs[job_id] = {"status": "pending"}
    background_tasks.add_task(process_url_task, job_id, url)
    return {"job_id": job_id}

def process_url_task(job_id: str, url: str):
    try:
        if not url.startswith("http") or "craigslist.org" not in url:
            jobs[job_id] = {"status": "failed", "error": "Not a valid URL. Please paste a full Craigslist listing link."}
            return
            
        # 1. Scrape the live URL
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_extra_http_headers({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"})
            
            try:
                page.goto(url, timeout=15000)
                page.wait_for_selector("h1.postingtitle", timeout=10000)
                html = page.content()
                soup = BeautifulSoup(html, "html.parser")
                browser.close()
            except Exception as e:
                browser.close()
                jobs[job_id] = {"status": "failed", "error": "Could not reach the listing. It may have been deleted."}
                return

        # 2. Extract Title and Price
        title_tag = soup.find("h1", class_="postingtitle")
        if not title_tag:
            jobs[job_id] = {"status": "failed", "error": "Could not find posting title."}
            return
        
        full_title_text = title_tag.text.strip()
        price_match = re.search(r'\$([\d,]+)', full_title_text)
        if not price_match:
            jobs[job_id] = {"status": "failed", "error": "Could not find a valid price."}
            return
        
        price_str = price_match.group(1).replace(',', '')
        try:
            listing_price = int(price_str)
        except ValueError:
            jobs[job_id] = {"status": "failed", "error": "Invalid price format."}
            return

        title_text = re.sub(r'\$[\d,]+', '', full_title_text).strip().title()

        # 3. Extract Mileage
        mileage = None
        miles_div = soup.find("div", class_="attr auto_miles")
        if miles_div:
            value_span = miles_div.find("span", class_="valu")
            if value_span:
                mileage_str = value_span.text.replace(',', '').strip()
                try:
                    mileage = float(mileage_str)
                except:
                    pass

        # 4. Extract ALL Perfect Specs (No Dictionary!)
        specs = extract_specs_from_soup(soup)
        make = specs['make']
        model_name = specs['model']
        trim = specs['trim']
        
        # 5. Engineer Year/Age
        year_match = re.search(r'\b(19[0-9]{2}|20[0-2][0-9])\b', title_text)
        if not year_match or not make or not model_name or not mileage:
            jobs[job_id] = {"status": "failed", "error": f"Missing critical data (Make: {make}, Model: {model_name}, Mileage: {mileage})"}
            return
        
        year = int(year_match.group(0))
        age = datetime.datetime.now().year - year
        location = "sanjose" # Default for live inference

        # 6. Run through ML Model (13 Features!)
        input_data = {
            "age": age, "make": make, "model": model_name, "trim": trim,
            "mileage": mileage, "location": location, 
            "condition": specs['condition'], "title_status": specs['title_status'],
            "cylinders": specs['cylinders'], "drive": specs['drive'], "fuel": specs['fuel'],
            "transmission": specs['transmission'], "type": specs['type']
        }
        input_df = pd.DataFrame([input_data])
        
        cat_encoded = ohe.transform(input_df[['make', 'model', 'trim', 'location', 'condition', 'title_status', 'cylinders', 'drive', 'fuel', 'transmission', 'type']])
        cat_df = pd.DataFrame(cat_encoded, columns=ohe.get_feature_names_out(), index=input_df.index)
        num_df = input_df[['age', 'mileage']]
        final_df = pd.concat([num_df, cat_df], axis=1)
        final_df = final_df.reindex(columns=model_columns, fill_value=0)
        
        predicted_price = float(model.predict(final_df)[0])
        difference = predicted_price - listing_price
        pct_diff = (difference / predicted_price) * 100
        
        if pct_diff > 10:
            verdict = "Excellent Deal! (Significantly Underpriced)"
        elif pct_diff > 3:
            verdict = "Great Deal! (Underpriced)"
        elif pct_diff >= -3:
            verdict = "Fair Market Price"
        elif pct_diff >= -10:
            verdict = "Slightly Overpriced"
        else:
            verdict = "Overpriced! (Significantly Above Market)"

        jobs[job_id] = {
            "status": "completed",
            "listing_title": title_text,
            "listing_price": listing_price,
            "predicted_price": predicted_price,
            "difference": difference,
            "verdict": verdict
        }

    except Exception as e:
        jobs[job_id] = {"status": "failed", "error": str(e)}

@app.get("/status/{job_id}")
def get_status(job_id: str):
    if job_id in jobs:
        return jobs[job_id]
    return {"error": "Job not found"}

@app.get("/regions")
def get_region_counts():
    if not db_engine:
        return {}
        
    regions = ['sfbay', 'losangeles', 'newyork', 'seattle', 'chicago', 'dallas', 'miami', 'atlanta', 'boston', 'phoenix']
    counts = {}
    
    with db_engine.connect() as conn:
        total_query = text("""
            SELECT COUNT(*) FROM cars 
            WHERE make IS NOT NULL AND model IS NOT NULL AND trim IS NOT NULL AND trim != 'Error'
            AND location IS NOT NULL AND location != 'null' AND TRIM(location) != '' AND location != 'Unknown'
        """)
        total_result = conn.execute(total_query)
        counts['total'] = total_result.fetchone()[0]
        
        for region in regions:
            query = text("""
                SELECT COUNT(*) FROM cars 
                WHERE region = :region 
                AND make IS NOT NULL AND model IS NOT NULL AND trim IS NOT NULL AND trim != 'Error'
                AND location IS NOT NULL AND location != 'null' AND TRIM(location) != '' AND location != 'Unknown'
            """)
            result = conn.execute(query, {"region": region})
            counts[region] = result.fetchone()[0]
            
    return counts

@app.get("/cities")
def get_cities(region: str):
    if not db_engine:
        return []
        
    with db_engine.connect() as conn:
        query = text("""
            SELECT location, COUNT(*) as count FROM cars
            WHERE region = :region 
            AND make IS NOT NULL AND model IS NOT NULL AND trim IS NOT NULL AND trim != 'Error'
            AND location IS NOT NULL AND location != 'null' AND TRIM(location) != '' AND location != 'Unknown'
            GROUP BY location
            ORDER BY count DESC
        """)
        results = conn.execute(query, {"region": region}).fetchall()
        
    return [{"name": row[0].title(), "count": row[1]} for row in results]

@app.get("/feed")
def get_market_feed(region: str = "all", city: str = "all", sort_by: str = "best", offset: int = 0):
    if not db_engine:
        return {"error": "Database not configured"}
        
    base_query = """
        SELECT * FROM cars 
        WHERE make IS NOT NULL AND model IS NOT NULL AND trim IS NOT NULL AND trim != 'Error'
        AND location IS NOT NULL AND location != 'null' AND TRIM(location) != '' AND location != 'Unknown'
        AND predicted_price IS NOT NULL AND predicted_price > 0
        AND price >= 1000
        AND difference < (predicted_price * 0.35)
    """
    params = {}
    
    if region != "all":
        base_query += " AND region = :region"
        params["region"] = region
        
    if city != "all":
        base_query += " AND location = :city"
        params["city"] = city.title()
        
    if sort_by == "best":
        base_query += " ORDER BY difference DESC"
    elif sort_by == "price_low":
        base_query += " ORDER BY price ASC"
    elif sort_by == "price_high":
        base_query += " ORDER BY price DESC"
    elif sort_by == "mileage_low":
        base_query += " ORDER BY mileage ASC"
    else:
        base_query += " ORDER BY difference DESC"
        
    base_query += " LIMIT 45 OFFSET :offset"
    params["offset"] = offset
    
    df = pd.read_sql(text(base_query), db_engine, params=params)
    
    if len(df) == 0:
        return []

    # Force these columns to be numeric, convert all NaN/Infinity to 0
    df['price'] = pd.to_numeric(df['price'], errors='coerce').fillna(0)
    df['predicted_price'] = pd.to_numeric(df['predicted_price'], errors='coerce').fillna(0)
    df['difference'] = pd.to_numeric(df['difference'], errors='coerce').fillna(0)
    df['mileage'] = pd.to_numeric(df['mileage'], errors='coerce').fillna(0)

    def clean_location(loc):
        return str(loc).title()

    feed_data = []
    for _, row in df.iterrows():
        clean_name = format_car_name(row.get('year'), row.get('make'), row.get('model'), row.get('trim'))
            
        feed_data.append({
            "name": clean_name,
            "mileage": int(row['mileage']),
            "location": clean_location(row.get('location', 'unknown')),
            "list_price": float(row['price']),
            "ai_price": float(row['predicted_price']),
            "difference": float(row['difference']),
            "url": str(row.get('url', '#'))
        })
        
    return feed_data

@app.post("/watchlist")
def get_watchlist_cars(urls: List[str]):
    if not db_engine or not urls:
        return []
        
    # Query the database for only the URLs the user has saved
    query = text("""
        SELECT * FROM cars 
        WHERE url = ANY(:urls)
        AND make IS NOT NULL
    """)
    with db_engine.connect() as conn:
        result = conn.execute(query, {"urls": urls})
        df = pd.DataFrame(result.fetchall(), columns=result.keys())
        
    if df.empty:
        return []

    df['price'] = pd.to_numeric(df['price'], errors='coerce').fillna(0)
    df['predicted_price'] = pd.to_numeric(df['predicted_price'], errors='coerce').fillna(0)
    df['difference'] = pd.to_numeric(df['difference'], errors='coerce').fillna(0)
    df['mileage'] = pd.to_numeric(df['mileage'], errors='coerce').fillna(0)

    feed_data = []
    for _, row in df.iterrows():
        clean_name = format_car_name(row.get('year'), row.get('make'), row.get('model'), row.get('trim'))
        
        feed_data.append({
            "name": clean_name,
            "mileage": int(row['mileage']),
            "location": str(row.get('location', 'unknown')).title(),
            "list_price": float(row['price']),
            "ai_price": float(row['predicted_price']),
            "difference": float(row['difference']),
            "url": str(row.get('url', '#'))
        })
        
    return feed_data
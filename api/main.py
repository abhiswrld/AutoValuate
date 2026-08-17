from fastapi import FastAPI, BackgroundTasks, Request
from pydantic import BaseModel
import pandas as pd
import joblib
import re
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from fastapi.middleware.cors import CORSMiddleware
import datetime
import os
from fastapi import Response, HTTPException
from sqlalchemy import create_engine, text
import uuid
from typing import List
import requests
import time
from dotenv import load_dotenv, find_dotenv

# Find the .env file in the root directory and load it
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path)

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
db_engine = create_engine(DATABASE_URL, pool_size=50, max_overflow=50, pool_timeout=60, pool_pre_ping=True) if DATABASE_URL else None

if db_engine:
    print("Database engine created!")
else:
    print("WARNING: Database engine NOT created! DATABASE_URL is missing!")

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
            "year": year,
            "age": age, "make": make, "model": model_name, "trim": trim,
            "mileage": mileage, "location": location, 
            "condition": specs['condition'], "title_status": specs['title_status'],
            "cylinders": specs['cylinders'], "drive": specs['drive'], "fuel": specs['fuel'],
            "transmission": specs['transmission'], "type": specs['type']
        }
        input_df = pd.DataFrame([input_data])
        
        try:
            avg_prices = pd.read_csv('api/avg_prices.csv')
            input_df['year'] = pd.to_numeric(input_df['year'])
            input_df = pd.merge(input_df, avg_prices, on=['year', 'make', 'model'], how='left')
            input_df['avg_market_price'] = input_df['avg_market_price'].fillna(15000)
        except Exception as e:
            print("Error loading avg_prices in live evaluation:", e)
            input_df['avg_market_price'] = 15000
            
        input_df['estimated_msrp'] = input_df['avg_market_price'] * (1 + 0.10 * input_df['age'])
        
        cat_encoded = ohe.transform(input_df[['make', 'model', 'trim', 'location', 'condition', 'title_status', 'cylinders', 'drive', 'fuel', 'transmission', 'type']])
        cat_df = pd.DataFrame(cat_encoded, columns=ohe.get_feature_names_out(), index=input_df.index)
        num_df = input_df[['age', 'mileage', 'avg_market_price', 'estimated_msrp']]
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
        AND price >= 1500
        AND price NOT IN (1234, 12345, 1111, 2222)
        AND year >= 1996
        AND difference > 0
    """
    params = {}
    
    if region != "all":
        base_query += " AND region = :region"
        params["region"] = region
        
    if city != "all":
        base_query += " AND location = :city"
        params["city"] = city.title()
        
    if sort_by == "latest":
        base_query += " ORDER BY created_at DESC"
    elif sort_by == "best":
        base_query += " ORDER BY difference DESC"
    elif sort_by == "price_low":
        base_query += " ORDER BY price ASC"
    elif sort_by == "price_high":
        base_query += " ORDER BY price DESC"
    elif sort_by == "mileage_low":
        base_query += " ORDER BY mileage ASC"
    else:
        base_query += " ORDER BY created_at DESC"
        
    base_query += " LIMIT 15 OFFSET :offset"
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
            "url": str(row.get('url', '#')),
            "image_url": str(row.get('image_url', '')) if pd.notna(row.get('image_url')) else None
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
            "url": str(row.get('url', '#')),
            "image_url": str(row.get('image_url', '')) if pd.notna(row.get('image_url')) else None
        })
        
    return feed_data

@app.get("/insights/makes")
def get_makes():
    if not db_engine:
        return []
    with db_engine.connect() as conn:
        query = text("SELECT DISTINCT make FROM cars WHERE make IS NOT NULL ORDER BY make")
        result = conn.execute(query).fetchall()
        return [row[0] for row in result]

@app.get("/insights/models")
def get_models(make: str):
    try:
        avg_prices = pd.read_csv('api/avg_prices.csv')
        make_df = avg_prices[avg_prices['make'] == make.lower()]
        unique_models = make_df['model'].dropna().unique().tolist()
        
        models = []
        for m in sorted(unique_models):
            m_str = str(m).strip()
            if m_str.lower() in ['unspecified', 'other', 'model', 'unknown', 'base']:
                continue
            if make.lower() == 'tesla' and m_str in ['3', 's', 'x', 'y']:
                m_str = f"{m_str}"
            models.append(m_str)
        return models
    except Exception as e:
        print(f"Error reading models: {e}")
        return []

@app.get("/insights/depreciation")
def get_depreciation_curve(make: str, model_name: str):
    import datetime
    current_year = datetime.datetime.now().year
    
    # Dynamically find the minimum year for this specific make/model to bound the chart
    start_year = 2005
    if db_engine:
        with db_engine.connect() as conn:
            query = text("SELECT MIN(year) FROM cars WHERE make ILIKE :make AND model ILIKE :model_name")
            min_year = conn.execute(query, {"make": make, "model_name": model_name}).scalar()
            if min_year:
                start_year = max(int(min_year), 1990)
    
    years = list(range(start_year, current_year + 1))
    
    # Create a synthetic dataframe
    synthetic_data = []
    for year in years:
        age = current_year - year
        mileage = age * 12000 # 12k miles per year average
        synthetic_data.append({
            'year': year,
            'age': age,
            'make': make.lower(),
            'model': model_name.lower(),
            'trim': 'unspecified',
            'mileage': mileage,
            'location': 'unspecified',
            'condition': 'good',
            'title_status': 'clean',
            'cylinders': 'unspecified',
            'drive': 'unspecified',
            'fuel': 'gas',
            'transmission': 'automatic',
            'type': 'unspecified',
        })
        
    df_synth = pd.DataFrame(synthetic_data)
    
    # We need to fill the baseline market data (MSRP and AVG Price) correctly
    try:
        avg_prices = pd.read_csv('api/avg_prices.csv')
        df_synth = pd.merge(df_synth, avg_prices, on=['year', 'make', 'model'], how='left')
        df_synth['avg_market_price'] = df_synth['avg_market_price'].fillna(15000)
    except Exception as e:
        print("Error loading avg_prices in get_depreciation_curve:", e)
        df_synth['avg_market_price'] = 15000
        
    # Calculate MSRP exactly like the training pipeline
    df_synth['estimated_msrp'] = df_synth['avg_market_price'] * (1 + 0.10 * df_synth['age'])
        
    # Predict!
    try:
        X_encoded = ohe.transform(df_synth[['make', 'model', 'trim', 'location', 'condition', 'title_status', 'cylinders', 'drive', 'fuel', 'transmission', 'type']])
        X_encoded_df = pd.DataFrame(X_encoded, columns=ohe.get_feature_names_out(), index=df_synth.index)
        
        X_num = df_synth[['age', 'mileage', 'avg_market_price', 'estimated_msrp']]
        
        X_final = pd.concat([X_num, X_encoded_df], axis=1)
        X_final = X_final.reindex(columns=model_columns, fill_value=0)
        
        predictions = model.predict(X_final)
        
        curve = []
        for i, year in enumerate(years):
            curve.append({
                "year": year,
                "price": float(predictions[i])
            })
            
        return curve
    except Exception as e:
        return {"error": str(e)}

def format_region(r: str) -> str:
    r = r.lower()
    mapping = {
        'sfbay': 'SF Bay',
        'losangeles': 'Los Angeles',
        'newyork': 'New York',
        'sandiego': 'San Diego',
        'lasvegas': 'Las Vegas',
        'orangecounty': 'Orange County',
        'southflorida': 'South Florida',
        'dallas': 'Dallas',
        'chicago': 'Chicago',
        'seattle': 'Seattle',
        'atlanta': 'Atlanta',
        'miami': 'Miami'
    }
    return mapping.get(r, r.title())

@app.get("/insights/live_data")
def get_live_data(make: str, model_name: str):
    if not db_engine:
        return []
    with db_engine.connect() as conn:
        query = text("""
            SELECT year, price, mileage, url, location, region 
            FROM cars 
            WHERE make ILIKE :make AND model ILIKE :model 
            AND price >= 1000 AND price <= 100000 
            AND year >= 2000
        """)
        result = conn.execute(query, {"make": f"%{make}%", "model": f"%{model_name}%"}).fetchall()
        
        data = []
        for row in result:
            region_str = str(row[5]) if row[5] and row[5] != 'null' else ''
            location_str = str(row[4]).title()
            if region_str and region_str.upper() != 'UNSPECIFIED':
                location_str = f"{location_str}, {format_region(region_str)}"
                
            data.append({
                "year": row[0],
                "price": float(row[1]),
                "mileage": float(row[2]) if row[2] else 0,
                "url": row[3],
                "location": location_str
            })
        return data

class ReportSoldRequest(BaseModel):
    url: str
    user_id: str

RATE_LIMIT_MAX = 20

@app.post("/api/report-sold")
def report_sold(payload: ReportSoldRequest):
    user_id = payload.user_id
    url = payload.url
    
    if not db_engine:
        return {"status": "error", "message": "Database disconnected"}

    with db_engine.begin() as conn:
        # Check rate limit
        result = conn.execute(text("SELECT report_count, reset_time FROM user_report_limits WHERE user_id = :uid"), {"uid": user_id}).fetchone()
        
        now = datetime.datetime.utcnow()
        if result:
            count, reset_time = result
            if now > reset_time:
                # Expired, reset it
                new_reset = now + datetime.timedelta(hours=6)
                conn.execute(text("UPDATE user_report_limits SET report_count = 1, reset_time = :rt WHERE user_id = :uid"), {"uid": user_id, "rt": new_reset})
            elif count >= RATE_LIMIT_MAX:
                raise HTTPException(status_code=429, detail="Cooldown active for 6 hours. Please try again later.")
            else:
                conn.execute(text("UPDATE user_report_limits SET report_count = report_count + 1 WHERE user_id = :uid"), {"uid": user_id})
        else:
            new_reset = now + datetime.timedelta(hours=6)
            conn.execute(text("INSERT INTO user_report_limits (user_id, report_count, reset_time) VALUES (:uid, 1, :rt)"), {"uid": user_id, "rt": new_reset})
    
    # Real-time Verification
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code in [404, 410]:
            # It's dead! Delete from DB
            if db_engine:
                with db_engine.begin() as conn:
                    conn.execute(text("DELETE FROM cars WHERE url = :url"), {"url": url})
            return {"status": "deleted", "message": "Successfully verified and deleted."}
        else:
            # Still alive or we got 403
            return {"status": "alive", "message": "Listing still appears to be active."}
    except Exception as e:
        return {"status": "error", "message": str(e)}
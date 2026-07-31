from fastapi import FastAPI
from pydantic import BaseModel
import pandas as pd
import joblib
import re
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from fastapi.middleware.cors import CORSMiddleware
import datetime
import os

# 1. Initialize the App
app = FastAPI(title="AutoValuate API")

@app.get("/")
def read_root():
    return {"status": "AutoValuate API is running!"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allows React app to connect to backend
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

# 3. Define Input Schemas
class CarData(BaseModel):
    age: int
    make: str
    model: str
    mileage: float
    location: str

class URLData(BaseModel):
    url: str

# HELPER FUNCTIONS - copied from previous work done in Jupyter notebook.
manufacturers = [
    'Toyota', 'Honda', 'Ford', 'Chevrolet', 'Chevy', 'Nissan', 'BMW', 'Mercedes', 'Benz', 
    'Audi', 'Lexus', 'Subaru', 'Volkswagen', 'Vw', 'Hyundai', 'Kia', 'Mazda', 'Acura', 'Jeep', 
    'Dodge', 'Ram', 'GMC', 'Cadillac', 'Infiniti', 'Volvo', 'Mitsubishi', 'Mini',
    'Porsche', 'Tesla', 'Land Rover', 'Jaguar', 'Chrysler', 'Buick', 'Pontiac', 'Saturn',
    'Lucid', 'Rivian', 'Polestar', 'Fisker'
]

car_models_dict = {
    'Toyota': ['Camry', 'Corolla', 'Prius', 'Sienna', 'Tacoma', 'Tundra', 'Rav4', 'Highlander', '4Runner', 'Avalon', 'Yaris', 'Sequoia', 'Matrix', 'Fj Cruiser', 'Venza'],
    'Honda': ['Civic', 'Accord', 'Cr-v', 'Crv', 'Odyssey', 'Pilot', 'Fit', 'Hr-v', 'Hrv', 'Element', 'Ridgeline', 'Insight', 'Passport', 'S2000'],
    'Ford': ['F150', 'F-150', 'F250', 'F-250', 'F350', 'F-350', 'Escape', 'Explorer', 'Focus', 'Fusion', 'Mustang', 'Edge', 'Transit', 'Ranger', 'Expedition', 'Taurus', 'Bronco', 'Flex'],
    'Chevrolet': ['Silverado', 'Equinox', 'Malibu', 'Cruze', 'Tahoe', 'Impala', 'Colorado', 'Camaro', 'Corvette', 'Suburban', 'Traverse', 'Spark', 'Sonic', 'Volt', 'Bolt'],
    'Nissan': ['Altima', 'Sentra', 'Rogue', 'Maxima', 'Murano', 'Pathfinder', 'Versa', 'Frontier', 'Titan', 'Armada', 'Leaf', '350Z', '370Z', 'Juke', 'Kicks'],
    'Bmw': ['328I', '335I', '325I', 'X5', 'X3', 'M3', 'M4', 'M5', '528I', '535I', '750Li', 'X1'],
    'Mercedes': ['C300', 'E350', 'E320', 'E300', 'Ml350', 'Glk350', 'S550', 'S500', 'Gle', 'Glc', 'Gla', 'Sprinter', 'C63', 'Amg', 'C230', 'C240', 'C250'],
    'Subaru': ['Outback', 'Forester', 'Impreza', 'Legacy', 'Crosstrek', 'Wrx', 'Brz', 'Ascent'],
    'Volkswagen': ['Jetta', 'Passat', 'Golf', 'Gti', 'Tiguan', 'Touareg', 'Atlas', 'Beetle'],
    'Vw': ['Jetta', 'Passat', 'Golf', 'Gti', 'Tiguan', 'Touareg', 'Atlas', 'Beetle'],
    'Lexus': ['Rx', 'Es', 'Is', 'Nx', 'Gx', 'Lx', 'Gs', 'Ls'],
    'Audi': ['A4', 'A6', 'Q5', 'Q7', 'A3', 'S4', 'Tt', 'Q3', 'S5'],
    'Jeep': ['Grand Cherokee', 'Wrangler', 'Cherokee', 'Compass', 'Renegade', 'Patriot', 'Gladiator'],
    'Hyundai': ['Elantra', 'Sonata', 'Tucson', 'Santa Fe', 'Accent', 'Kona', 'Palisade', 'Veloster'],
    'Kia': ['Optima', 'Sorento', 'Soul', 'Forte', 'Sportage', 'Telluride', 'Sedona', 'Rio'],
    'Mazda': ['Mazda3', 'Mazda6', 'Cx-5', 'Cx5', 'Cx-9', 'Cx9', 'Miata', 'Mx-5'],
    'Dodge': ['Charger', 'Challenger', 'Grand Caravan', 'Durango', 'Journey', 'Dart'],
    'Ram': ['1500', '2500', '3500', 'Promaster'],
    'Gmc': ['Sierra', 'Acadia', 'Terrain', 'Yukon', 'Canyon', 'Savana'],
    'Tesla': ['Model 3', 'Model Y', 'Model S', 'Model X', 'Cybertruck'],
    'Mini': ['Cooper', 'Countryman', 'Clubman', 'Hardtop', 'Paceman', 'Cooper S'],
    'Acura': ['Mdx', 'Rdx', 'Tlx', 'Ilx', 'Integra', 'Tsx', 'Tl', 'Rsx', 'Rl', 'Rlx'],
    'Lucid': ['Air'],
    'Rivian': ['R1T', 'R1S'],
    'Polestar': ['Polestar 2', 'Polestar 3'], 
    'Fisker': ['Ocean', 'Karma'],
    'Cadillac': ['Escalade', 'Cts', 'Ats', 'Xt5', 'Xt4', 'Srx', 'Xts', 'Deville', 'Seville'],
    'Infiniti': ['G37', 'G35', 'Q50', 'Qx60', 'Qx80', 'Q60', 'Fx35', 'M35'],
    'Volvo': ['Xc90', 'Xc60', 'Xc40', 'S60', 'S90', 'V60', 'V90'],
    'Mitsubishi': ['Outlander', 'Lancer', 'Eclipse', 'Mirage', 'Galant'],
    'Porsche': ['911', 'Cayenne', 'Macan', 'Panamera', 'Boxster', 'Cayman', 'Taycan'],
    'Land Rover': ['Range Rover', 'Discovery', 'Defender', 'Evoque', 'Lr4', 'Lr3'],
    'Jaguar': ['Xf', 'Xj', 'F-Type', 'F-Pace', 'E-Pace', 'I-Pace', 'Xe'],
    'Chrysler': ['300', 'Pacifica', 'Town & Country', 'Sebring', 'Pt Cruiser'],
    'Buick': ['Enclave', 'Encore', 'Envision', 'Lacrosse', 'Regal', 'Lucerne'],
    'Pontiac': ['Grand Prix', 'G6', 'Grand Am', 'Vibe', 'Firebird', 'G8', 'Bonneville'],
    'Saturn': ['Vue', 'Ion', 'Aura', 'Sky', 'Outlook']
}

def extract_make(title):
    title_lower = title.lower()
    for make in manufacturers:
        if make.lower() in title_lower:
            if make.lower() == 'chevy': return 'Chevrolet'
            if make.lower() == 'vw': return 'Volkswagen'
            if make.lower() == 'benz': return 'Mercedes'
            return make.title()
    return None

def extract_model(title, make):
    if not make: return None
    title_lower = title.lower()
    if make in car_models_dict:
        for model in car_models_dict[make]:
            if model.lower() in title_lower:
                return model.replace('-', '').title()
    return None

# --- ENDPOINTS ---

@app.post("/predict")
def predict_price(car: CarData):
    input_df = pd.DataFrame([car.model_dump()])
    cat_encoded = ohe.transform(input_df[['make', 'model', 'location']])
    cat_df = pd.DataFrame(cat_encoded, columns=ohe.get_feature_names_out(), index=input_df.index)
    num_df = input_df[['age', 'mileage']]
    final_df = pd.concat([num_df, cat_df], axis=1)
    final_df = final_df.reindex(columns=model_columns, fill_value=0)
    
    predicted_price = model.predict(final_df)[0]
    return {"predicted_price": float(predicted_price), "currency": "USD"}

@app.post("/evaluate_url")
def evaluate_url(url_data: URLData):
    url = url_data.url
    
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
            return {"error": f"Failed to scrape URL: {str(e)}"}

    # 2. Extract Title and Price
    title_tag = soup.find("h1", class_="postingtitle")
    if not title_tag:
        return {"error": "Could not find posting title. Is this a valid Craigslist URL?"}
    
    # The title usually looks like: "$10,500 2016 Toyota Corolla Sport"
    # We will use Regex to find the price, and then remove it to get the clean title.
    full_title_text = title_tag.text.strip()
    
    price_match = re.search(r'\$([\d,]+)', full_title_text)
    if not price_match:
        return {"error": "Could not find a valid price in the title."}
    
    # Clean the price string (e.g., "10,500" -> 10500)
    price_str = price_match.group(1).replace(',', '')
    try:
        listing_price = int(price_str)
    except ValueError:
        return {"error": "Invalid price format."}

    # Remove the price from the title string so our NLP doesn't get confused
    title_text = re.sub(r'\$[\d,]+', '', full_title_text).strip().title()

    # 3. Extract Mileage
    mileage = None
    
    # Target the exact div holding the miles
    miles_div = soup.find("div", class_="attr auto_miles")
    
    if miles_div:
        # Extract just the value span
        value_span = miles_div.find("span", class_="valu")
        if value_span:
            # Get the text, strip the comma, and convert
            mileage_str = value_span.text.replace(',', '').strip()
            try:
                mileage = float(mileage_str)
            except Exception as e:
                print(f"Mileage parsing error: {e}")

    # 4. Engineer Features (Make, Model, Year, Age)
    make = extract_make(title_text)
    model_name = extract_model(title_text, make)
    
    year_match = re.search(r'\b(19[0-9]{2}|20[0-2][0-9])\b', title_text)
    if not year_match:
        return {"error": "Could not extract year from title."}
    
    year = int(year_match.group(0))
    import datetime
    age = datetime.datetime.now().year - year

    # Default location if we can't find it
    location = "sanjose" 

    if not make or not model_name or not mileage:
        return {"error": f"Missing data -> Make: {make}, Model: {model_name}, Mileage: {mileage}"}

    # 5. Run through ML Model
    input_data = {
        "age": age,
        "make": make,
        "model": model_name,
        "mileage": mileage,
        "location": location
    }
    input_df = pd.DataFrame([input_data])
    cat_encoded = ohe.transform(input_df[['make', 'model', 'location']])
    cat_df = pd.DataFrame(cat_encoded, columns=ohe.get_feature_names_out(), index=input_df.index)
    num_df = input_df[['age', 'mileage']]
    final_df = pd.concat([num_df, cat_df], axis=1)
    final_df = final_df.reindex(columns=model_columns, fill_value=0)
    
    predicted_price = float(model.predict(final_df)[0])
    
    # 6. Calculate the Deal
    difference = predicted_price - listing_price
    
    # Calculate percentage difference (Listing Price vs Predicted Price)
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

    return {
        "listing_title": title_text,
        "listing_price": listing_price,
        "predicted_price": predicted_price,
        "difference": difference,
        "verdict": verdict
    }

@app.get("/feed")
def get_market_feed():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    csv_path = os.path.join(base_dir, 'data', 'clean_listings.csv')
    
    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        print(f"Error loading CSV: {e}")
        return []
        
    current_year = datetime.datetime.now().year
    df['age'] = current_year - df['year']
    df = df.dropna(subset=['age', 'make', 'model', 'mileage', 'location', 'price', 'url'])
    
    # Predict prices
    input_df = df[['age', 'make', 'model', 'mileage', 'location']]
    cat_encoded = ohe.transform(input_df[['make', 'model', 'location']])
    cat_df = pd.DataFrame(cat_encoded, columns=ohe.get_feature_names_out(), index=input_df.index)
    num_df = input_df[['age', 'mileage']]
    final_df = pd.concat([num_df, cat_df], axis=1)
    final_df = final_df.reindex(columns=model_columns, fill_value=0)
    
    df['predicted_price'] = model.predict(final_df)
    df['difference'] = df['predicted_price'] - df['price']
    
    # Randomly sample 6 cars
    sample_df = df.sample(n=6, replace=False)

    def clean_location(loc):
        loc = str(loc).lower().strip()

        # Bay Area location slugs, mapped back to their proper display names.
        replacements = {
            'southsanfrancisco': 'South San Francisco',
            'sanjosedowntown': 'San Jose Downtown',
            'sanjose': 'San Jose',
            'sanfrancisco': 'San Francisco',
            'santaclara': 'Santa Clara',
            'sanleandro': 'San Leandro',
            'sanbruno': 'San Bruno',
            'sanmateo': 'San Mateo',
            'santarosa': 'Santa Rosa',
            'sancarlos': 'San Carlos',
            'walnutcreek': 'Walnut Creek',
            'castrovalley': 'Castro Valley',
            'dalycity': 'Daly City',
            'mountainview': 'Mountain View',
            'redwoodcity': 'Redwood City',
            'unioncity': 'Union City',
            'losgatos': 'Los Gatos',
            'pleasanthill': 'Pleasant Hill',
            'elcerrito': 'El Cerrito',
            'halfmoonbay': 'Half Moon Bay',
            'napacounty': 'Napa County',
            'hayesvalley': 'Hayes Valley',
            'eastbayarea': 'East Bay Area',
            'willowglen': 'Willow Glen',
            'losaltos': 'Los Altos',
            'oaklandeast': 'Oakland East',
            'sananselmo': 'San Anselmo',
            'bernalheights': 'Bernal Heights',
            'redwoodshores': 'Red Wood Shores',
            'santacruz': 'Santa Cruz',
            'sanrafael': 'San Rafael',
            'morganhill': 'Morgan Hill',
            'berkeleynorth': 'Berkeley North',
            'scottottsvalley': 'Scotts Valley',
            'scottsvalley': 'Scotts Valley'
        }

        # Check the longest slugs first, so "sanjosedowntown" matches before the shorter "sanjose" substring inside it.
        for wrong in sorted(replacements, key=len, reverse=True):
            if wrong in loc:
                return replacements[wrong]

        return loc.title()

    feed_data = []
    for _, row in sample_df.iterrows():
        clean_name = f"{int(row['year'])} {row['make']} {row['model']}"
        feed_data.append({
            "name": clean_name,
            "location": clean_location(row['location']), # Use the cleaner here
            "list_price": float(row['price']),
            "ai_price": float(row['predicted_price']),
            "difference": float(row['difference']),
            "url": str(row['url'])
        })
        
    return feed_data
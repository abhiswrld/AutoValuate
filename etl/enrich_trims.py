import os
import time
import json
import pandas as pd
from groq import Groq
from pydantic import BaseModel
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Initialize Groq Client
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

class CarSpecs(BaseModel):
    make: str
    model: str
    trim: str

def extract_car_specs(title):
    prompt = f"""
    Extract the vehicle Make, Model, and Trim from this Craigslist title. 
    - If a trim is not explicitly stated, return 'Base'.
    - Return ONLY valid JSON matching this schema: {{"make": "", "model": "", "trim": ""}}.
    Title: "{title}"
    """
    
    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        data = json.loads(response.choices[0].message.content)
        return CarSpecs(**data)
    except Exception as e:
        print(f"Groq API Error: {e}")
        return None

def enrich_trims():
    print("Starting LLM Trim Enrichment...")
    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        print("Error: DATABASE_URL not set.")
        return
        
    engine = create_engine(DATABASE_URL)
    
    # Ensure the 'trim' column exists
    with engine.connect() as conn:
        conn.execute(text("ALTER TABLE cars ADD COLUMN IF NOT EXISTS trim TEXT;"))
        conn.commit()
        
    # Grab 500 cars that haven't been enriched with a trim yet
    with engine.connect() as conn:
        query = text("SELECT url, name FROM cars WHERE trim IS NULL LIMIT 500")
        result = conn.execute(query)
        cars_to_update = result.fetchall()
        
    total_cars = len(cars_to_update)
    print(f"Found {total_cars} cars to enrich. Estimated time: {total_cars * 0.5 / 60} minutes.")
    
    updated_count = 0
    for i, car in enumerate(cars_to_update):
        url = car[0]
        title = car[1]
        
        print(f"[{i+1}/{total_cars}] LLM analyzing: {title}")
        specs = extract_car_specs(title)
        
        if specs:
            # Update the database with the clean LLM extracted data
            with engine.begin() as conn:
                update_query = text("""
                    UPDATE cars 
                    SET make = :make, model = :model, trim = :trim 
                    WHERE url = :url
                """)
                conn.execute(update_query, {
                    "make": specs.make.title(), 
                    "model": specs.model.title(), 
                    "trim": specs.trim.title(), 
                    "url": url
                })
                updated_count += 1
        else:
            # If Groq fails, mark it as 'Error' so we don't get stuck in a loop
            with engine.begin() as conn:
                conn.execute(text("UPDATE cars SET trim = 'Error' WHERE url = :url"), {"url": url})
                
        time.sleep(0.2)

    print(f"\nEnrichment Complete! Updated {updated_count} cars with clean Make/Model/Trim.")

if __name__ == "__main__":
    enrich_trims()
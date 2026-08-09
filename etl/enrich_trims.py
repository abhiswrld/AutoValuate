import os
import time
import json
import pandas as pd
from typing import Literal
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
    trim: Literal["Base", "Sport", "Luxury", "Touring", "Off-Road", "Performance", "Other"]

def extract_car_specs(title):
    prompt = f"""
    Analyze this Craigslist car title and extract the Make, Model, and Trim tier.

    Trim Tier Rules:
    - Base: Standard trims (e.g., LX, SE, S) or no trim stated at all.
    - Sport: Sporty trims (e.g., GT, Sport, TRD Sport, RS)
    - Luxury: Premium/leather trims (e.g., EX-L, Limited, Platinum, Premium)
    - Touring: Tech/highway trims (e.g., Touring, Grand Touring)
    - Off-Road: Trail trims (e.g., TRD Off-Road, Rubicon, Z71)
    - Performance: High-horsepower trims (e.g., M, AMG, Hellcat, Type R)
    - Other: A trim is clearly stated but doesn't fit any tier above (rare -- use sparingly).

    If no trim is stated, use "Base", not "Other".

    Return ONLY valid JSON matching this schema:
    {{"make": "string", "model": "string", "trim": "one of the exact tier names above"}}

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
            with engine.begin() as conn:
                update_query = text("""
                    UPDATE cars 
                    SET trim = :trim 
                    WHERE url = :url
                """)
                conn.execute(update_query, {
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
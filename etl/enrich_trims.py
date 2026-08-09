import os
import time
import json
import pandas as pd
from groq import Groq
from pydantic import BaseModel
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
from typing import Literal

load_dotenv()
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

class CarSpecs(BaseModel):
    make: str
    model: str
    trim: Literal["Base", "Sport", "Luxury", "Touring", "Off-Road", "Performance", "Other"]

def extract_car_specs(title):
    prompt = f"""
    Analyze this Craigslist car title and extract the Make, Model, and Trim category.
    
    Standardization Rules:
    - Make: Always use the official full name (e.g., "Chevrolet" not "Chevy", "Volkswagen" not "VW", "Mercedes-Benz" not "Benz").
    - Model: The base model name without trim designations (e.g., "Civic", not "Civic EX-L").
    
    Trim Categorization Rules:
    - Base: Standard trims (e.g., LX, SE, S, Base)
    - Sport: Sporty trims (e.g., GT, Sport, TRD Sport, RS)
    - Luxury: Premium/Leather trims (e.g., EX-L, Limited, Platinum, Premium)
    - Touring: Tech/Highway trims (e.g., Touring, Grand Touring)
    - Off-Road: Trail trims (e.g., TRD Off-Road, Rubicon, Z71)
    - Performance: High horsepower (e.g., M, AMG, Hellcat, Type R)
    - Other: If it clearly does not fit or isn't stated, default to 'Other'.
    
    Return ONLY valid JSON matching this schema: 
    {{"make": "string", "model": "string", "trim": "Must be one of the exact categories above"}}
    
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
    
    with engine.connect() as conn:
        conn.execute(text("ALTER TABLE cars ADD COLUMN IF NOT EXISTS trim TEXT;"))
        conn.commit()
        
    with engine.connect() as conn:
        # Grab cars where the LLM hasn't run yet (make is NULL or trim is NULL)
        query = text("SELECT url, name FROM cars WHERE trim IS NULL OR make IS NULL LIMIT 500")
        result = conn.execute(query)
        cars_to_update = result.fetchall()
        
    total_cars = len(cars_to_update)
    print(f"Found {total_cars} cars to enrich.")
    
    updated_count = 0
    for i, car in enumerate(cars_to_update):
        url = car[0]
        title = car[1]
        
        print(f"[{i+1}/{total_cars}] LLM analyzing: {title}")
        specs = extract_car_specs(title)
        
        if specs:
            with engine.begin() as conn:
                # UPDATE MAKE, MODEL, AND TRIM!
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
            with engine.begin() as conn:
                conn.execute(text("UPDATE cars SET trim = 'Error' WHERE url = :url"), {"url": url})
                
        time.sleep(0.2)

    print(f"\nEnrichment Complete! Updated {updated_count} cars.")

if __name__ == "__main__":
    enrich_trims()
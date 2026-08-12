import os
import json
import time
import pandas as pd
from groq import Groq
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
engine = create_engine(os.getenv("DATABASE_URL"))

def clean_locations():
    print("Fetching distinct locations from database...")
    with engine.connect() as conn:
        result = conn.execute(text("SELECT DISTINCT location FROM cars WHERE location IS NOT NULL"))
        locations = [row[0] for row in result.fetchall()]
        
    print(f"Found {len(locations)} unique locations. Asking LLM to clean them in batches...")
    
    chunk_size = 150
    all_mappings = {}
    
    for i in range(0, len(locations), chunk_size):
        chunk = [loc.replace('"', '').replace("'", "") for loc in locations[i:i+chunk_size]]
        print(f"Processing batch {i//chunk_size + 1}/{(len(locations) + chunk_size - 1)//chunk_size}...")
        
        prompt = f"""
        You are a database cleaning expert. I have a list of messy Craigslist location strings.
        Clean and standardize them into simple, lowercase city or region names.
        
        Rules:
        - Convert everything to lowercase.
        - Combine neighborhoods into their main city (e.g., "san jose downtown" -> "san jose").
        - Convert Craigslist codes to real names (e.g., "eby" -> "east bay", "sby" -> "south bay", "pen" -> "peninsula", "sfc" -> "san francisco").
        - Remove state abbreviations (e.g., "oakland ca" -> "oakland").
        - If it's already a clean city, just make it lowercase.
        - Fix spacing issues as well (oaklandeast -> oakland east), and if an entry doesn't seem like a city, convert its value to the exact string "null".
        
        Return ONLY a valid JSON object mapping the original string to the cleaned string.
        Ensure there are no trailing periods or commas inside the JSON keys or values.
        Example: {{"san jose downtown": "san jose", "eby": "east bay"}}
        
        Here is the list: {json.dumps(chunk)}
        """
        
        try:
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            mapping = json.loads(response.choices[0].message.content)
            all_mappings.update(mapping)
        except Exception as e:
            print(f"Error on batch {i//chunk_size + 1}: {e}")
            
        time.sleep(5)
        
    print(f"LLM returned {len(all_mappings)} total mappings. Updating database...")
    
    updated_count = 0
    with engine.begin() as conn:
        for original, cleaned in all_mappings.items():
            # FIX: Handle cases where LLM returned JSON null (Python None)
            if cleaned is None or not isinstance(cleaned, str):
                cleaned = "null"
                
            if original != cleaned:
                conn.execute(text("UPDATE cars SET location = :clean WHERE location = :original"), {
                    "clean": cleaned.lower(), 
                    "original": original
                })
                updated_count += 1
                
    print(f"Locations cleaned successfully! Updated {updated_count} rows.")

if __name__ == "__main__":
    clean_locations()
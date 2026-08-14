import pandas as pd
import numpy as np
import joblib
import re
import os
import datetime
from sqlalchemy import create_engine

def clean_and_upload():
    print("Starting ETL Pipeline...")
    
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    raw_path = os.path.join(project_root, 'data', 'raw_listings.csv')
    
    if not os.path.exists(raw_path):
        print("No raw_listings.csv found. Exiting.")
        return
        
    df = pd.read_csv(raw_path)
    
    # 1. Basic Cleaning
    df['location'] = df['location'].astype(str).str.split('/').str[0].str.lower().str.strip()
    df = df.dropna(subset=['price', 'mileage'])
    df = df[(df['price'] >= 800) & (df['price'] <= 100000)]
    df = df[(df['mileage'] >= 100) & (df['mileage'] <= 300000)]
    
    # 2. Extract Year/Age (We still parse this from the title for the ML model)
    df['year'] = df['name'].astype(str).str.extract(r'(\b(19[0-9]{2}|20[0-2][0-9])\b)')[0]
    df = df.dropna(subset=['year'])
    df['year'] = df['year'].astype(int)
    current_year = datetime.datetime.now().year
    df['age'] = current_year - df['year']
    
    # 3. Prepare for upload (Drop rows missing core requirements)
    df = df.dropna(subset=['age', 'mileage', 'location', 'price', 'url'])
    cars_to_upload = df.copy()
        
    # 4. Upload to Supabase
    print("Uploading raw listings to Supabase for deep-scraper processing...")
    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        print("Error: DATABASE_URL environment variable not set.")
        return
        
    engine = create_engine(DATABASE_URL)
    
    print("Checking for existing cars to avoid duplicates...")
    try:
        existing_urls = pd.read_sql("SELECT url FROM cars", engine)['url'].tolist()
    except Exception:
        existing_urls = []
        
    new_cars_df = cars_to_upload[~cars_to_upload['url'].isin(existing_urls)]
    
    # Make, Model, Trim, Cylinders, etc. are left out so they default to NULL in Postgres.
    columns_to_upload = ['name', 'url', 'price', 'mileage', 'location', 'region', 'year', 'age', 'image_url']
    cols_present = [col for col in columns_to_upload if col in new_cars_df.columns]
    new_cars_df = new_cars_df[cols_present]
    
    if not new_cars_df.empty:
        new_cars_df.to_sql('cars', engine, if_exists='append', index=False)
        print(f"Added {len(new_cars_df)} new raw cars to Supabase. Waiting for deep-scraper enrichment...")
    else:
        print("No new cars to add today.")
        
    print(f"ETL Complete! Total cars processed: {len(df)}")

if __name__ == "__main__":
    clean_and_upload()
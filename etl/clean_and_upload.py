import pandas as pd
import numpy as np
import joblib
import re
import os
import datetime
from sqlalchemy import create_engine
from vocab import extract_make, extract_model

def clean_and_upload():
    print("Starting ETL Pipeline...")
    
    # Dynamically find the project root folder
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # 1. Load Data and Models using the absolute path
    raw_path = os.path.join(project_root, 'data', 'raw_listings.csv')
    model_path = os.path.join(project_root, 'api', 'model.pkl')
    ohe_path = os.path.join(project_root, 'api', 'ohe.pkl')
    cols_path = os.path.join(project_root, 'api', 'model_columns.pkl')
    
    df = pd.read_csv(raw_path)
    model = joblib.load(model_path)
    ohe = joblib.load(ohe_path)
    model_columns = joblib.load(cols_path)
    
    # 2. Basic Cleaning
    df['location'] = df['location'].astype(str).str.split('/').str[0].str.lower().str.strip()
    df = df.dropna(subset=['price', 'mileage'])
    df = df[(df['price'] >= 800) & (df['price'] <= 100000)]
    df = df[(df['mileage'] >= 100) & (df['mileage'] <= 300000)]
    
    # 3. Extract Make
    df['make'] = df['name'].apply(extract_make)
    df = df.dropna(subset=['make'])

    # 4. Extract Year
    df['year'] = df['name'].astype(str).str.extract(r'(\b(19[0-9]{2}|20[0-2][0-9])\b)')[0]
    df = df.dropna(subset=['year'])
    df['year'] = df['year'].astype(int)

    # 5. Extract Model
    df['model'] = df.apply(lambda row: extract_model(row['name'], row['make']), axis=1)
    
    # 6. Feature Engineering
    current_year = datetime.datetime.now().year
    df['age'] = current_year - df['year']
    df = df.dropna(subset=['age', 'make', 'model', 'mileage', 'location', 'price', 'url'])
    
    # 7. Upload Raw Listings to Supabase
    # The raw CSV doesn't have 'make' or 'trim' yet. We upload them as NULLs.
    print("Uploading raw listings to Supabase for deep-scraper processing...")
    cars_to_upload = df.copy()
        
    # 8. Upload to Supabase
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
    
    # EXPLICITLY DEFINE COLUMNS TO UPLOAD (Including 'region'!)
    # Make, Model, and Trim are left out so they default to NULL in Postgres.
    columns_to_upload = ['name', 'url', 'price', 'mileage', 'location', 'region', 'year', 'age']
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
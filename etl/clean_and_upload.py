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
    
    # 7. ML Inference
    print("Running ML predictions...")
    df['condition'] = 'unspecified'
    df['title_status'] = 'unspecified'
    
    input_df = df[['age', 'make', 'model', 'trim', 'mileage', 'location', 'condition', 'title_status']]
    cat_encoded = ohe.transform(input_df[['make', 'model', 'trim', 'location', 'condition', 'title_status']])
    cat_df = pd.DataFrame(cat_encoded, columns=ohe.get_feature_names_out(), index=input_df.index)
    num_df = input_df[['age', 'mileage']]
    final_df = pd.concat([num_df, cat_df], axis=1)
    final_df = final_df.reindex(columns=model_columns, fill_value=0)
    
    df['predicted_price'] = model.predict(final_df)
    df['difference'] = df['predicted_price'] - df['price']
    
    # 8. Upload to Supabase
    print("Uploading to Supabase...")
    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        print("Error: DATABASE_URL environment variable not set.")
        return
        
    engine = create_engine(DATABASE_URL)
    
    # 1. Get all the URLs currently in the database
    print("Checking for existing cars to avoid overwriting enriched data...")
    try:
        existing_urls = pd.read_sql("SELECT url FROM cars", engine)['url'].tolist()
    except Exception as e:
        print(f"Error occurred while fetching existing URLs: {e}")
        existing_urls = []
        
    # 2. Filter our DataFrame to only include cars we don't already have
    new_cars_df = df[~df['url'].isin(existing_urls)]
    
    # 3. Append ONLY the new cars
    if not new_cars_df.empty:
        new_cars_df.to_sql('cars', engine, if_exists='append', index=False)
        print(f"Added {len(new_cars_df)} new cars to Supabase.")
    else:
        print("No new cars to add today.")
        
    print(f"ETL Complete! Total cars in DB: {len(df)}")

if __name__ == "__main__":
    clean_and_upload()
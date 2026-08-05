import pandas as pd
import joblib
from sqlalchemy import create_engine
import datetime

DATABASE_URL = "postgresql://postgres:Abhinavk11#@db.ezcvriynjmielevtvzaf.supabase.co:5432/postgres"

def migrate_data():
    print("Loading data and ML models...")
    # Load the cleaned data
    df = pd.read_csv('data/clean_listings.csv')
    
    # Load ML models
    model = joblib.load('api/model.pkl')
    ohe = joblib.load('api/ohe.pkl')
    model_columns = joblib.load('api/model_columns.pkl')
    
    # 2. Feature Engineering (Same as Jupyter Notebook)
    current_year = datetime.datetime.now().year
    df['age'] = current_year - df['year']
    df = df.dropna(subset=['age', 'make', 'model', 'mileage', 'location', 'price', 'url'])
    
    # 3. Run ML Inference on ALL rows locally
    print("Running ML inference on data")
    input_df = df[['age', 'make', 'model', 'mileage', 'location']]
    cat_encoded = ohe.transform(input_df[['make', 'model', 'location']])
    cat_df = pd.DataFrame(cat_encoded, columns=ohe.get_feature_names_out(), index=input_df.index)
    num_df = input_df[['age', 'mileage']]
    final_df = pd.concat([num_df, cat_df], axis=1)
    final_df = final_df.reindex(columns=model_columns, fill_value=0)
    
    # 4. Add predictions to the DataFrame
    df['predicted_price'] = model.predict(final_df)
    df['difference'] = df['predicted_price'] - df['price']
    
    # 5. Connect to Supabase and Push the data!
    print("Connecting to Supabase and uploading data")
    engine = create_engine(DATABASE_URL)
    
    # 'if_exists="replace"' means it will drop the old table and create a fresh one with this data
    df.to_sql('cars', engine, if_exists='replace', index=False)
    
    print("\nSUCCESS! Data uploaded to Supabase successfully!")
    print(f"Total cars uploaded: {len(df)}")

if __name__ == "__main__":
    migrate_data()
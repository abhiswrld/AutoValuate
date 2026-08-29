import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import joblib
import pandas as pd
from api.main import model, ohe, model_columns, db_engine
from datetime import datetime

print("Loading data...")
df = pd.read_sql("SELECT url, year, make, model, trim, name, mileage, location, condition, title_status, cylinders, drive, fuel, transmission, type, price FROM cars", db_engine)
print(f"Loaded {len(df)} rows.")

current_year = datetime.now().year
input_df = df.copy()
input_df['age'] = current_year - input_df['year']

print("Merging avg_prices...")
avg_prices = pd.read_csv('api/avg_prices.csv')
input_df = pd.merge(input_df, avg_prices, on=['year', 'make', 'model'], how='left')

print("Applying fallback logic...")
def fill_price(row):
    if pd.isna(row['avg_market_price']):
        return 5000 
    return row['avg_market_price']
input_df['avg_market_price'] = input_df.apply(fill_price, axis=1)
input_df['estimated_msrp'] = input_df['avg_market_price'] * (1 + 0.10 * input_df['age'])

print("Encoding...")
input_df['trim'] = input_df['trim'].fillna('unspecified')

def extract_trim_tier(name):
    if pd.isna(name): return 'base'
    name = str(name).lower()
    if any(k in name for k in ['type r', 'type-r', 'trd', 'amg', 'm3', 'm4', 'm5', 'srt', 'hellcat', 'platinum', 'limited', 'touring', 'grand touring', 'premium', 'denali', 'autobiography']):
        return 'high_performance_luxury'
    if any(k in name for k in ['ex-l', 'xle', 'xls', 'ltz', 'sl', 'sle', 'slt', 'titanium', 'lariat', 'king ranch', 'rubicon', 'sahara']):
        return 'high'
    if any(k in name for k in ['ex', 'se', 'sv', 'lt', 'sr5', 'sport', 'latitude', 'big horn', 'xlt']):
        return 'mid'
    if any(k in name for k in ['lx', 'le', 'ls', 's', 'base', 'xl', 'work']):
        return 'base'
    return 'unspecified'

# For DB recalculation, we should extract trim from URL or just use the current logic
# The DB has 'name' which is the car title? Wait, 'name' is not in the query!
# Let's check line 10: SELECT url, year, make, model, trim, mileage, location, condition, title_status, cylinders, drive, fuel, transmission, type, price FROM cars
# We need to add 'name' to the query.
input_df['location'] = input_df['location'].fillna('sanjose')
input_df['condition'] = input_df['condition'].fillna('good')
input_df['title_status'] = input_df['title_status'].fillna('clean')
input_df['cylinders'] = input_df['cylinders'].fillna('unspecified')
input_df['drive'] = input_df['drive'].fillna('unspecified')
input_df['fuel'] = input_df['fuel'].fillna('gas')
input_df['transmission'] = input_df['transmission'].fillna('automatic')
input_df['type'] = input_df['type'].fillna('unspecified')

if 'name' in input_df.columns:
    input_df['trim'] = input_df.apply(lambda row: extract_trim_tier(row['name']) if row['trim'] == 'unspecified' else row['trim'], axis=1)


cat_encoded = ohe.transform(input_df[['make', 'model', 'trim', 'location', 'condition', 'title_status', 'cylinders', 'drive', 'fuel', 'transmission', 'type']])
cat_df = pd.DataFrame(cat_encoded, columns=ohe.get_feature_names_out(), index=input_df.index)
num_df = input_df[['age', 'mileage', 'avg_market_price', 'estimated_msrp']]
final_df = pd.concat([num_df, cat_df], axis=1)
final_df = final_df.reindex(columns=model_columns, fill_value=0)

print("Predicting...")
predictions = model.predict(final_df)
update_df = pd.DataFrame({
    'url': df['url'],
    'predicted_price': predictions,
    'difference': predictions - df['price']
})

print("Sample predictions for 2025+ cars:")
sample = update_df[df['year'] >= 2025].head(10)
print(sample)


print("Updating database via temp table...")
update_df.to_sql('temp_predictions', db_engine, if_exists='replace', index=False)
from sqlalchemy import text
with db_engine.begin() as conn:
    conn.execute(text("""
        UPDATE cars c
        SET predicted_price = t.predicted_price, difference = t.difference
        FROM temp_predictions t
        WHERE c.url = t.url
    """))
    conn.execute(text("DROP TABLE temp_predictions"))

print("Done!")

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import joblib
import pandas as pd
from api.main import model, ohe, model_columns, db_engine
from datetime import datetime

print("Loading data...")
df = pd.read_sql("SELECT * FROM cars", db_engine)
print(f"Loaded {len(df)} rows.")

current_year = datetime.now().year
input_df = df.copy()
input_df['age'] = current_year - input_df['year']

print("Merging avg_prices...")
avg_prices = pd.read_csv('api/avg_prices.csv')
input_df = pd.merge(input_df, avg_prices, on=['year', 'make', 'model'], how='left')

# The current evaluate_url logic uses 0.95 fallback for old cars if avg_market_price is missing.
# Let's apply a simpler/saner fallback or match evaluate_url exactly.
print("Applying fallback logic...")
def fill_price(row):
    if pd.isna(row['avg_market_price']):
        return 5000 # reasonable fallback for unknown old cars instead of $30k!
    return row['avg_market_price']
input_df['avg_market_price'] = input_df.apply(fill_price, axis=1)

input_df['estimated_msrp'] = input_df['avg_market_price'] * (1 + 0.10 * input_df['age'])

print("Encoding...")
# Ensure missing features are filled
input_df['trim'] = input_df['trim'].fillna('unspecified')
input_df['location'] = input_df['location'].fillna('sanjose')
input_df['condition'] = input_df['condition'].fillna('good')
input_df['title_status'] = input_df['title_status'].fillna('clean')
input_df['cylinders'] = input_df['cylinders'].fillna('unspecified')
input_df['drive'] = input_df['drive'].fillna('unspecified')
input_df['fuel'] = input_df['fuel'].fillna('gas')
input_df['transmission'] = input_df['transmission'].fillna('automatic')
input_df['type'] = input_df['type'].fillna('unspecified')

cat_encoded = ohe.transform(input_df[['make', 'model', 'trim', 'location', 'condition', 'title_status', 'cylinders', 'drive', 'fuel', 'transmission', 'type']])
cat_df = pd.DataFrame(cat_encoded, columns=ohe.get_feature_names_out(), index=input_df.index)
num_df = input_df[['age', 'mileage', 'avg_market_price', 'estimated_msrp']]
final_df = pd.concat([num_df, cat_df], axis=1)
final_df = final_df.reindex(columns=model_columns, fill_value=0)

print("Predicting...")
predictions = model.predict(final_df)
df['new_predicted'] = predictions
df['new_difference'] = df['new_predicted'] - df['price']

print("Updating database...")
from sqlalchemy import text
with db_engine.begin() as conn:
    for i, row in df.iterrows():
        url = row['url']
        predicted = row['new_predicted']
        diff = row['new_difference']
        conn.execute(text("UPDATE cars SET predicted_price = :p, difference = :d WHERE url = :u"), {"p": float(predicted), "d": float(diff), "u": url})

print("Done!")

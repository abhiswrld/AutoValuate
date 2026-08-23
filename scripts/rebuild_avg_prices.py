"""
Rebuild avg_prices.csv from the LIVE database so every year/make/model combo
that exists in our DB gets a proper average market price anchor.

Then re-predict every car in the DB using the updated avg_prices.
"""
import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

import pandas as pd
from api.main import model, ohe, model_columns, db_engine
from datetime import datetime
from sqlalchemy import text

print("=" * 60)
print("STEP 1: Rebuild avg_prices.csv from live database")
print("=" * 60)

# Pull every year/make/model combo and compute the median price
# Using median instead of mean to be more resistant to outliers
avg_df = pd.read_sql("""
    SELECT year, make, model, 
           PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY price) AS avg_market_price,
           COUNT(*) as sample_count
    FROM cars 
    WHERE make IS NOT NULL AND model IS NOT NULL 
    AND price >= 500 AND price <= 150000
    AND year >= 1990
    GROUP BY year, make, model
    ORDER BY year, make, model
""", db_engine)

print(f"Generated {len(avg_df)} unique year/make/model combinations from DB")
print(f"  (was 7,206 rows in old avg_prices.csv)")

# Save it
avg_df[['year', 'make', 'model', 'avg_market_price']].to_csv('api/avg_prices.csv', index=False)
print(f"Saved new avg_prices.csv with {len(avg_df)} rows")

# Quick sanity check
mazda6 = avg_df[(avg_df['make'] == 'mazda') & (avg_df['model'] == '6')]
print(f"\nMazda 6 coverage: {len(mazda6)} year entries")
print(mazda6[['year', 'avg_market_price', 'sample_count']].to_string(index=False))

print()
print("=" * 60)
print("STEP 2: Re-predict every car using new avg_prices")
print("=" * 60)

# Reload the fresh avg_prices
avg_prices = pd.read_csv('api/avg_prices.csv')

# Load all cars
df = pd.read_sql("SELECT url, year, make, model, trim, mileage, location, condition, title_status, cylinders, drive, fuel, transmission, type, price FROM cars", db_engine)
print(f"Loaded {len(df)} cars from DB")

current_year = datetime.now().year
input_df = df.copy()
input_df['age'] = current_year - input_df['year']

# Merge with fresh avg_prices
input_df = pd.merge(input_df, avg_prices, on=['year', 'make', 'model'], how='left')

# Count coverage
matched = input_df['avg_market_price'].notna().sum()
total = len(input_df)
print(f"avg_market_price coverage: {matched}/{total} ({matched/total*100:.1f}%)")

# For the remaining unmatched cars, try a make+model average (across all years)
make_model_avg = avg_prices.groupby(['make', 'model'])['avg_market_price'].median().reset_index()
make_model_avg.columns = ['make', 'model', 'fallback_price']

input_df = pd.merge(input_df, make_model_avg, on=['make', 'model'], how='left')

def fill_price(row):
    if pd.notna(row['avg_market_price']):
        return row['avg_market_price']
    if pd.notna(row['fallback_price']):
        # Use make+model median, adjusted by age
        return row['fallback_price'] * max(0.3, (0.95 ** row['age']))
    return 5000  # last resort

input_df['avg_market_price'] = input_df.apply(fill_price, axis=1)
input_df['estimated_msrp'] = input_df['avg_market_price'] * (1 + 0.10 * input_df['age'])

# Fill NaN categoricals
for col in ['trim', 'location', 'condition', 'title_status', 'cylinders', 'drive', 'fuel', 'transmission', 'type']:
    defaults = {'trim': 'unspecified', 'location': 'sanjose', 'condition': 'good', 
                'title_status': 'clean', 'cylinders': 'unspecified', 'drive': 'unspecified',
                'fuel': 'gas', 'transmission': 'automatic', 'type': 'unspecified'}
    input_df[col] = input_df[col].fillna(defaults.get(col, 'unspecified'))

print("Encoding features...")
cat_encoded = ohe.transform(input_df[['make', 'model', 'trim', 'location', 'condition', 'title_status', 'cylinders', 'drive', 'fuel', 'transmission', 'type']])
cat_df = pd.DataFrame(cat_encoded, columns=ohe.get_feature_names_out(), index=input_df.index)
num_df = input_df[['age', 'mileage', 'avg_market_price', 'estimated_msrp']]
final_df = pd.concat([num_df, cat_df], axis=1)
final_df = final_df.reindex(columns=model_columns, fill_value=0)

print("Running predictions...")
predictions = model.predict(final_df)

update_df = pd.DataFrame({
    'url': df['url'],
    'predicted_price': predictions,
    'difference': predictions - df['price']
})

print(f"Updating {len(update_df)} rows in database...")
update_df.to_sql('temp_predictions', db_engine, if_exists='replace', index=False)

with db_engine.begin() as conn:
    conn.execute(text("""
        UPDATE cars c
        SET predicted_price = t.predicted_price, difference = t.difference
        FROM temp_predictions t
        WHERE c.url = t.url
    """))
    conn.execute(text("DROP TABLE temp_predictions"))

print()
print("=" * 60)
print("DONE! Sanity checking Mazda 6 predictions...")
print("=" * 60)

check = pd.read_sql("""
    SELECT year, mileage, price, predicted_price, difference, location
    FROM cars WHERE make = 'mazda' AND model = '6'
    ORDER BY year DESC, mileage ASC
    LIMIT 10
""", db_engine)
print(check.to_string(index=False))

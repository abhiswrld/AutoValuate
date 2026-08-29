import pandas as pd
import numpy as np
import os
import re
import datetime
from sqlalchemy import create_engine
from dotenv import load_dotenv
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder
from xgboost import XGBRegressor
from sklearn.metrics import mean_absolute_error, r2_score
import joblib

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)

# 1. ONLY pull cars that have been successfully deep-scraped!
print("Downloading deep-scraped data from Supabase...")
df = pd.read_sql("SELECT * FROM cars WHERE cylinders IS NOT NULL AND make IS NOT NULL", engine)

# 2. Fill any missing specs with 'unspecified' so OHE doesn't crash
cat_cols = ['condition', 'title_status', 'trim', 'cylinders', 'drive', 'fuel', 'transmission', 'type', 'location']
for col in cat_cols:
    df[col] = df[col].fillna('unspecified')

# Extract Trim Tiers if Trim is unspecified
def extract_trim_tier(name):
    if pd.isna(name): return 'base'
    name = str(name).lower()
    
    # Performance / Luxury
    if any(k in name for k in ['type r', 'type-r', 'trd', 'amg', 'm3', 'm4', 'm5', 'srt', 'hellcat', 'platinum', 'limited', 'touring', 'grand touring', 'premium', 'denali', 'autobiography']):
        return 'high_performance_luxury'
    
    # High / Mid-High
    if any(k in name for k in ['ex-l', 'xle', 'xls', 'ltz', 'sl', 'sle', 'slt', 'titanium', 'lariat', 'king ranch', 'rubicon', 'sahara']):
        return 'high'
        
    # Mid
    if any(k in name for k in ['ex', 'se', 'sv', 'lt', 'sr5', 'sport', 'latitude', 'big horn', 'xlt']):
        return 'mid'
        
    # Base
    if any(k in name for k in ['lx', 'le', 'ls', 's', 'base', 'xl', 'work']):
        return 'base'
        
    return 'unspecified'

df['trim'] = df.apply(lambda row: extract_trim_tier(row['name']) if row['trim'] == 'unspecified' else row['trim'], axis=1)

# 3. Filter outliers
df = df[(df['price'] >= 800) & (df['price'] <= 100000)]
df = df[(df['mileage'] >= 100) & (df['mileage'] <= 300000)]
df = df.dropna(subset=['name', 'price', 'mileage'])

print(f"Rows before outlier removal: {len(df)}")
# Calculate age
current_year = datetime.datetime.now().year
df['age'] = current_year - df['year']

# 1. Drop extreme classic cars
df = df[df['age'] <= 30]

# 2. Drop unrealistic junk/parts cars
df = df[df['price'] >= 2000]

# 3. Drop impossible mileage for the age (clip age to 1 to protect brand new cars)
df = df[df['mileage'] <= (df['age'].clip(lower=1) * 25000)]

# 4. Advanced IQR Outlier Removal per Make/Model
Q1 = df.groupby(['make', 'model'])['price'].transform('quantile', 0.25)
Q3 = df.groupby(['make', 'model'])['price'].transform('quantile', 0.75)
IQR = Q3 - Q1
df = df[(df['price'] >= Q1 - 1.5 * IQR) & (df['price'] <= Q3 + 1.5 * IQR)]

print(f"Rows after outlier removal: {len(df)}")


# ---

# Calculate Market Baselines to stabilize AI predictions
print('Calculating market baselines and building robust lookup table...')

# Create a robust lookup table with interpolated missing years
current_year = datetime.datetime.now().year
makes_models = df[['make', 'model']].drop_duplicates()
years = pd.DataFrame({'year': range(1990, current_year + 2)})  # 1990 to 2027

# Cross join makes_models with years safely
grid = makes_models.merge(years, how='cross')
avg_prices = df.groupby(['make', 'model', 'year'])['price'].mean().reset_index()
avg_prices.rename(columns={'price': 'avg_market_price'}, inplace=True)
lookup = pd.merge(grid, avg_prices, on=['make', 'model', 'year'], how='left')

def fill_group(grp):
    grp = grp.sort_values('year')
    grp['avg_market_price'] = grp['avg_market_price'].interpolate(method='linear')
    
    valid = grp.dropna(subset=['avg_market_price'])
    if not valid.empty:
        max_year = valid['year'].max()
        max_price = valid[valid['year'] == max_year]['avg_market_price'].iloc[0]
        min_year = valid['year'].min()
        min_price = valid[valid['year'] == min_year]['avg_market_price'].iloc[0]
        
        def fill_extrapolate(row):
            if pd.notna(row['avg_market_price']):
                return row['avg_market_price']
            if row['year'] > max_year:
                return max_price * (1.05 ** (row['year'] - max_year))
            else:
                return min_price * (0.94 ** (min_year - row['year']))
                
        grp['avg_market_price'] = grp.apply(fill_extrapolate, axis=1)
    else:
        grp['avg_market_price'] = 5000
        
    grp['avg_market_price'] = grp['avg_market_price'].cummax()
    return grp

lookup = lookup.groupby(['make', 'model']).apply(fill_group)
# reset_index will bring make and model back from the MultiIndex
lookup = lookup.reset_index(level=['make', 'model'])
lookup = lookup.reset_index(drop=True)

df = pd.merge(df, lookup, on=['make', 'model', 'year'], how='left')
df['estimated_msrp'] = df['avg_market_price'] * (1 + 0.10 * df['age'])

# Export lookup table for the Live API scraper to use
os.makedirs('../api', exist_ok=True)
lookup.to_csv('../api/avg_prices.csv', index=False)
print('Saved robust avg_prices.csv lookup table.')

# Define Features (X) and Target (y)
X = df[['age', 'make', 'model', 'trim', 'mileage', 'location', 'condition', 
        'title_status', 'cylinders', 'drive', 'fuel', 'transmission', 'type', 'avg_market_price', 'estimated_msrp']]
y = df['price']

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# OneHotEncoder
ohe = OneHotEncoder(handle_unknown='ignore', sparse_output=False)
cat_features = ['make', 'model', 'trim', 'location', 'condition', 
                'title_status', 'cylinders', 'drive', 'fuel', 'transmission', 'type']

X_train_encoded = ohe.fit_transform(X_train[cat_features])
X_test_encoded = ohe.transform(X_test[cat_features])

X_train_encoded_df = pd.DataFrame(X_train_encoded, columns=ohe.get_feature_names_out(), index=X_train.index)
X_test_encoded_df = pd.DataFrame(X_test_encoded, columns=ohe.get_feature_names_out(), index=X_test.index)

X_train_num = X_train[['age', 'mileage', 'avg_market_price', 'estimated_msrp']]
X_test_num = X_test[['age', 'mileage', 'avg_market_price', 'estimated_msrp']]

X_train_final = pd.concat([X_train_num, X_train_encoded_df], axis=1)
X_test_final = pd.concat([X_test_num, X_test_encoded_df], axis=1)

print(f"Training matrix shape: {X_train_final.shape}")

# ---

# Train XGBoost with Monotonic Constraints
# age and mileage (first two columns) must have negative correlation with price (-1)
# avg_market_price and estimated_msrp (next two columns) have positive correlation (1)
monotone_constraints = tuple([-1, -1, 1, 1] + [0] * (X_train_final.shape[1] - 4))

model = XGBRegressor(
    n_estimators=500,
    learning_rate=0.05,
    max_depth=8,
    subsample=0.8,
    colsample_bytree=0.8,
    monotone_constraints=monotone_constraints,
    random_state=42
)

print("Training model on data...")
model.fit(X_train_final, y_train)
print("Training complete!")


# ---

# Predict
predictions = model.predict(X_test_final)
mae = mean_absolute_error(y_test, predictions)
r2 = r2_score(y_test, predictions)

print("Model Performance:")
print(f"Mean Absolute Error (MAE): ${mae:,.2f}")
print(f"R-Squared (R2): {r2:.2f}")

# Sample comparison
comparison = pd.DataFrame({
    'Actual_Price': y_test.values[:10],
    'Predicted_Price': predictions[:10].astype(int),
    'Age': X_test['age'].values[:10],
    'Make': X_test['make'].values[:10],
    'Model': X_test['model'].values[:10],
    'Cylinders': X_test['cylinders'].values[:10],
    'Trim': X_test['trim'].values[:10],
    'Drive': X_test['drive'].values[:10],
    'Fuel': X_test['fuel'].values[:10]
})
print("\nSample Predictions vs Actuals:")
print(comparison)

# ---

# Save artifacts
os.makedirs('../api', exist_ok=True)
joblib.dump(model, '../api/model.pkl')
joblib.dump(ohe, '../api/ohe.pkl')
joblib.dump(X_train_final.columns.tolist(), '../api/model_columns.pkl')
print("\nArtifacts saved successfully!")

# ---


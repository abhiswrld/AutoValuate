# Core Data Processing
import pandas as pd
import numpy as np
import os
import re
import datetime
from sqlalchemy import create_engine
from dotenv import load_dotenv

# Visualization
import matplotlib.pyplot as plt
import seaborn as sns

# ML & Embeddings
from sentence_transformers import SentenceTransformer
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder
from xgboost import XGBRegressor
from sklearn.metrics import mean_absolute_error, r2_score
import joblib

# Environment Setup
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)

# Bring in all data from Supabase
print("Bringing data from Supabase...")
df = pd.read_sql("SELECT * FROM cars WHERE price >= 1000", engine)

# Initial NA handling for known scraped fields
df['condition'] = df['condition'].fillna('unspecified')
df['title_status'] = df['title_status'].fillna('unspecified')

print(f"Total records brought in: {len(df)}")
df.head()

# ---

df.sample(10)

# ---

df.describe()

# ---

df['location'] = df['location'].astype(str).str.split('/').str[0].str.lower().str.strip()

# ---

df.sample(10)

# ---

print(df[['price', 'mileage']].describe())

# ---

# Plot price distribution

plt.figure(figsize=(10, 5))
sns.histplot(df['price'], bins=50, kde=True)
plt.title('Distribution of Car Prices (Before Cleaning)')
plt.xlabel('Price ($)')
plt.show()

# ---

# Plot Mileage distribution
plt.figure(figsize=(10, 5))
sns.histplot(df['mileage'].dropna(), bins=50, kde=True)
plt.title('Distribution of Mileage (Before Cleaning)')
plt.xlabel('Mileage')
plt.show()

# ---

# Define realistic bounds for market vehicles
MIN_PRICE = 800
MAX_PRICE = 100000
MIN_MILEAGE = 100
MAX_MILEAGE = 300000

# Filter outliers and drop rows missing absolute core requirements
df_clean = df[
    (df['price'] >= MIN_PRICE) & 
    (df['price'] <= MAX_PRICE) &
    (df['mileage'] >= MIN_MILEAGE) & 
    (df['mileage'] <= MAX_MILEAGE) &
    (df['name'].notna())
].copy()

# Extract Year and calculate Age
df_clean['year'] = df_clean['name'].astype(str).str.extract(r'(\b(19[0-9]{2}|20[0-2][0-9])\b)')[0]
df_clean = df_clean.dropna(subset=['year'])
df_clean['year'] = df_clean['year'].astype(int)

current_year = datetime.datetime.now().year
df_clean['age'] = current_year - df_clean['year']

# Standardize location string
df_clean['location'] = df_clean['location'].astype(str).str.split('/').str[0].str.lower().str.strip()

print(f"Rows after cleaning: {len(df_clean)}")

# ---

# Plot price distribution (after)

plt.figure(figsize=(10, 5))
sns.histplot(df_clean['price'], bins=50, kde=True)
plt.title('Distribution of Car Prices (After Cleaning)')
plt.xlabel('Price ($)')
plt.show()

# ---

# Plot Mileage distribution (after)

plt.figure(figsize=(10, 5))
sns.histplot(df_clean['mileage'].dropna(), bins=50, kde=True)
plt.title('Distribution of Mileage (After Cleaning)')
plt.xlabel('Mileage')
plt.show()

# ---

import re

# Extract Year (Looks for 19xx or 20xx)
df_clean['year'] = df_clean['name'].str.extract(r'(\b(19[0-9]{2}|20[0-2][0-9])\b)')[0]

# Drop rows that didn't have a year in the title
df_clean = df_clean.dropna(subset=['year'])
df_clean['year'] = df_clean['year'].astype(int)

df_clean

# ---

import datetime

# Get the current year
current_year = datetime.datetime.now().year

# Calculate age
df_clean['age'] = current_year - df_clean['year']

# Quick check
print(df_clean[['name', 'year', 'age']].head())

# ---

df_clean.to_csv('../data/clean_listings.csv', index=False)

# ---

from sklearn.model_selection import train_test_split
from xgboost import XGBRegressor
from sklearn.metrics import mean_absolute_error, r2_score

# ---

# Initialize local HuggingFace embedding model
print("Loading SentenceTransformer model...")
embed_model = SentenceTransformer('all-MiniLM-L6-v2')

# Generate embeddings for the 'name' column
print("Generating title embeddings...")
title_embeddings = embed_model.encode(df_clean['name'].tolist(), show_progress_bar=True)

# Convert embeddings to DataFrame
embed_df = pd.DataFrame(title_embeddings, index=df_clean.index)
embed_df.columns = [f"embed_{i}" for i in range(embed_df.shape[1])]

del embed_model

# ---

# One-Hot Encode remaining categorical features
ohe = OneHotEncoder(handle_unknown='ignore', sparse_output=False)
cat_features = ['condition', 'title_status']

cat_encoded = ohe.fit_transform(df_clean[cat_features])
cat_df = pd.DataFrame(cat_encoded, columns=ohe.get_feature_names_out(), index=df_clean.index)

# Isolate numerical features
num_df = df_clean[['age', 'mileage']].copy()

# Construct final feature matrix (X) and target (y)
X = pd.concat([num_df, cat_df, embed_df], axis=1)
y = df_clean['price']

# Train/Test Split
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

print(f"Training matrix shape: {X_train.shape}")
print(f"Testing matrix shape: {X_test.shape}")

# ---

# Initialize and train XGBoost Regressor
model = XGBRegressor(
    n_estimators=500,
    learning_rate=0.05,
    max_depth=8,
    subsample=0.8,
    colsample_bytree=0.8,
    random_state=42
)

print("Training model...")
model.fit(X_train, y_train)
print("Training complete.")

# ---

# Generate predictions
predictions = model.predict(X_test)

# Calculate metrics
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
    'Mileage': X_test['mileage'].values[:10],
    'Title': df_clean.loc[X_test.index[:10], 'name'].values
})
print("\nSample Predictions vs Actuals:")
print(comparison)

# ---

import joblib
import os

os.makedirs('../api', exist_ok=True)

# Save the XGBoost model
joblib.dump(model, '../api/model.pkl')

# Save the One-Hot Encoder
joblib.dump(ohe, '../api/ohe.pkl')

# Save the list of model columns for future reference
joblib.dump(X_train.columns.tolist(), '../api/model_columns.pkl')

# Save the sentence transformer model
# embed_model.save('../api/sentence_transformer_model')

print("Artifacts saved successfully: model.pkl, ohe.pkl, model_columns.pkl, sentence_transformer_model/")

# ---


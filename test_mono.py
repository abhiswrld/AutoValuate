import pandas as pd
years = list(range(1990, 2027))
current_year = 2026
max_year = 2024
max_price = 25000

def fill_smooth_price(row):
    if row['year'] >= current_year - 1:
        return max_price * 1.30 * (1.05 ** (row['year'] - max_year))
    elif row['year'] > max_year:
        return max_price * (1.05 ** (row['year'] - max_year))
    else:
        return max_price * (0.94 ** (max_year - row['year']))

df = pd.DataFrame({'year': years})
df['age'] = current_year - df['year']
df['avg_market_price'] = df.apply(fill_smooth_price, axis=1)
df['estimated_msrp'] = df['avg_market_price'] * (1 + 0.10 * df['age'])
print("Before cummax:")
print(df[['year', 'avg_market_price', 'estimated_msrp']].tail(10))

df['estimated_msrp'] = df['estimated_msrp'].cummax()
df['avg_market_price'] = df['avg_market_price'].cummax()
print("\nAfter cummax:")
print(df[['year', 'avg_market_price', 'estimated_msrp']].tail(10))

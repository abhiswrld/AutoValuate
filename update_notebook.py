import json

with open('ml/AutoValuate.ipynb', 'r') as f:
    nb = json.load(f)

for cell in nb['cells']:
    if cell['cell_type'] == 'code':
        source = "".join(cell['source'])
        
        # 1. Update Outlier Removal
        if 'def remove_outliers(group):' in source:
            new_lines = []
            skip = False
            for line in cell['source']:
                if 'def remove_outliers(group):' in line:
                    skip = True
                    new_source = """# 4. Advanced IQR Outlier Removal per Make/Model
Q1 = df.groupby(['make', 'model'])['price'].transform('quantile', 0.25)
Q3 = df.groupby(['make', 'model'])['price'].transform('quantile', 0.75)
IQR = Q3 - Q1
df = df[(df['price'] >= Q1 - 1.5 * IQR) & (df['price'] <= Q3 + 1.5 * IQR)]

print(f"Rows after outlier removal: {len(df)}")
"""
                    new_lines.extend([line + '\n' for line in new_source.split('\n')[1:-1]])
                if skip and 'print(f"Rows after outlier removal:' in line:
                    skip = False
                    continue
                if not skip:
                    new_lines.append(line)
            
            cell['source'] = new_lines

with open('ml/AutoValuate.ipynb', 'w') as f:
    json.dump(nb, f, indent=1)

print("Notebook updated successfully.")

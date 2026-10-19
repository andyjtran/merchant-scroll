import pandas as pd
import requests
import unicodedata
from datetime import date
from string import ascii_uppercase

# --- Configuration & Constants ---
INPUT_FILE = '/home/andy/Downloads/moxfield_haves.csv'
OUTPUT_FILE = '/home/andy/Downloads/cardkingdom.csv'
FDN_RELEASE_DATE = date(2024, 11, 15)
SCRYFALL_SEARCH = "https://api.scryfall.com/cards/search"
SCRYFALL_SET = "https://api.scryfall.com/sets/{}"

# Sets requiring 3-digit vs 4-digit padding
SETS_3_DIGIT = {'afr', 'bro', 'brr', 'dmu', 'eld', 'j22', 'm19', 'm20', 'm21', 'neo', 'tneo', 'one', 'slx', 'snc', 'tsnc', 'vow', 'tvow', 'war'}

# Use a session for faster consecutive requests
session = requests.Session()

def normalize_name(name):
    if not isinstance(name, str): return name
    return unicodedata.normalize('NFD', name).encode('ascii', 'ignore').decode('ascii')

def get_scryfall_data(query):
    """Fetch all pages of data from Scryfall for a specific query."""
    results = []
    params = {'q': query, 'unique': 'prints'}
    url = SCRYFALL_SEARCH
    while url:
        resp = session.get(url, params=params if url == SCRYFALL_SEARCH else None)
        if resp.status_code != 200: break
        data = resp.json()
        results.extend(data.get('data', []))
        url = data.get('next_page') if data.get('has_more') else None
    return results

# --- 1. Load and Initial Clean ---
df = pd.read_csv(INPUT_FILE)
df['Name'] = df['Name'].apply(normalize_name)

# Filter Art cards/Promos (Vectorized)
mask_exclude = (df['Edition'].str.len() == 4) & (
    df['Edition'].str.startswith('a') | 
    df['Edition'].str.startswith('f') | 
    df['Edition'].str.contains('p30a')
)
df = df[~mask_exclude].copy()

# Remove specific tokens (Vectorized instead of loop)
excluded_tokens = pd.DataFrame([
    ['Goblin Token', 'tafr', 'foil'],
    ['Skeleton Token', 'tafr', 'foil'],
    ['The Atropal Token', 'tafr', 'foil']
], columns=['Name', 'Edition', 'Foil'])

df = df.merge(excluded_tokens, on=['Name', 'Edition', 'Foil'], how='left', indicator=True)
df = df[df['_merge'] == 'left_only'].drop(columns=['_merge'])

# --- 2. Collector Number Padding (Vectorized) ---
def pad_cn(row):
    cn = str(row['Collector Number'])
    # Clean possible existing letters/parens before padding
    cn_clean = "".join(filter(str.isdigit, cn))
    suffix = "".join(filter(str.isalpha, cn))
    
    target_len = 3 if row['Edition'].lower() in SETS_3_DIGIT else 4
    padded = cn_clean.zfill(target_len)
    return f"({padded}{suffix})"

df['Formatted_CN'] = df.apply(pad_cn, axis=1)

# --- 3. Basic Land Logic (Batch API calls) ---
lands = ['Plains', 'Island', 'Swamp', 'Mountain', 'Forest']
land_sets = ['eld', 'war', 'm19', 'm20']
land_data = []

for s in land_sets:
    q = f'set:{s} ({" or ".join([f"name:\"{l}\"" for l in lands])})'
    for card in get_scryfall_data(q):
        land_data.append({
            'Name': card['name'], 
            'Edition': card['set'], 
            'Collector Number': card['collector_number']
        })

if land_data:
    df_ld = pd.DataFrame(land_data).sort_values(['Name', 'Edition', 'Collector Number'])
    df_ld['Letter'] = df_ld.groupby(['Name', 'Edition']).cumcount().map(lambda x: ascii_uppercase[x])
    
    # Merge letters back to main DF
    df = df.merge(df_ld, on=['Name', 'Edition', 'Collector Number'], how='left')
    # Update CN for lands that got a letter
    mask = df['Letter'].notna()
    df.loc[mask, 'Formatted_CN'] = df.loc[mask, 'Collector Number'].astype(str) + " " + df.loc[mask, 'Letter']

# --- 4. Token Processing (Batch API & Date Cache) ---
token_mask = (df['Edition'].str.len() == 4) & (df['Edition'].str.startswith('t'))
target_tokens = df[token_mask][['Name', 'Edition']].drop_duplicates()

set_cache = {}
token_counts = {}

for _, row in target_tokens.iterrows():
    base_set = row['Edition'][1:]
    # Cache set release date
    if base_set not in set_cache:
        r = session.get(SCRYFALL_SET.format(base_set))
        if r.status_code == 200:
            set_cache[base_set] = date.fromisoformat(r.json()['released_at'])
    
    # Count unique prints for this token in this set
    q = f'set:{row["Edition"]} name:"{row["Name"]}"'
    token_counts[(row['Name'], row['Edition'])] = len(get_scryfall_data(q))

def finalize_token_name(row):
    if not (len(row['Edition']) == 4 and row['Edition'].startswith('t')):
        return row['Name']
    
    base_set = row['Edition'][1:]
    is_post_fdn = set_cache.get(base_set, date(1900,1,1)) >= FDN_RELEASE_DATE
    unique_count = token_counts.get((row['Name'], row['Edition']), 0)
    
    name = f"{row['Name']} Token "
    cn_clean = "".join(filter(str.isdigit, str(row['Collector Number'])))
    
    if is_post_fdn:
        return f"{name}({cn_clean.zfill(4)})"
    elif unique_count > 1:
        return f"{name}{row['Formatted_CN']}"
    return name

df['Title'] = df.apply(finalize_token_name, axis=1)

# --- 5. Bonus Sheets & DFCs ---
# Update Title for standard cards not processed as tokens
df.loc[df['Title'].isna(), 'Title'] = df['Name']

# Bonus Sheets
df.loc[df['Edition'] == 'wot', 'Title'] += " " + df['Formatted_CN']
df.loc[df['Edition'] == 'otp', 'Title'] += " " + df['Formatted_CN'].str.slice(0, 5) + " - Showcase)"

# DFC Trimming
dfc_mask = df['Title'].str.contains('//') & ~df['Title'].str.contains('Token')
df.loc[dfc_mask, 'Title'] = df.loc[dfc_mask, 'Title'].str.split('//').str[0].str.strip()

# Handle Prerelease
PRERELEASE = {'pdft': 'dft', 'pmkm': 'mkm', 'ptdm': 'tdm'}
is_pre = df['Edition'].str.lower().isin(PRERELEASE.keys())
df.loc[is_pre, 'Title'] += " (Prerelease Foil)"
df['Edition'] = df['Edition'].replace(PRERELEASE)

# Final Cleanup
df['Edition'] = df['Edition'].apply(lambda x: x[1:] if (len(x) == 4 and x.startswith('t')) else x)
df.rename(columns={'Count': 'Qty'}, inplace=True)
df[['Title', 'Edition', 'Foil', 'Qty']].to_csv(OUTPUT_FILE, index=False)
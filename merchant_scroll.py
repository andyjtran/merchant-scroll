import pandas as pd
import requests
from string import ascii_uppercase
import unicodedata
from datetime import date

df = pd.read_csv('/home/andy/Downloads/moxfield_haves.csv')

# Remove art cards, Jumpstart theme cards, and 30th Anniversary Play Promo cards
df = df[~((df['Edition'].str.len() == 4) & (df['Edition'].str.startswith('a') | df['Edition'].str.startswith('f') | df['Edition'].str.contains('p30a')))]

# Remove Adventures in the Forgotten Realms dungeon tokens
EXCLUDED_TOKENS = [
    ('Goblin Token', 'tafr', 'foil'),
    ('Skeleton Token', 'tafr', 'foil'),
    ('The Atropal Token', 'tafr', 'foil'),
]

for token_name, token_edition, token_foil in EXCLUDED_TOKENS:
    df = df[~(
        (df['Name'] == token_name) &
        (df['Edition'].str.lower() == token_edition) &
        (df['Foil'] == token_foil)
    )]

# Normalize special characters in card names (e.g. á -> a, ü -> u)
def normalize_name(name):
    return unicodedata.normalize('NFD', name).encode('ascii', 'ignore').decode('ascii')

df['Name'] = df['Name'].apply(normalize_name)


# Basic Land Formatting
# Scryfall API to count unique prints of basic lands for relevant sets
basic_land = ['Plains','Island','Swamp','Mountain','Forest']
scryfall_url = "https://api.scryfall.com/cards/search"
scryfall_land = []
editions_with_assigned_letters = ['eld', 'war', 'm19', 'm20']
for edition in editions_with_assigned_letters:
    for land in basic_land:
        query = f'set:{edition} name:"{land}" unique:prints'
        has_more = True
        page_url = scryfall_url
        while has_more:
            response = requests.get(page_url, params={'q': query})
            if response.status_code == 200:
                response_json = response.json()
                has_more = response_json['has_more']
                page_url = response_json['next_page'] if has_more else ''
                for card in response_json['data']:
                    scryfall_land.append({
                        'Name': card['name'],
                        'Edition': card['set'],
                        'Collector Number': card['collector_number']
                    })
            else:
                has_more = False

df_land = pd.DataFrame(scryfall_land)
df_land = df_land.sort_values(by=['Name','Edition', 'Collector Number'])

def assign_letters(group):
    group['Letter'] = [ascii_uppercase[i] for i in range(len(group))]
    return group

df_land_letter = df_land.groupby(['Name','Edition'], as_index=True).apply(assign_letters, include_groups=False)
df_land_letter = df_land_letter.reset_index(drop=False)
df_land_letter['Collector Number'] = df_land_letter['Collector Number'].astype(str)
df = pd.merge(df, df_land_letter, on=['Name','Edition', 'Collector Number'], how='left')
df.loc[pd.notna(df['Letter']), 'Collector Number'] = df['Collector Number'].astype(str) + ' ' + df['Letter'].fillna('')
df = df.drop(columns=['Letter'])

# Token Formatting
# Scryfall API to count unique prints of tokens in each set
token_edition = df[(df['Edition'].str.len() == 4) & (df['Edition'].str.startswith('t'))]
scryfall_token = []

for edition, name in zip(token_edition['Edition'], token_edition['Name']):
    query = f'set:{edition} name:"{name}" unique:prints'
    has_more = True
    page_url = scryfall_url
    while has_more:
        response = requests.get(page_url, params={'q': query})
        if response.status_code == 200:
            response_json = response.json()
            has_more = response_json['has_more']
            page_url = response_json['next_page'] if has_more else ''
            for card in response_json['data']:
                scryfall_token.append({
                    'Name': card['name'],
                    'Edition': card['set'],
                    'Collector Number': card['collector_number']
                })
        else:
            has_more = False

df_token = pd.DataFrame(scryfall_token)
unique_token = df_token.groupby(['Name', 'Edition'])['Collector Number'].nunique().reset_index(name='Unique Count')
df = pd.merge(df, unique_token, on=['Name','Edition'], how='left')

# Collector Number Formatting
editions_with_three_digit_collector_number = ['afr', 'bro', 'brr', 'dmu', 'eld', 'j22', 'm19', 'm20', 'm21', 'neo', 'tneo', 'one', 'slx', 'snc', 'tsnc', 'vow', 'tvow', 'war']

def format_collector_number(row):
    if row['Edition'] in editions_with_three_digit_collector_number:
        length = len(str(row['Collector Number']))
        if length == 2:
            return '(0' + str(row['Collector Number']) + ')'
        elif length == 1:
            return '(00' + str(row['Collector Number']) + ')'
        else:
            return '('+ (row['Collector Number']) + ')'
    else:
        length = len(str(row['Collector Number']))
        if length == 3:
            return '(0' + str(row['Collector Number']) + ')'
        elif length == 2:
            return '(00' + str(row['Collector Number']) + ')'
        elif length == 1:
            return '(000' + str(row['Collector Number']) + ')'
        else:
            return '('+ (row['Collector Number']) + ')'
    
df['Collector Number'] = df.apply(format_collector_number, axis=1)

# Append collector number to basic lands
df.loc[df['Name'].isin(basic_land),'Name'] = df['Name'] + ' ' + df['Collector Number'].astype(str)

# Append collector number to tokens
# Sets released on or after Foundations (2024-11-15) always append a 4-digit collector number.
# Earlier sets only append when there are multiple prints of the same token in a set.
FDN_RELEASE_DATE = date(2024, 11, 15)
scryfall_set_url = "https://api.scryfall.com/sets/{}"
set_release_cache = {} 

token_editions = df[(df['Edition'].str.len() == 4) & (df['Edition'].str.startswith('t'))]['Edition'].unique()
for edition in token_editions:
    base_code = edition[1:]  # strip leading 't' to get the parent set code
    if base_code in set_release_cache:
        continue
    response = requests.get(scryfall_set_url.format(base_code))
    if response.status_code == 200:
        released_at_str = response.json().get('released_at', '')
        try:
            set_release_cache[base_code] = date.fromisoformat(released_at_str)
        except ValueError:
            set_release_cache[base_code] = None
    else:
        set_release_cache[base_code] = None

def is_post_fdn(edition):
    base_code = edition[1:] if (len(edition) == 4 and edition.startswith('t')) else edition
    release = set_release_cache.get(base_code)
    return release is not None and release >= FDN_RELEASE_DATE

token_str = ' Token '
df['Name'] = df.apply(lambda x: x['Name'] + token_str if (len(x['Edition']) == 4 and x['Edition'].startswith('t')) else x['Name'], axis=1)

def append_token_collector_number(row):
    is_token = len(row['Edition']) == 4 and row['Edition'].startswith('t')
    if not is_token:
        return row['Name']
    cn_raw = str(row['Collector Number']).lstrip('(').rstrip(')')
    if is_post_fdn(row['Edition']):
        return row['Name'] + '(' + cn_raw.zfill(4) + ')'
    if row['Unique Count'] > 1:
        return row['Name'] + row['Collector Number']
    return row['Name']

df['Name'] = df.apply(append_token_collector_number, axis=1)

# Append collector number to bonus sheet
df.loc[df['Edition'].isin(['wot']),'Name'] = df['Name'] + ' ' + df['Collector Number'].astype(str)
df.loc[df['Edition'].isin(['otp']),'Name'] = df['Name'] + ' ' + df['Collector Number'].astype(str).str.slice(0, 5) + ' - Showcase)'

# Trim names for double-faced cards
# Specifying layouts ensures split cards are not trimmed
STRIP_LAYOUTS = {'transform', 'modal_dfc'}

dfc_cards = df[df['Name'].str.contains('//', na=False) & ~df['Name'].str.contains('Token')]
dfc_unique = dfc_cards[['Name', 'Edition']].drop_duplicates()

scryfall_layout_url = "https://api.scryfall.com/cards/named"
layout_cache = {}  # keyed by (name_front, edition)

for _, row in dfc_unique.iterrows():
    front_name = row['Name'].split('//')[0].strip()
    edition = row['Edition']
    key = (front_name, edition)
    if key in layout_cache:
        continue
    response = requests.get(scryfall_layout_url, params={'exact': front_name, 'set': edition})
    if response.status_code == 200:
        layout_cache[key] = response.json().get('layout', '')
    else:
        # Fallback: try without set constraint
        response = requests.get(scryfall_layout_url, params={'exact': front_name})
        layout_cache[key] = response.json().get('layout', '') if response.status_code == 200 else ''

def should_strip(row):
    if '//' not in str(row['Name']) or 'Token' in str(row['Name']):
        return False
    front_name = row['Name'].split('//')[0].strip()
    layout = layout_cache.get((front_name, row['Edition']), '')
    return layout in STRIP_LAYOUTS

strip_mask = df.apply(should_strip, axis=1)
df.loc[strip_mask, 'Name'] = df.loc[strip_mask, 'Name'].str.split('//').str[0].str.strip()

df['Edition'] = df['Edition'].apply(lambda x: x[1:] if (len(x) == 4 and x.startswith('t')) else x)

# Prerelease Foil Formatting
PRERELEASE_EDITIONS = ['pdft', 'pmkm', 'ptdm']
df.loc[df['Edition'].str.lower().isin(PRERELEASE_EDITIONS), 'Name'] = df['Name'] + ' (Prerelease Foil)'
df['Edition'] = df['Edition'].apply(lambda x: x[1:] if x.lower() in PRERELEASE_EDITIONS else x)


# Header Formatting
df.rename(columns={'Name': 'Title', 'Count': 'Qty'}, inplace=True)
cardkingdom_column_subset = ['Title','Edition','Foil','Qty']
df = df[cardkingdom_column_subset]

# Create cardkingdom.csv
df.to_csv('/home/andy/Downloads/cardkingdom.csv', index=False)
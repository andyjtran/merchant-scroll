import pandas as pd
import requests
from string import ascii_uppercase

df = pd.read_csv('/home/andy/Downloads/moxfield_haves.csv')

# Remove art cards, Jumpstart theme cards, and 30th Anniversary Play Promo cards
df = df[~((df['Edition'].str.len() == 4) & (df['Edition'].str.startswith('a') | df['Edition'].str.startswith('f') | df['Edition'].str.contains('p30a')))]

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
token_str = ' Token '
df['Name'] = df.apply(lambda x: x['Name'] + token_str if (len(x['Edition']) == 4 and x['Edition'].startswith('t')) else x['Name'], axis=1)
df['Name'] = df.apply(lambda x: x['Name'] + x['Collector Number'] if (len(x['Edition']) == 4 and x['Edition'].startswith('t') and x['Unique Count'] > 1) else x['Name'], axis=1)
# Append collector number to bonus sheet
df.loc[df['Edition'].isin(['wot']),'Name'] = df['Name'] + ' ' + df['Collector Number'].astype(str)
df.loc[df['Edition'].isin(['otp']),'Name'] = df['Name'] + ' ' + df['Collector Number'].astype(str).str.slice(0, 5) + ' - Showcase)'
# Trim names for double-faced cards
mask = ~df['Name'].str.contains('Token')
df.loc[mask, 'Name'] = df.loc[mask, 'Name'].str.split('//').str[0]
df['Edition'] = df['Edition'].apply(lambda x: x[1:] if (len(x) == 4 and x.startswith('t')) else x)

# Header Formatting
df.rename(columns={'Name': 'Title', 'Count': 'Qty'}, inplace=True)
cardkingdom_column_subset = ['Title','Edition','Foil','Qty']
df = df[cardkingdom_column_subset]

# Create cardkingdom.csv
df.to_csv('/home/andy/Downloads/cardkingdom.csv', index=False)
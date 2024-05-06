import pandas as pd
import requests
from string import ascii_uppercase

df = pd.read_csv('/home/andy/Downloads/moxfield_haves.csv')

# Remove Art cards, Jumpstart theme cards, and 30th Anniversary Play Promo cards
df = df[~((df['Edition'].str.len() == 4) & (df['Edition'].str.startswith('a') | df['Edition'].str.startswith('f') | df['Edition'].str.contains('p30a')))]

# Card Kingdom assigned a letter to basic lands before Ikoria: Lair of Behemoths (IKO) / Q2 2020 whenever basic lands had mulitple arts
# Call Scryfall API to get basic land collector numbers and assign letter
editions_with_assigned_letters = ['eld', 'war', 'm19', 'm20']
basic_land = ['Plains','Island','Swamp','Mountain','Forest']

scryfall_url = "https://api.scryfall.com/cards/search"

cards_data = []

for edition in editions_with_assigned_letters:
    for land in basic_land:
        query = f'set:{edition} name:"{land}" unique:prints'
        has_more = True
        page_url = scryfall_url
        # Paginate through each basic land art
        while has_more:
            response = requests.get(page_url, params={'q': query})
            if response.status_code == 200:
                response_json = response.json()
                has_more = response_json['has_more']
                page_url = response_json['next_page'] if has_more else ''
                for card in response_json['data']:
                    cards_data.append({
                        'Name': card['name'],
                        'Edition': card['set'],
                        'Collector Number': card['collector_number']
                    })
            else:
                has_more = False

df_scry = pd.DataFrame(cards_data)
df_scry = df_scry.sort_values(by=['Name','Edition', 'Collector Number'])

def assign_letters(group):
    group['Letter'] = [ascii_uppercase[i] for i in range(len(group))]
    return group

df_land_letter = df_scry.groupby(['Name','Edition'], as_index=True).apply(assign_letters, include_groups=False)
df_land_letter = df_land_letter.reset_index(drop=False)

df_land_letter['Collector Number'] = df_land_letter['Collector Number'].astype(str)

df = pd.merge(df, df_land_letter, on=['Name','Edition', 'Collector Number'], how='left')

df.loc[pd.notna(df['Letter']), 'Collector Number'] = df['Collector Number'].astype(str) + ' ' + df['Letter'].fillna('')
df = df.drop(columns=['Letter'])

# Change collector number format.
editions_with_three_digit_collector_number = ['afr', 'bro', 'brr', 'dmu', 'eld', 'j22', 'm19', 'm20', 'm21', 'neo', 'one', 'slx', 'snc', 'vow', 'war']

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

# Append 'token' to token card names and trim 't' from token card edition 
token_str = ' Token '
df['Name'] = df.apply(lambda x: x['Name'] + token_str + x['Collector Number'] if (len(x['Edition']) == 4 and x['Edition'].startswith('t')) else x['Name'], axis=1)
df['Edition'] = df['Edition'].apply(lambda x: x[1:] if (len(x) == 4 and x.startswith('t')) else x)

# Append collector number to land and bonus sheet card names
df.loc[df['Name'].isin(basic_land),'Name'] = df['Name'] + ' ' + df['Collector Number'].astype(str)

df.loc[df['Edition'].isin(['wot']),'Name'] = df['Name'] + ' ' + df['Collector Number'].astype(str)

df.loc[df['Edition'].isin(['otp']),'Name'] = df['Name'] + ' ' + df['Collector Number'].astype(str).str.slice(0, 5) + ' - Showcase)'


# Trim names for split and double-faced cards
df['Name'] = df['Name'].str.split("//").str[0]

df.rename(columns={'Name': 'Title', 'Count': 'Qty'}, inplace=True)

cardkingdom_column_subset = ['Title','Edition','Foil','Qty']

df = df[cardkingdom_column_subset]

df.to_csv('/home/andy/Downloads/cardkingdom.csv', index=False)
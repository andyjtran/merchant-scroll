import pandas as pd

df = pd.read_csv('/home/andy/Downloads/moxfield_haves.csv')

# Remove Art cards, Jumpstart theme cards, and 30th Anniversary Play Promo cards
df = df[~((df['Edition'].str.len() == 4) & (df['Edition'].str.startswith('a') | df['Edition'].str.startswith('f') | df['Edition'].str.contains('p30a')))]

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
is_land = df['Name'].isin(['Plains','Island','Swamp','Mountain','Forest'])
df.loc[is_land, 'Name'] = df['Name'] + ' ' + df['Collector Number'].astype(str)

df.loc[df['Edition'].isin(['wot']),'Name'] = df['Name'] + ' ' + df['Collector Number'].astype(str)

df.loc[df['Edition'].isin(['otp']),'Name'] = df['Name'] + ' ' + df['Collector Number'].astype(str).str.slice(0, 5) + ' - Showcase)'

# Trim names for split and double-faced cards
df['Name'] = df['Name'].str.split("//").str[0]

df.rename(columns={'Name': 'Title', 'Count': 'Qty'}, inplace=True)

cardkingdom_column_subset = ['Title','Edition','Foil','Qty']

df = df[cardkingdom_column_subset]

df.to_csv('/home/andy/Downloads/cardkingdom.csv', index=False)
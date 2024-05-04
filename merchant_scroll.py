import pandas as pd

df = pd.read_csv('/home/andy/Downloads/moxfield_haves.csv')

df.rename(columns={'Name': 'Title', 'Count': 'Qty'}, inplace=True)

cardkingdom_column_subset = ['Title','Edition','Foil','Qty']

df = df[cardkingdom_column_subset]

df.to_csv('/home/andy/Downloads/cardkingdom.csv', index=False)
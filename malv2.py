#!/usr/bin/env python

import pandas as pd
from bs4 import BeautifulSoup
import re
import requests
import time
import json
import matplotlib.pyplot as plt
from adjustText import adjust_text

from concurrent.futures import as_completed, ThreadPoolExecutor
MAX_THREADS = 20

USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.130 Safari/537.36'

def get_genres(data):
    url = data['url']
    r = session.get(url)
    soup = BeautifulSoup(r.content, 'lxml', from_encoding="utf-8")
    genre_tags = soup.find('span', string='Genres:').find_all_next('a', href=re.compile('genre'))
    genres = [tag.text for tag in genre_tags]
    data['genres'] = genres

url = input("Enter the url: ")
username = url.split('/')[-1]
type_list = url.split('/')[-2]

domain = 'https://myanimelist.net'

session = requests.Session()
session.headers['User-Agent'] = USER_AGENT
response = session.get(url)

soup = BeautifulSoup(response.text, 'lxml')

data = soup.find('table')['data-items'].strip('[]')
data_list = re.split(r'(?<=}),', data)
data_list = list(map(json.loads, data_list))

if type_list=='animelist':
    for data in data_list:
        data['url'] = data.pop('anime_url')
        data['title'] = data.pop('anime_title')
else:
    for data in data_list:
        data['url'] = data.pop('manga_url')
        data['title'] = data.pop('manga_title')

for data in data_list:
    data['url'] = domain + data['url']


print("Extraction started")
start_time = time.time()
with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
    futures = (
            executor.submit(get_genres, data) for data in data_list
    )
    for future in as_completed(futures):
        future.result()

print("Entire request took", time.time()-start_time, "seconds")

table = {
    'Title':[],
    'Score':[],
    'Genres':[]
}

for data in data_list:
    table['Title'].append(data['title'])
    table['Score'].append(data['score'])
    table['Genres'].append(data['genres'])

df = pd.DataFrame(table)
df.to_excel('{0}-{1}-Data.xlsx'.format(username, type_list), index=False)
print("Excel file has been created")

#Data Analysis

# remove unrated mangas/animes
df = df[df['Score'] != 0]

# reset the index and remove the previous index
df = df.reset_index().drop('index', axis=1)

#convert scores from str to int
df['Score'] = df['Score'].astype(int)

#split the list of genres to create a dataframe
genre_df = pd.DataFrame(df['Genres'].values.tolist())

#merge the genre dataframe with the original dataframe
df1 = df.merge(genre_df, right_index = True, left_index = True).drop('Genres', axis=1)

# Unpivot a DataFrame from wide to long format and drop the None genres
df1 = df1.melt(id_vars = ['Title', 'Score'], value_name = "Genre").dropna().drop('variable', axis=1)

# create a Boolean series containing genres more than 1
s = df1['Genre'].value_counts() != 1

# store the names of the genres in a list
genlist = (s.loc[lambda x: x==True].index).tolist()

#create a new DataFrame of genres if it is present in other list
df2 = df1[df1['Genre'].isin(genlist)]

#store the value counts of genres
a = df2['Genre'].value_counts()

#return the correlation between genres and their scores
s_corr = df2.Genre.str.get_dummies().corrwith(df2.Score)

# combine the value counts and correlations into a new dataframe
df3 = pd.concat([a, s_corr], axis=1).rename(columns={0:'Correlation', 'Genre': 'Counts'})

#store the index of dataframe in a list
text = df3.index.tolist()

#create a plot showing the relation between the counts of genres and ratings coefficient
fig = plt.figure(figsize=(15,9))
ax = fig.add_subplot(1, 1, 1)
textl = []
for i, txt in enumerate(text):
    x, y = df3['Counts'][i], df3['Correlation'][i]
    plt.scatter(x, y, marker='x', color='red')
    textl.append(plt.text(x, y, txt, fontsize=10))
adjust_text(textl)
ax.spines['left'].set_position('center')
ax.spines['bottom'].set_position('zero')

plt.show()

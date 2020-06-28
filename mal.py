# coding: utf-8
#!/usr/bin/env python

from selenium import webdriver
import pandas as pd
from bs4 import BeautifulSoup
import re
import requests
import time
import matplotlib.pyplot as plt
from adjustText import adjust_text

from concurrent.futures import as_completed, ThreadPoolExecutor
MAX_THREADS = 20

def get_genres(url):
    r = requests.get(url)
    soup = BeautifulSoup(r.content, 'html5lib')
    genre_tags = soup.find('span', string='Genres:').find_all_next('a', href=re.compile('genre'))
    genres = [tag.text for tag in genre_tags]
    return genres

def info_async(i):
    data = []
    tag = titles[i].find('a')
    url = domain + tag['href']
    data.append(tag.text)
#     data.append(url)
    data.append(scores[i].text.strip())
    data.append(get_genres(url))
    return data

CHROMEDRIVER_PATH = "C:\Program Files (x86)\Google\Chrome\chromedriver.exe"

options = webdriver.ChromeOptions()
options.add_argument("headless")
options.add_argument("--mute-audio")

driver = webdriver.Chrome(executable_path=CHROMEDRIVER_PATH,
                          options=options)

url = input("Enter the url: ")
username = url.split('/')[-1]
type_list = url.split('/')[-2]

domain = 'https://myanimelist.net'

print("Page request started")
start_time = time.time()
driver.get(url)
print("Page request took", time.time()-start_time, "seconds")

soup = BeautifulSoup(driver.page_source, 'html5lib')

driver.quit()

title_classes = ["data title", "data title clearfix"]
title = title_classes[0] if type_list == 'mangalist' else title_classes[1]

titles = soup.find_all('td', class_=title)
scores = soup.find_all('td', class_="data score")

database = {
            "Title":[],
            "Score":[],
            "Genres":[]
}

print("Extraction started")
start_time = time.time()
with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
    futures = (
            executor.submit(info_async, i) for i in range(len(titles))
        )
    for future in as_completed(futures):
        data = future.result()
        database['Title'].append(data[0])
#         database['Link'].append(data[1])
        database['Score'].append(data[1])
        database['Genres'].append(data[2])
        
print("Entire request took", time.time()-start_time, "seconds")

df = pd.DataFrame(database)
df.to_excel('{0}-{1}-Data.xlsx'.format(username, type_list), index=False)
print("Excel file has been created")

#Data Analysis

# remove unrated mangas/animes
df = df[df['Score'] != '-']

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

import pandas as pd
import sys
import os

directory = '.'
if len(sys.argv) > 1:
    directory = sys.argv[1]
    
file = os.path.join(directory,'topics.csv')    

to_dir = '.'
if len(sys.argv) > 2:
    to_dir = sys.argv[2]
    
#to_dir =  os.path.join(os.getcwd(), to_dir)

to_file = os.path.join(to_dir, 'topic_ids_and_titles.py')
    

# Lees het CSV-bestand in een DataFrame
df_topics = pd.read_csv(file, delimiter=';')
topic_data = []
seen_titles = set()
for index, row in df_topics.iterrows():
    title = row['title']
    if title not in seen_titles:
        topic_data.append({'topic': row['topic'], 'title': title})  # projectID eerst
        seen_titles.add(title)

# Schrijf de lijst met dictionaries naar een nieuw Python-bestand

with open(to_file, 'w', encoding='utf-8') as f: 
    f.write('topic_ids_and_titles = [\n')  
    for topic in topic_data:
        f.write(f'    {topic},\n')
    f.write(']\n')

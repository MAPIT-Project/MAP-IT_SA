#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Nov 14 08:55:10 2024

@author: marco
"""

import os
import requests
import pandas as pd
import logging
from pathlib import Path
import sys
from time import sleep

def download_and_rename_pdfs(csv_file):
   
    df = pd.read_csv(csv_file, delimiter=';')
    downloaded_files = []
    not_downloaded_files = []

    for index, row in df.iterrows():
        url = row['physUrl']
        project_id = row['projectID']
        field_id = row['id']
        
        if url.startswith('https://ec.europa.eu/'):
            try:
                response = requests.get(url)
                response.raise_for_status()

                # Maak de map als deze nog niet bestaat
                os.makedirs('pdfs', exist_ok=True)

                filename = f"pdfs/cordis_{project_id}_{field_id}.pdf"
                
                if response.content.decode().find("window.location='")>-1:
                
                    start_idx = response.content.decode().index(
                        "window.location='") + 17
                    end_idx = response.content.decode().index("';", start_idx)
                    
                    print(f"{start_idx}- {end_idx}")
                    url = response.content[start_idx:end_idx].decode()
                    response = requests.get(url, cookies=response.cookies)
                    response.raise_for_status()
                    
                    if response.content[:5] == b'%PDF-': #magic pdf number 
                        
                        with open(filename, 'wb') as f:
                            f.write(response.content)
                            downloaded_files.append(filename)
                            logging.info(f"Downloaded {filename}")
                            print(filename)
                    else:
                        logging.info(f"Skipped {url} not PDF: {response.content[:5]}")
                        not_downloaded_files.append(url)
            except requests.exceptions.RequestException as e:
                logging.info(f"Error downloading {url}: {e}")
                not_downloaded_files.append(url)
        else:
            logging.info(f"Skipped {url} not ")
            not_downloaded_files.append(url)
        sleep(1) #too many sequential requests are ignored
    return downloaded_files, not_downloaded_files


if __name__ == "__main__":
    #initiate logging as quickly as possible!
    Path('./log/').mkdir(exist_ok=True)
    logger = logging.getLogger(__name__)
    logging.basicConfig(filename='log/MAPIT.log', filemode="a", encoding='utf-8', 
                        level=logging.INFO, format='%(asctime)s %(message)s')
    
    directory = '.'
    if len(sys.argv) > 1:
        directory = sys.argv[1]
    file = os.path.join(directory, 'webLink.csv')
    logging.info(f"Using {directory} as directory for PDF download.")
    
    # Aanroepen van de functie
    downloaded_files, not_downloaded_files = download_and_rename_pdfs(file)
    
    # Print de bestandsnamen die gedownload zijn
    print("\nDownloaded files:")
    for file in downloaded_files:
        print(file)
    
    # Print de bestandsnamen die niet gedownload zijn
    print("\nNot downloaded files:")
    for file in not_downloaded_files:
        print(file)
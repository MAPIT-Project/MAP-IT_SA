#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Sep 26 16:54:51 2024

@author: marco
"""

import os
import sys
from pathlib import Path
from CORDISProjectReader import ProjectLoader
import logging

##Buidls the graph from nothing,
#needed for installation or after a desaster
class Grapher:
    ##entry point for building the graph
    # @param directory where the CORDIS and OPENAIR exports are located.
    def buildGraph(self, directory):
        file = os.path.join(directory, "project.csv")
        if Path(file).is_file():
            loader = ProjectLoader(file)
            client, client_stub = loader.connectToGraph()
            if not loader.load_projects(client):
                logging.info("Projects not loaded: no database or file is empty.")
        else:
            logging.info(f"Projects not loaded: file {file} not found")
            
if __name__ == "__main__":
    #initiate logging as quickly as possible!
    Path('./log/').mkdir(exist_ok=True)
    logger = logging.getLogger(__name__)
    logging.basicConfig(filename='log/MAPIT.log', filemode="a", encoding='utf-8', level=logging.INFO)
    grapher = Grapher()
    #arg 1 is the directory otherwise the current dir
    dir = '.'
    if len(sys.argv) > 1:
        dir = sys.argv[1]
        
    logging.info(f"Using {dir} as directory for fileimport.")
        
    sys.exit(grapher.buildGraph(dir))
                

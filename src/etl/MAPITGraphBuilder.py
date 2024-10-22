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
from pydgraph import json 

##Builds the graph from nothing,
#needed for installation or after a desaster 
class Grapher:
    ##entry point for building the graph
    # @param directory where the CORDIS and OPENAIR exports are located.
    def buildGraph(self, directory):
        logging.info("Starting import....")
        file = os.path.join(directory, "project.csv")
        if Path(file).is_file():
            loader = ProjectLoader(file)
            client, client_stub = loader.connectToGraph()
            result, projects = loader.load_projects(client)
            if not result:
                logging.info("Projects not loaded: no database or file is empty.")
            else:
                self.add_or_update_topic_relation(projects, client)
                
        else:
            logging.info(f"Projects not loaded: file {file} not found")
        
        client_stub.close()            

    ##
    #Add or update the relation between projects that have similar keywords
    #this edge is defined as n_shared_keywords/max(number_of_all_keywords)
    def add_or_update_keyword_relation(self, projects, client):
        #TODO
        #list thu projects
        #download the project xml
        #search other projects with similar keywords
        #add relation and facet
        
        
        
        
        return

    
    ##
    #Add or update the relation between projects that have a similar topic
    #this edge is defined as equal, the name implies more topics but the 
    #dataset shows one.
    def add_or_update_topic_relation(self, projects, client):
        for _, row in projects.iterrows():
            # Create a dictionary for each row
            project_data = {col: row[col] for col in projects.columns}
            horizon_topics = project_data['topics']
        
            #find related projects
            query = f"""{{
                var(func: has(topics)) {{
                    tp as topics
                }}
                q(func: eq(val(tp), {horizon_topics}))
                  {{ uid }}
                 }}
             """
            
            res = client.txn(read_only=True).query(query)
            horizon_topics = json.loads(res.json).get('q')
            
            #retrieve the current project in the database
            projectq=f"""
            {{
            temp_uid as var(func: eq(id, {project_data['id']} ))
            }}
            """
            
            set_nquads = ""
            if (len(horizon_topics)):
                #mutate it with the relations
                
                for horizon_topic in horizon_topics:
                    #every one except itself
                    if horizon_topic['uid'] != project_data['id']:                    
                        set_nquads += f"""
                            uid(temp_uid) <topic_projects> <{horizon_topic['uid']}> .
                        """
                            
                txn = client.txn()
                mutation = txn.create_mutation(set_nquads=set_nquads)
                request = txn.create_request(query=projectq, mutations=[mutation], commit_now=True)
                txn.do_request(request)


if __name__ == "__main__":
    #initiate logging as quickly as possible!
    Path('./log/').mkdir(exist_ok=True)
    logger = logging.getLogger(__name__)
    logging.basicConfig(filename='log/MAPIT.log', filemode="a", encoding='utf-8', 
                        level=logging.INFO, format='%(asctime)s %(message)s')
    grapher = Grapher()
    #arg 1 is the directory otherwise the current dir
    dir = '.'
    if len(sys.argv) > 1:
        dir = sys.argv[1]
        
    logging.info(f"Using {dir} as directory for fileimport.")
        
    sys.exit(grapher.buildGraph(dir))
                

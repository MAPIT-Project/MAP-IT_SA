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
#needed for installation or after a disaster 
class Grapher:
    ##entry point for building the graph
    # @param directory where the CORDIS and OPENAIR exports are located.
    def buildGraph(self, directory):
        logging.info("Starting import from directory: %s", directory)
        
        if not os.path.isdir(directory):
            logging.error("Import failed: %s is not a valid directory", directory)
            return
            
        file = os.path.join(directory, "project.csv")
        client = None
        client_stub = None
        
        if Path(file).is_file():
            logging.info("Found project.csv file, initializing loader...")
            loader = ProjectLoader(file)
            client, client_stub = loader.connectToGraph()
            logging.info("Connected to graph database successfully")
            result, projects = loader.load_projects(client)
            if not result:
                logging.warning("Projects not loaded: no database or file is empty.")
            else:
                logging.info("Successfully loaded %d projects, updating topic relations...", len(projects))
                self.add_or_update_topic_relation(projects, client)
        else:
            logging.error("Projects not loaded: file %s not found", file)
        
        if client_stub:
            client_stub.close()
            logging.info("Database connection closed")
            client_stub.close()            
    ##
    #Add or update the relation between projects that have similar keywords
    #this edge is defined as n_shared_keywords/max(number_of_all_keywords)
    def add_or_update_keyword_relation(self, projects, client):
        logging.info("Starting keyword relation update for %d projects", len(projects))
        #TODO
        #list thu projects
        #download the project xml
        #search other projects with similar keywords
        #add relation and facet
        logging.warning("Keyword relation update not implemented yet")
        return
    def add_or_update_topic_relation(self, projects, client):
        logging.info("Starting topic relation update for %d projects", len(projects))
        processed_count = 0
        updated_count = 0
        
        for _, row in projects.iterrows():
            processed_count += 1
            # Create a dictionary for each row
            project_data = {col: row[col] for col in projects.columns}
            horizon_topics = project_data['topics']
            
            logging.debug("Processing project %s with topic %s", project_data['id'], horizon_topics)
        
            #find related projects
            query = f"""{{
                var(func: has(topics)) {{
                    tp as topics
                }}
                q(func: eq(val(tp), {horizon_topics}))
                  {{ uid }}
                 }}
             """
            
            try:
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
                    relation_count = 0
                    for horizon_topic in horizon_topics:
                        #every one except itself
                        if horizon_topic['uid'] != project_data['id']:                    
                            set_nquads += f"""
                                uid(temp_uid) <topic_projects> <{horizon_topic['uid']}> .
                            """
                            relation_count += 1
                                
                    if relation_count > 0:
                        txn = client.txn()
                        mutation = txn.create_mutation(set_nquads=set_nquads)
                        request = txn.create_request(query=projectq, mutations=[mutation], commit_now=True)
                        txn.do_request(request)
                        updated_count += 1
                        logging.debug("Added %d topic relations for project %s", relation_count, project_data['id'])
                
            except Exception as e:
                logging.error("Error processing project %s: %s", project_data['id'], str(e))
            
            if processed_count % 100 == 0:
                logging.info("Processed %d projects, updated %d with topic relations", processed_count, updated_count)
        
        logging.info("Completed topic relation update. Total processed: %d, Total updated: %d", processed_count, updated_count)
        txn = client.txn()
        mutation = txn.create_mutation(set_nquads=set_nquads)
        request = txn.create_request(query=projectq, mutations=[mutation], commit_now=True)
        txn.do_request(request)


if __name__ == "__main__":
    #initiate logging as quickly as possible!
    Path('./log/').mkdir(exist_ok=True)
    logger = logging.getLogger(__name__)
    
    
    # Configure file handler
    logging.basicConfig(filename='log/MAPIT.log', filemode="a", encoding='utf-8', 
                        level=logging.INFO, format='%(asctime)s %(message)s')
    grapher = Grapher()
    #arg 1 is the directory otherwise the current dir
    directory = '.'
    if len(sys.argv) > 1:
        directory = sys.argv[1]
        
    logging.info(f"Using {directory} as directory for fileimport.")
        
    sys.exit(grapher.buildGraph(directory))
                

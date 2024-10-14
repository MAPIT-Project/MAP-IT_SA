## @CORDISProjectReader
#

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Sep 19 14:38:12 2024
Purpose is to load the project.csv file. 

@author: marco
"""

import logging
import pandas as pd
from pydgraph import DgraphClientStub, DgraphClient, json, Mutation 
import os

class CORDISProject:
    def __init__(self, id, acronym, status, title, startDate, endDate, totalCost, ecMaxContribution, legalBasis, topics, ecSignatureDate, frameworkProgramme, masterCall, subCall, fundingScheme, nature, objective, contentUpdateDate,   
 rcn, grantDoi):
        self.id = id
        self.acronym = acronym
        self.status = status
        self.title = title
        self.startDate = startDate
        self.endDate = endDate
        self.totalCost = totalCost
        self.ecMaxContribution = ecMaxContribution
        self.legalBasis = legalBasis
        self.topics = topics
        self.ecSignatureDate = ecSignatureDate
        self.frameworkProgramme = frameworkProgramme
        self.masterCall = masterCall
        self.subCall = subCall
        self.fundingScheme = fundingScheme
        self.nature = nature
        self.objective = objective
        self.contentUpdateDate = contentUpdateDate
        self.rcn = rcn
        self.grantDoi = grantDoi


class ProjectLoader:
    ##Loads a the projects in a CORDIS project file format into a Dataframe
    #
    
    
    ##Constructor
    # @param filename of the CORDIS project file
    # @param delimiter of the CORDIS project file (default is ;)
    #
    def __init__(self, filename, delimiter=';'):
        self.filename = filename
        self.delimiter = delimiter

    def load_projects(self) -> bool:
        ## reads file in dataframe
        df = None
        try:
            df = pd.read_csv(self.filename, delimiter=self.delimiter)
        except:
           logging.exception('')

        # Create a Dgraph client stub
        client, client_stub = self.connectToGraph()
        
        #assert {I}-premisse before commencing
        if not (client or client_stub or df) and len(df):
            return False
        
        #The central node in the ontology is a CORDIS project.
        #Therefore, loading starts this the projects in CORDIS.
        #Every other piece of information is added to the project

        # Convert date columns to datetime
        date_columns = ['startDate', 'endDate', 'contentUpdateDate']
        for col in date_columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')

        # Iterate through each row and create Project instances
        for _, row in df.iterrows():
            # Create a dictionary for each row
            project_data = {col: row[col] for col in df.columns}

            # Ensure datatypes match those defined in the Project class
            project_data['id'] = int(project_data['id'])
            project_data['totalCost'] = float(project_data['totalCost'])
            if not pd.isna(project_data['ecMaxContribution']):
                project_data['ecMaxContribution'] = float(project_data['ecMaxContribution'])

            # Create a Project instance and append to the graph
            project = CORDISProject(**project_data)
            
            self.add_or_update_projects(project, client)

        return True
    
    ##
    # Load the projectdata into the graph,
    #
    
    def add_or_update_projects(self, project, client):

        # Query to check if the project already exists
        query = """
        query q0($id: string) {
            existing_project(func: eq(id, $id)) {
                uid
            }
        }
        """
        variables = {'$id': str(project.id)}
        res = client.txn(read_only=True).query(query, variables=variables)
        existing_project = json.loads(res.json).get('existing_project')
    
        if existing_project:
            # Project already exists, update the node
            mutation = Mutation(
                set_nquads=f"""
                uid({existing_project[0]['uid']}) <id> "{project.id}" .
                uid({existing_project[0]['uid']}) <acronym> "{project.acronym}" .
                uid({existing_project[0]['uid']}) <status> "{project.status}" .
                uid({existing_project[0]['uid']}) <title> "{project.title}" .
                uid({existing_project[0]['uid']}) <startDate> "{project.startDate.strftime('%Y-%m-%d') if project.startDate else ''}" .
                uid({existing_project[0]['uid']}) <endDate> "{project.endDate.strftime('%Y-%m-%d') if project.endDate else ''}" .
                uid({existing_project[0]['uid']}) <totalCost> "{project.totalCost}" .
                uid({existing_project[0]['uid']}) <ecMaxContribution> "{project.ecMaxContribution}" .
                uid({existing_project[0]['uid']}) <legalBasis> "{project.legalBasis}" .
                uid({existing_project[0]['uid']}) <topics> "{project.topics}" .
                uid({existing_project[0]['uid']}) <ecSignatureDate> "{project.ecSignatureDate.strftime('%Y-%m-%d') if project.ecSignatureDate else ''}" .
                uid({existing_project[0]['uid']}) <frameworkProgramme> "{project.frameworkProgramme}" .
                uid({existing_project[0]['uid']}) <masterCall> "{project.masterCall}" .
                uid({existing_project[0]['uid']}) <subCall> "{project.subCall}" .
                uid({existing_project[0]['uid']}) <fundingScheme> "{project.fundingScheme}" .
                uid({existing_project[0]['uid']}) <nature> "{project.nature}" .
                uid({existing_project[0]['uid']}) <objective> "{project.objective}" .
                uid({existing_project[0]['uid']}) <contentUpdateDate> "{project.contentUpdateDate.strftime('%Y-%m-%d %H:%M:%S') if project.contentUpdateDate else ''}" .
                uid({existing_project[0]['uid']}) <rcn> "{project.rcn}" .
                uid({existing_project[0]['uid']}) <grantDoi> "{project.grantDoi}" .
                """
            )
            txn = client.txn()
            txn.mutate(mutation)
            txn.commit()
        else:
            # Project doesn't exist, create a new node
            mutation = Mutation(
                set_nquads=f"""
                _:newProject <id> "{project.id}" .
                _:newProject <acronym> "{project.acronym}" .
                _:newProject <status> "{project.status}" .
                _:newProject <title> "{project.title}" .
                _:newProject <startDate> "{project.startDate.strftime('%Y-%m-%d') if project.startDate else ''}" .
                _:newProject <endDate> "{project.endDate.strftime('%Y-%m-%d') if project.endDate else ''}" .
                _:newProject <totalCost> "{project.totalCost}" .
                _:newProject <ecMaxContribution> "{project.ecMaxContribution}" .
                _:newProject <legalBasis> "{project.legalBasis}" .
                _:newProject <topics> "{project.topics}" .
                _:newProject <ecSignatureDate> "{project.ecSignatureDate.strftime('%Y-%m-%d') if project.ecSignatureDate else ''}" .
                _:newProject <frameworkProgramme> "{project.frameworkProgramme}" .
                _:newProject <masterCall> "{project.masterCall}" .
                _:newProject <subCall> "{project.subCall}" .
                _:newProject <fundingScheme> "{project.fundingScheme}" .
                _:newProject <nature> "{project.nature}" .
                _:newProject <objective> "{project.objective}" .
                _:newProject <contentUpdateDate> "{project.contentUpdateDate.strftime('%Y-%m-%d %H:%M:%S') if project.contentUpdateDate else ''}" .
                _:newProject <rcn> "{project.rcn}" .
                _:newProject <grantDoi> "{project.grantDoi}" .
                """
            )
            txn = client.txn()
            txn.mutate(mutation)
            txn.commit()

        print("Projects have been added or updated in the database.")     
       
        ## Method that creates the connection to the graph
        # 
        #
        def connectToGraph(self):
                
            # Create a Dgraph client stub
            client_stub = DgraphClientStub(os.environ('DGRAPH_URL'))  # Replace with your Dgraph configuration
    
            # Create a Dgraph client
            client = DgraphClient(client_stub)
            return client, client_stub
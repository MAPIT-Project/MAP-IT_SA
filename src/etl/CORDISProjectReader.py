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
import locale
import json

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
        self.dtypes = {"id":str,"acronym":str,"status":str,"title":str,"totalCost":str,
                  "ecMaxContribution":str,"legalBasis":str,"topics":str,"frameworkProgramme":str,
                  "masterCall":str,"subCall":str,"fundingScheme":str,"nature":str,"objective":str,
                  "rcn":str,"grantDoi":str, "startDate":str,"endDate":str,"contentUpdateDate":str, 
                  "ecSignatureDate":str}
        #filter for currencies

    def load_projects(self, client) -> bool:
        ## reads file in dataframe
        # encoding is needed for imperial numberformats and dates
        #
        df = None
        
        
        try:
            df = pd.read_csv(self.filename, delimiter=self.delimiter, dtype=self.dtypes)
        except:
           logging.exception('Exception while loading data')
           return False, df

        #The central node in the ontology is a CORDIS project.
        #Therefore, loading starts this the projects in CORDIS.
        #Every other piece of information is added to the project

        
        # Convert date columns to datetime
        
        date_columns = ['startDate', 'endDate', 'contentUpdateDate', 'ecSignatureDate']
        for col in date_columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')

        # Iterate through each row and create Project instances
        for _, row in df.iterrows():
            # Create a dictionary for each row
            project_data = {col: row[col] for col in df.columns}

            # Ensure datatypes match those defined in the Project class
            project_data['id'] = int(project_data['id'])
            project_data['title'] = json.dumps(project_data['title']).encode("ascii").decode('utf-8')[1:-1]
            project_data['objective'] = json.dumps(project_data['objective']).encode("ascii").decode('utf-8')[1:-1]
            project_data['totalCost'] = project_data['totalCost']
            if not pd.isna(project_data['ecMaxContribution']):
                project_data['ecMaxContribution'] = project_data['ecMaxContribution']

            # Create a Project instance and append to the graph
            project = CORDISProject(**project_data)
            
            self.add_or_update_projects(project, client)

        return True, df
    
    ##
    # Load the projectdata into the graph,
    #
    
    def add_or_update_projects(self, project, client):
        
        query=f"""
        {{
        temp_uid as var(func: eq(id, {project.id} ))
        }}
        """
                
        # Project already exists, update the node
        set_nquads=f"""
        uid(temp_uid) <id> "{project.id}" .
        uid(temp_uid) <acronym> "{project.acronym}" .
        uid(temp_uid) <status> "{project.status}" .
        uid(temp_uid) <title> "{project.title}" .
        uid(temp_uid) <startDate> "{project.startDate.strftime('%Y-%m-%d') if project.startDate else ''}" .
        uid(temp_uid) <endDate> "{project.endDate.strftime('%Y-%m-%d') if project.endDate else ''}" .
        uid(temp_uid) <totalCost> "{project.totalCost}" .
        uid(temp_uid) <ecMaxContribution> "{project.ecMaxContribution}" .
        uid(temp_uid) <legalBasis> "{project.legalBasis}" .
        uid(temp_uid) <topics> "{project.topics}" .
        uid(temp_uid) <ecSignatureDate> "{project.ecSignatureDate.strftime('%Y-%m-%d') if project.ecSignatureDate else ''}" .
        uid(temp_uid) <frameworkProgramme> "{project.frameworkProgramme}" .
        uid(temp_uid) <masterCall> "{project.masterCall}" .
        uid(temp_uid) <subCall> "{project.subCall}" .
        uid(temp_uid) <fundingScheme> "{project.fundingScheme}" .
        uid(temp_uid) <nature> "{project.nature}" .
        uid(temp_uid) <objective> "{project.objective}" .
        uid(temp_uid) <contentUpdateDate> "{project.contentUpdateDate.strftime('%Y-%m-%dT%H:%M:%S') if project.contentUpdateDate else ''}" .
        uid(temp_uid) <rcn> "{project.rcn}" .
        uid(temp_uid) <grantDoi> "{project.grantDoi}" .
        """
        
        print (set_nquads)        
        
        cond = "@if(eq(len(temp_uid), 1))"
        
        #mutation = Mutation(set_nquads=set_nquads)
#        txn = client.txn()
#        txn.mutate(set_nquads=set_nquads)
#        txn.commit()

        #if there is no existing project than temp_uid is filled with the uid.
        #than this update is iqnored
        txn = client.txn()
        mutation = txn.create_mutation(cond=cond, set_nquads=set_nquads)
        request = txn.create_request(query=query, mutations=[mutation], commit_now=True)
        txn.do_request(request)
        

        query = """
        query q($id: string) {
            existing_project(func: eq(id, $id)) {
                uid
            }
        }
        """

        variables = {'$id': str(project.id)}
        res = client.txn(read_only=True).query(query, variables=variables)
        existing_project = json.loads(res.json).get('existing_project')
    
        if not existing_project:

            # Project doesn't exist, create a new node
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
            _:newProject <contentUpdateDate> "{project.contentUpdateDate.strftime('%Y-%m-%dT%H:%M:%S') if project.contentUpdateDate else ''}" .
            _:newProject <rcn> "{project.rcn}" .
            _:newProject <grantDoi> "{project.grantDoi}" .
            """.encode('utf-8')
            print(set_nquads) 
            mutation = Mutation(set_nquads = set_nquads)
            txn = client.txn()
            txn.mutate(mutation)
            txn.commit()

        print("Projects have been added or updated in the database.")     
       
    ## Method that creates the connection to the graph
    # 
    #
    def connectToGraph(self):
        
        dgraph_url = "localhost:9080"
        if 'DGRAPH_URL' in os.environ:
            dgraph_url = os.environ['DGRAPH_URL']
             
        logging.info(f"Using {dgraph_url} as DGRAPH_URL environment variable, specify if needed!")
            
        # Create a Dgraph client stub
        client_stub = DgraphClientStub(dgraph_url)  # Replace with your Dgraph configuration

        # Create a Dgraph client
        client = DgraphClient(client_stub)
        return client, client_stub
    
    ## method to convert currencies
    #
    def currencyConverter(self, amount) -> float:
        if len(amount.split("."))==2 and amount.rfind(",")>0:
            #number with a dotted separator and commated decimals
            locale.setlocale(locale.LC_ALL, 'en_US.utf8')
            amount = locale.atof(amount)
            return float(amount)
        if len(amount.split(","))==2 and amount.rfind(".")>0:
            #number with commated separators and dotted decimals
            locale.setlocale(locale.LC_ALL, 'nl_NL.utf8')
            amount = locale.atof(amount)
            return float(amount)
        if len(amount.split(","))==2 and amount.rfind(".") == -1:
            #number with comma decimal
            locale.setlocale(locale.LC_ALL, 'nl_NL.utf8')
            amount = locale.atof(amount)
            return float(amount)
            
        #number with dot decimal (no action needed)
            
        return float(amount)
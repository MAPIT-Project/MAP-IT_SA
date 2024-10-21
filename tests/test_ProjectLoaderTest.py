import os
import sys

import unittest
from datetime import datetime
from src.etl.CORDISProjectReader import ProjectLoader
from pydgraph import DgraphClientStub, DgraphClient
from unittest.mock import Mock
import numpy as np


# ... (Project and ProjectLoader classes remain the same)

## Testing the projectloader


class TestProjectLoader(unittest.TestCase):
    def test_load_projects(self):
        TESTDATA_FILENAME = os.path.join(os.path.dirname(__file__), 'project.csv')
        print(TESTDATA_FILENAME)

        loader = ProjectLoader(TESTDATA_FILENAME)
        #do not touch database
        loader.add_or_update_projects = Mock(name="method")
        
        client, client_stub = loader.connectToGraph()
        
        databaseClient = DgraphClient(DgraphClientStub())
        
        result, projects = loader.load_projects(databaseClient)
        projects = projects.to_records()
        
        # Check if projects list is not empty
        self.assertNotEqual(len(projects), 0, "Projects list should not be empty")
        self.assertEqual(result, True)

        # Check if the first project has the correct values
        
        first_project = projects[0]
        self.assertEqual(first_project.id, '101131292')
        self.assertEqual(first_project.acronym, 'AIAS')
        self.assertEqual(first_project.status, 'SIGNED')
        self.assertEqual(first_project.startDate, np.datetime64('2024-01-01T00:00:00.000000000'))
        self.assertEqual(first_project.totalCost, '0')
        self.assertEqual(first_project.ecMaxContribution, '1564000')
        
        
    def test_CurrencyConverter(self):

        loader = ProjectLoader(".")
        self.assertEqual(loader.currencyConverter("101131292"), 101131292)
        self.assertEqual(loader.currencyConverter("101131292.00"), float(101131292.00))
        self.assertEqual(loader.currencyConverter("101131292,00"), 101131292.00)
        self.assertEqual(loader.currencyConverter("101.131.292,00"), 101131292.00)
        self.assertEqual(loader.currencyConverter("101,131,292.00"), 101131292.00)
        
        

if __name__ == '__main__':
    #adding the project path.
   
    unittest.main()
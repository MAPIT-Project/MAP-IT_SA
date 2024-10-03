import os
import sys

import unittest
from datetime import datetime
from src.data.CORDISProjectReader import ProjectLoader

# ... (Project and ProjectLoader classes remain the same)

## Testing the projectloader


class TestProjectLoader(unittest.TestCase):
    def test_load_projects(self):
        TESTDATA_FILENAME = os.path.join(os.path.dirname(__file__), 'project.csv')
        print(TESTDATA_FILENAME)

        loader = ProjectLoader(TESTDATA_FILENAME)
        projects = loader.load_projects()

        # Check if projects list is not empty
        self.assertNotEqual(len(projects), 0, "Projects list should not be empty")

        # Check if the first project has the correct values
        first_project = projects[0]
        self.assertEqual(first_project.id, 101131292)
        self.assertEqual(first_project.acronym, 'AIAS')
        self.assertEqual(first_project.status, 'SIGNED')
        self.assertEqual(first_project.startDate, datetime(2024, 1, 1))
        self.assertEqual(first_project.totalCost, 0)
        self.assertEqual(first_project.ecMaxContribution, 1564000)

if __name__ == '__main__':
    #adding the project path.
   
    unittest.main()
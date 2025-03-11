#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Mar 11 11:14:10 2025

@author: marco



    Initialization: The __init__ method initializes the class with the API key and sets the base URL for the API endpoints.

    request_extraction: This method requests a new data extraction by sending a GET request to the /getExtraction endpoint with the specified query and output format.

    check_extraction_status: This method checks the status of a data extraction by sending a GET request to the /getExtractionStatus endpoint with the task ID.

    cancel_extraction: This method cancels an ongoing extraction by sending a GET request to the /cancelExtraction endpoint with the task ID.

    delete_extraction: This method deletes a completed extraction by sending a DELETE request to the /deleteExtraction endpoint with the task ID.


"""

import requests

class CORDISDataExtractionAPI:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://cordis.europa.eu/api/dataextractions"

    def request_extraction(self, query, output_format="json"):
        """Request a new data extraction."""
        url = f"{self.base_url}/getExtraction"
        params = {
            "query": query,
            "outputFormat": output_format,
            "key": self.api_key
        }
        response = requests.get(url, params=params)
        return response.json()

    def check_extraction_status(self, task_id):
        """Check the status of a given extraction."""
        url = f"{self.base_url}/getExtractionStatus"
        params = {
            "taskId": task_id,
            "key": self.api_key
        }
        response = requests.get(url, params=params)
        return response.json()

    def cancel_extraction(self, task_id):
        """Cancel an ongoing extraction."""
        url = f"{self.base_url}/cancelExtraction"
        params = {
            "taskId": task_id,
            "key": self.api_key
        }
        response = requests.get(url, params=params)
        return response.json()

    def delete_extraction(self, task_id):
        """Delete a completed extraction."""
        url = f"{self.base_url}/deleteExtraction"
        params = {
            "taskId": task_id,
            "key": self.api_key
        }
        response = requests.delete(url, params=params)
        return response.json()

# Example usage:
# api_wrapper = CORDISDataExtractionAPI(api_key="your_api_key_here")
# response = api_wrapper.request_extraction(query="contenttype='project' AND (programme/code='H2020')", output_format="csv")
# print(response)

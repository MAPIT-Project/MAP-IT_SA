import requests
import xml.etree.ElementTree as ET

def get_project_data(project_id):
    """
    Haalt projectdata op van de CORDIS REST API en retourneert een dictionary met de data.
    """
    url = f"https://cordis.europa.eu/project/id/{project_id}?format=xml"
    response = requests.get(url)
    response.raise_for_status()  # genereer een exception voor HTTP-fouten

    # Parse de XML-response
    root = ET.fromstring(response.content)

    # Extraheer de gewenste data
    project_data = {
        "rcn": root.find(".//rcn").text,
        "acronym": root.find(".//acronym").text,
        "title": root.find(".//title").text,
        "startDate": root.find(".//startDate").text,
        "endDate": root.find(".//endDate").text,
        # Voeg hier andere velden toe die je wilt extraheren
    }

    return project_data

# Voorbeeldgebruik
project_id = 101016751
project = get_project_data(project_id)
print(project)

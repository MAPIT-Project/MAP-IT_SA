import openai

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time

import xml.etree.ElementTree as ET
import json
import requests
from bs4 import BeautifulSoup




def get_ai_response(self, user_text):

    key = "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"

    client = openai.OpenAI(api_key=key) 

    question = user_text

    role = f"""You play the role of a knowledge steward providing the research and innovation landscape of European research projects. You are helping to a research university or institute or SME to retrieve information from the corpus of previously funded projects.
        Your scenario of operation is as such: 
        You will receive a question. In two or three stages, you extract queries from the question. At the first stage, you should extract queries to retrieve information about projects required to answer the questions. The first stage queries will be input to a xml retriever. Those queries may be names, topics, keywords, used methods and technologies of the projects as well as information related to participating organizations such as name, country, type, personnel of the institution. Occasionally, it may be start and end dates of projects, a budget interval or the name or code of a project call. 
        The xml retriever will retrieve xml files that include information about the project. At the second stage, according to information in the xml files and the information need in the question, you will extract information from the retrieved xml files.
        In rare cases, a third stage in which additional queries are sent to the xml retriever may be required. 
        """

    quest = f"""The question is: {question}
                Please generate the first stage queries to input to the xml retriever to retrieve projects relevant to the question. Generate neat and concise textual boolean queries. If you need to connect parts of a query with "AND" connective, give them as seperate queries. That is, for example, if the query is "word1 AND word2" give it as two seperate queries which are "word1" and "word2". However, if you need to connect parts of a query with "OR" do it explicitly and do not seperate it into multiple queries in this case. That is, "word1 OR word2" should be given as it is. If you generate a query about dates, write in the format "startDate<YEAR-MONTH-DAY", "endDate>YEAR-MONTH-DAY". Note that date related information need may be implicitly given in the question using words recent, first, last etc.  If you generate a query about geographical locations, only include country names and no other region names. Explain your reasoning step by step. Do not provide the queries or relations about which you are not sure. Give your whole answer in xml format with the fields <explanation>,<code>, and <problem>. Your explanations goes under <explanations> key. Under the <code> key, provide the queries as a Python code in the following format:   
                "
                queries= []
                problem_flag = False
                required_information = []
                "
                Give the code in exactly two lines. problem_flag is set True when such a problem in the question exists: If you think the question is problematic (irrelevant or too general or we have no sufficient information sources to answer the question), set the problem_flag in the code and write the problem and a brief guiding sentence for the user under the <problem> key.
                For example, for the question "What are the machine learning related projects?" the queries list should be queries = [machine learning OR deep learning OR artificial intelligence]. Please keep this format. Note that queries should only include texts in natural language and the logical connectives. If no queries can be generated from given information, take the question itself as the query and add it to the queries list.
                Also, as you know, some xml files each holding information about one project will be returned after queries run. For the second stage (or for answer generation without second stage), which type of information will be required? Fill the required_information list with the required types of information. Available types of information are project_objective, keywords, call_scope, budget, participant_names, participant_properties, participant_countries, publications. For example, if countries of participants are required for the second stage or for direct answer generation, the required information list ahould be required_information = [participant_countries].
                The last remark for you: If the question ask for filtering projects according to a metric such as best projects, worst projects, most successful projects etc., we need some restrictions about the projects we will consider, such as topics, participants, keywords etc. of the project. Otherwise we cannot reply the question. However, if the set of projects we should consider is sufficiently restricted, then we can devise a metric to answer such questions, therefore, no problem. For example, we cannot answer the question of most successful project, however, we may answer the questions of most successful machine learning project or the most successfull project conducted in Central Europe in the last decade. 
                """
    response = client.chat.completions.create(
        model="gpt-4-turbo",
        #model="gpt-4",
        messages=[
            {"role": "system", "content": role},
            {"role": "user", "content": quest}
        ],
        temperature=0.9
    )

    conversation_history = []
    conversation_history.append({"role": "system", "content": role})
    conversation_history.append({"role": "user", "content": quest})

    ans = response.choices[0].message.content

    ans_lines = response.choices[0].message.content.splitlines()

    queries = []
    for line in ans_lines:
        if "problem_flag" in line:
            if "True" in line:
                #print(list(filter(lambda x: x.startswith("<problem>"),ans_lines)))
                end_flag = 1
                break
        if "queries=" in line or "queries =" in line:
            lst = line[line.index("["):line.index("]")+1]
            queries = eval(lst)


    cordis_search_link_head = f"""https://cordis.europa.eu/search?q=contenttype%3D%27project%27%20AND%20language%3D%27en%27%20AND%20"""
    cordis_search_link_tail = f"""&p=1&num=10&srt=Relevance:decreasing&archived=true"""


    body = ""

    dates = []

    for query in queries:
        query2L = query.split("OR")
        
        for idx,elm in enumerate(query2L):
            if "startdate" in elm.lower() or "enddate" in elm.lower():
                dates.append(elm)
                del query2L[idx]

        if len(query2L):
            query2L = ["%27"+x.strip()+"%27" for x in query2L]
            query2L = [x.replace(" ","%20") for x in query2L]
            query = "(" + "%20OR%20".join(query2L) + ")"
        
        else:
            continue

        body = body+"%20"+query+"%20" if query[-3:]!="%20" else body+"%20"+query
        body = body + "AND%20"
        

    datefilter=""
    for q in dates:
        if "=" in q:
            q.replace("=","")
        if "<" in q:
            q.replace("<","%3C")
        if ">" in q:
            q.replace(">","%3E")
        datefilter = "%20" + q + "%20" + datefilter

    body = datefilter + body

    cordis_link = cordis_search_link_head + body + cordis_search_link_tail

        

    # FOR SILENCE #
    options = webdriver.ChromeOptions()
    options.add_argument("headless")
    driver = webdriver.Chrome(options=options)

    links = [] 

    #driver = webdriver.Chrome()
    driver.get(cordis_link)
    time.sleep(6)  # Allow page to load


    results = driver.find_elements(By.CSS_SELECTOR, "app-card-search")[:10]

    #print("\n First 10 Retrieved Results:")
    for i, result in enumerate(results, start=1):
        try:
            title_element = result.find_element(By.CSS_SELECTOR, "a.c-card-search__title")
            title = title_element.text.strip()
            link = title_element.get_attribute("href")  # LINK***

            links.append(link)

        except Exception as e:
            print(f"Error extracting result {i}: {e}")

    driver.quit()



    def fetch_webpage_content(url):
        """Retrieve webpage content as an XML string."""
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()  # Raise error for bad responses (4xx, 5xx)

            # Parse content as XML
            soup = BeautifulSoup(response.content, 'xml')  # Keep XML structure

            # Remove unnecessary tags (optional)
            for tag in soup(["script", "style"]):
                tag.decompose()

            # Return XML string properly
            return str(soup)  # Preserve XML structure

        except Exception as e:
            return f"Failed to fetch webpage: {e}"
        



    def remove_namespace(element):
        for elem in element.iter():
            if '}' in elem.tag:
                elem.tag = elem.tag.split('}', 1)[1]  #remove namespace

    def extract_project_data(xml_string):
        if not xml_string.strip():
            raise ValueError("Error: Provided XML string is empty!")

        try:
            root = ET.fromstring(xml_string.strip())  # Ensure clean parsing
            remove_namespace(root)  # Remove XML namespaces
        except ET.ParseError as e:
            raise ValueError(f"XML parsing failed: {e}")

        project_data = {}

        #objective
        objective = root.find(".//objective")
        project_data["objective"] = objective.text if objective is not None else "Unknown"

        #title
        title = root.find(".//title")
        project_data["title"] = title.text if title is not None else "Unknown"

        #keywords
        keywords = root.find(".//keywords")
        keywords = keywords.text.split(",") if keywords is not None else "Unknown"
        project_data["keywords"] = keywords

        #call information
        call_id = root.find(".//call/identifier")
        project_data["call"] = {
            "id": call_id.text if call_id is not None else "Unknown"
        }

        #budget-related information
        total_budget = root.find(".//totalCost")
        eu_contrib = root.find(".//ecMaxContribution")
        project_data["budget"] = {
            "total_cost": total_budget.text if total_budget is not None else "Unknown",
            "eu_contribution": eu_contrib.text if eu_contrib is not None else "Unknown"
        }

        #participants
        participants = []
        for org in root.findall(".//organization"):
            name = org.find(".//legalName")
            country = org.find(".//country")
            city = org.find(".//city")
            attributes = {
                "name": name.text if name is not None else "Unknown",
                "country": country.text if country is not None else "Unknown",
                "city": city.text if city is not None else "Unknown"
            }
            participants.append(attributes)

        project_data["participants"] = participants

        return project_data


    jsons = []
    for link in links[:5]:
        link += "?format=xml"
        xml = fetch_webpage_content(link)
        to_json = extract_project_data(xml)
        jsons.append(to_json)


    #prompt2 = f"""xml files holding project informations are converted to json files. The json files embodying detailed information about relevant projects are as follows: {jsons}. Reply the question asked in the beginning accordingly. You may discard some projects if you think they are not really relevant to the question. To remind, the question is: {question}. Give your answer as a free text."""
    prompt2 = f"""xml files holding project informations are converted to json files. The json files embodying detailed information about relevant projects are as follows: {jsons}. Reply the question asked in the beginning accordingly. You may discard some projects if you think they are not really relevant to the question. To remind, the question is: {question}. Give your answer as a free text. Never say "provided json file" directly. If you need you may refer to the provided json file by "retrieved information". You may ignore some parts of the retrieved information. If you do so, do not say you ignored them. Just do not mention the ignored parts."""

    conversation_history.append({"role": "user", "content": prompt2})

    response = client.chat.completions.create(
        model="gpt-4-turbo",
        messages=conversation_history,
        temperature=0.251
    )

    return response.choices[0].message.content

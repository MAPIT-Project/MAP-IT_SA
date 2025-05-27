

import openai

from selenium import webdriver
#from selenium.webdriver.chrome.service import Service
#from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
#from selenium.webdriver.common.keys import Keys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import xml.etree.ElementTree as ET
#import json
import requests
from bs4 import BeautifulSoup




def mapitAI(question_text):
    def createCordisLink(queries):
        cordis_search_link_head = f"""https://cordis.europa.eu/search?q=contenttype%3D%27project%27%20AND%20language%3D%27en%27%20AND%20"""
        cordis_search_link_tail = f"""&p=1&num=10&srt=Relevance:decreasing&archived=true"""

        body = ""
        for query in queries:
            query2L = query.split("OR")
            for i,q in enumerate(query2L):
                if ":" in q:
                    query2L[i] = q[q.index(":")+1:]

            """
            dates = []
            for idx,elm in enumerate(query2L):
                if "startdate" in elm.lower() or "enddate" in elm.lower():
                    dates.append(elm)
                    del query2L[idx]
            """    
            ##########################
            query2L = [x.replace("<","<%3D") for x in query2L]
            query2L = [x.replace(">",">%3D") for x in query2L]
            query2L = [x.replace("totalCost","%2Fproject%2FtotalCost") for x in query2L]
            query2L = [x.replace("totalCost=","totalCost%3D") for x in query2L]
            #############################
            query2L = ["%27"+x.strip()+"%27" if "%3D" not in x else x.strip() for x in query2L]
            query2L = [x.replace(" ","%20") for x in query2L]
            query = "(" + "%20OR%20".join(query2L) + ")"
            """
            for q in dates:
                if "<" in q:
                    q = q[:q.index("<")+1] + "%3D" + q[q.index("<")+1:]
                elif ">" in q:
                    q = q[:q.index(">")+1] + "%3D" + q[q.index(">")+1:]
                query = query + "%20" + q + "%20"
            """
            body = body+"%20"+query+"%20" if query[-3:]!="%20" else body+"%20"+query
            body = body + "AND%20"

        if body.endswith("AND%20"):
            body = body[:-6]
        if not body and cordis_search_link_head.endswith("AND%20"):
            cordis_search_link_head = cordis_search_link_head[:-6]
        cordis_link = cordis_search_link_head + body + cordis_search_link_tail

        #print(cordis_link)
        return cordis_link
        

    def getProjects(cordis_link,n_links_per_page):
        options = webdriver.ChromeOptions()
        options.add_argument("headless")
        driver = webdriver.Chrome(options=options)

        links = []
        try:
            driver.get(cordis_link)
            time.sleep(6)  # Wait for the page to load
            #time.sleep(10)  # Wait for the page to load

            results = driver.find_elements(By.CSS_SELECTOR, "app-card-search")[:n_links_per_page]

            for result in results:
                try:
                    title_element = result.find_element(By.CSS_SELECTOR, "a.c-card-search__title")
                    link = title_element.get_attribute("href")
                    links.append(link)
                except Exception as e:
                    print(f"Error extracting a link: {e}")
        finally:
            driver.quit()

        return links






    def fetch_webpage_content(url):
        """Retrieve webpage content as an XML string."""
        try:
            response = requests.get(url, timeout=10)
            #response = requests.get(url, timeout=5)
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
                elem.tag = elem.tag.split('}', 1)[1]  # Remove namespace

    def extract_project_data(xml_string):
        if not xml_string.strip():
            raise ValueError("Error: Provided XML string is empty!")

        try:
            root = ET.fromstring(xml_string.strip())  # Ensure clean parsing
            remove_namespace(root)  # Remove XML namespaces
        except ET.ParseError as e:
            raise ValueError(f"XML parsing failed: {e}")

        project_data = {}

        # Extract project objective
        objective = root.find(".//objective")
        project_data["objective"] = objective.text if objective is not None else "Unknown"

        # Extract project title
        title = root.find(".//title")
        project_data["title"] = title.text if title is not None else "Unknown"


        # Extract keywords
        keywords = root.find(".//keywords")
        keywords = keywords.text.split(",") if keywords is not None else "Unknown"
        project_data["keywords"] = keywords

        # Extract call information
        call_id = root.find(".//call/identifier")
        project_data["call"] = {
            "id": call_id.text if call_id is not None else "Unknown"
        }

        # Extract budget-related information
        total_budget = root.find(".//totalCost")
        eu_contrib = root.find(".//ecMaxContribution")
        project_data["budget"] = {
            "total_cost": total_budget.text if total_budget is not None else "Unknown",
            "eu_contribution": eu_contrib.text if eu_contrib is not None else "Unknown"
        }

        # Extract participants' information
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





    def getProjectsParallel(cordis_links, n_links_per_page=5, max_parallel_browsers=5):
        """Visit multiple Cordis pages in parallel and fetch links."""
        all_links = []

        with ThreadPoolExecutor(max_workers=max_parallel_browsers) as executor:
            futures = [executor.submit(getProjects, link, n_links_per_page) for link in cordis_links]

            for future in as_completed(futures):
                try:
                    links = future.result()
                    all_links.extend(links)
                except Exception as e:
                    print(f"Error scraping a Cordis page: {e}")

        return all_links



    #def fetch_all_contents_batched(links, batch_size=10, parallel_workers=5):
    def fetch_all_contents_batched(links, batch_size=5, parallel_workers=5):
        jsons = []
        # Divide into batches
        for i in range(0, len(links), batch_size):
            batch = links[i:i+batch_size]
            #print(f"\nProcessing batch {i//batch_size + 1}: {len(batch)} links...")

            with ThreadPoolExecutor(max_workers=parallel_workers) as executor:
                future_to_url = {executor.submit(fetch_webpage_content, url): url for url in batch}

                for future in as_completed(future_to_url):
                    url = future_to_url[future]
                    try:
                        xml = future.result()
                        to_json = extract_project_data(xml)
                        jsons.append(to_json)
                        #print(f"Fetched: {url}")
                    except Exception as e:
                        print(f"Error fetching {url}: {e}")

        return jsons





















    key = "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"


    client = openai.OpenAI(api_key=key)  # create a client instance

    #question = input("Ask boss!:")
    question = question_text

    ################################### REFINED!!! #################################################
    role = f"""You play the role of a knowledge steward providing the research and innovation landscape of European research projects. You are helping to a research university or an institute or an SME to retrieve information from the corpus of previously funded projects.
        Your scenario of operation is as such: 
        You will receive a question. In two stages, you will extract queries from the question. At the first stage, you should extract queries to retrieve information about projects required to answer the questions. The first stage queries will be input to a xml retriever. Those queries may be names, topics, keywords, used methods and technologies of the projects as well as information related to participating organizations such as name, country, type, employees of the institution. Occasionally, they may be start and end dates of projects, a budget interval or the name or the acronym of a project call. 
        The xml retriever will retrieve xml files that include information about the project. If needed, at the second stage, according to information in the xml files and the information need in the question, you will generate new queries called second stage queries that will be input to the xml retriever. 
        """

    quest = f"""The question is: {question}
                Please generate the first stage queries to input to the xml retriever to retrieve projects relevant to the question. Generate neat and concise textual boolean queries. If you need to connect parts of a query with "AND" connective, give them as seperate queries. That is, for example, if the query is "word1 AND word2" give it as two seperate queries which are "word1" and "word2". However, if you need to connect parts of a query with "OR" do it explicitly and do not seperate it into multiple queries in this case. That is, "word1 OR word2" should be given as it is. If you generate a query about dates, write in the format "startDate<YEAR-MONTH-DAY", "endDate>YEAR-MONTH-DAY". If you generate a query about budget, write in the format totalCost<1000, totalCost>1000. Moreover, if you are given a budget interval between a lower limit ans an upper limit write it in the format totalCost=lower-upper. Note that date related information need may be implicitly given in the question using words recent, first, last etc.  If you generate a query about geographical locations, only include country names and no other region names, no continent names, no city names. Explain your reasoning step by step. Do not provide the queries or relations about which you are not sure. Give your whole answer in xml format with the fields <explanation>,<code>, and <problem>. Your explanations goes under <explanations> key. Under the <code> key, provide the queries as a Python code in the following format:   
                "
                queries= []
                problem_flag = False
                required_information = []
                second_stage = False
                ranking_criteria = []
                "
                Give the code in exactly five lines.
                The list of queries you generate must be at the first line. For example, for the question "What are the machine learning related projects?" the queries list should be queries = [machine learning OR deep learning OR artificial intelligence] and for the question "What are the machine learning related projects in which Turkish organizations participated?" the queries list should be queries = [machine learning OR deep learning OR artificial intelligence, Turkey]. Please keep this format. Note that queries should only include texts in natural language and the logical connectives. If no queries can be generated from given information, take the question itself as the query and add it to the queries list. Also, do not forget that queries include be names, topics, keywords, used methods and technologies of the projects as well as information related to participating organizations such as name, country, type of the institution. Occasionally, they may include start and end dates of projects, a budget interval or the name or the acronym of a project call. 
                You must put the variable problem_flag to the second line. problem_flag is set True when such a problem in the question exists: If you think the question is problematic (irrelevant or too general or we have no sufficient information sources to answer the question), set the problem_flag to True in the code and write the problem and a brief guiding sentence for the user under the <problem> key.
                The third line must contain the list named required_information. As you know, some xml files each holding information about one project will be returned as response to your queries. Remember that a second stage of query generation may be run on those xml files. So, decide that which type of information should be requested by the second stage queries. Fill the required_information list with the required types of information that will be asked in second stage queries. Available types of information are project_objective, keywords, call_scope, budget, participant_names, participant_properties, participant_countries. For example, if countries of participants are required for the second stage, the required information list should be required_information = [participant_countries]. Note that if you need participant related information for the second stage, you generally do not need keywords. If no second stage queries are required, leave required_information list empty and set second_stage=False.
                As underlined in the provided code format, the variable second_stage must be at the fourth line.
                At the fifth line we have another list named ranking_criteria. Let me explain the expected content of that list: After the first stage retrieval, we need to rerank the retrieved documents according to some criteria such that documents that are more relevant to the intention of the first stage retrieval ranked higher. However, those reranking criteria should be dynamically inferred from the question. Those criteria are expected to be recency, novelty, actuality, impact, success, budget level of the project. For example, when the first stage retrieval aims to retrieve most successful projects, the ranking criteria may be ranking_criteria = [high success, high impact, high novelty, high budget], similarly, when the the first stage retrieval aims to retrieve the most unrealistic projects, the ranking criteria may be ranking_criteria = [low success, low impact, low actuality]. Beware that in the list of queries you are absolutely forbidden to include reranking criteria such as impact, success, recency, novelty, actuality! For example, ["machine learning", "successful"] and ["machine learning", "high impact"] are WRONG queries because they respectively include the words "successful" and "high impact". 
                Before giving the code, in your explanation, explicitly write to what the question reduced after receiving the reply to the first stage query. That reduced question will help you to formulate the required information and to decide the ranking criteria. Then, try justifying that reduced question. If you cannot justify it, change the reduced question. Additionally, in your explanation, explicitly write why you selected the required information types and ranking criteria you selected. Then, try justifying your selections, and change the selections you cannot justify.
                The last remarks for you: Firstly, if the second stage will not require retrieving information about projects or participating organizations, such a second stage is unnecessary. So, for such cases, set second_stage = False. Secondly, if the question asks for filtering projects according to a metric such as best projects, worst projects, most successful projects etc., we need some restrictions about the projects we will consider, such as topics, participants, keywords etc. of the project. Otherwise we cannot reply the question, so you must set problem_flag = True in this case. Also, if the only restriction is about time, we can still not reply, so set problem_flag = True in this case as well. However, if the set of projects we should consider is sufficiently restricted, then we can devise a metric to answer such questions, therefore, no problem in this case. For example, we cannot answer the questions most successful project or the most successful recent project, however, we can answer the questions of most successful machine learning project or the most successful project conducted in Central Europe in the last decade. 
                """
    ###################################################################

    response = client.chat.completions.create(
        model="gpt-4-turbo",
        #model="gpt-4",
        messages=[
            {"role": "system", "content": role},
            {"role": "user", "content": quest}
        ],
        top_p=0.75,
        temperature = 0.9,
        #temperature= 0.6,
        n=3
    )

    conversation_history = []
    conversation_history.append({"role": "system", "content": role})
    conversation_history.append({"role": "user", "content": quest})

    #ans = response.choices[0].message.content
    #***************************************
    ans = response.choices[1].message.content
    #***************************************

    conversation_history.append({"role": "assistant", "content": ans})
    #print(ans)
    """
    ans_lines = response.choices[0].message.content.splitlines()
    print(ans_lines)
    print("\n")
    ans_lines = response.choices[1].message.content.splitlines()
    print(ans_lines)
    print("\n")
    ans_lines = response.choices[2].message.content.splitlines()
    print(ans_lines)
    """

    #***************************************************************
    ans_lines = response.choices[1].message.content.splitlines()
    #***************************************************************

    end_flag = False
    queries = []
    next_pass = 0
    new_query_keys = []
    rerank_criteria = []
    for line in ans_lines:
        if line == "problem_flag=True" or line=="problem_flag = True":
                end_flag = True
                break
        if "queries=" in line or "queries =" in line:
            lst = line[line.index("["):line.index("]")+1]
            queries = eval(lst)
        if "second_stage" in line:
            if "True" in line:
                next_pass = 1
        if "required_information=" in line or "required_information =" in line:
            lst = line[line.index("["):line.index("]")+1]
            new_query_keys = eval(lst)
        if "ranking_criteria=" in line or "ranking_criteria =" in line:
            lst = line[line.index("["):line.index("]")+1]
            rerank_criteria = eval(lst)

    #print(queries)

    #to_cordis = " AND ".join(queries) if len(queries)>1 else queries[0]
    #print(to_cordis)




    if end_flag:
            start_problem = ans.index("<problem>")
            end_problem = ans.index("</problem>")
            problem_text = ans[start_problem+9:end_problem]
            return problem_text


    else:
        cordis_link = createCordisLink(queries)
        #links = getProjects(cordis_link,5)
        links = getProjects(cordis_link,10)


        #print(links)






        jsons = []
        for link in links:
            link += "?format=xml"
            xml = fetch_webpage_content(link)
            #f = open("xmlfile.txt", "w")
            #f.write(xml)
            #f.close()
            to_json = extract_project_data(xml)
            jsons.append(to_json)

        #print(len(jsons))
        """
        if next_pass and new_query_keys:
            for project in jsons:
                for attr in new_query_keys:
                    
        """


        #prompt2 = f"""xml files embodying detailed information about relevant projects are as follows: {xmls}. Reply the question asked in the beginning accordingly. You may discard some projects if you think they are not really relevant to the question. To remind, the question is: {question}. Give your answer as a free text."""









        ############################# FIRST RERANKER #################################################

        #reranker_role = f"""You help an AI knowledge steward that retrieves information from the corpus of previously funded projects. Specifically, you are responsible from reranking the projects according to some criteria provided by the AI knowledge steward. Thus, you help the AI knowledge steward such that it can select which projects to consider. Note that each project is represented by a json file and the list of projects you receive is a list of json files. In parallel, your response must preserve the format, which means you must return a list of the json files without changing the individual files but only changing their order in the list."""
        reranker_role = f"""You help an AI knowledge steward that retrieves information from the corpus of previously funded projects. Specifically, you are responsible from reranking the projects according to some criteria provided by the AI knowledge steward. Thus, you help the AI knowledge steward such that it can select which projects to consider. Note that each project is represented by a json file and the list of projects you receive is a list of json files."""


        #rerank_criteria = ["brilliant", "expensive"]
        prompt_rerank=f"""The json files embodying detailed information about relevant projects are as follows: {jsons}. Sort those json files according to the criteria in the following list: {rerank_criteria}. Also consider their relevance to the question and their overall importance. At the very and of your response, give the sorted list of titles of projects. The titles you put in the list must be written totally the same as they are in the json file. The list must be a python list named sorted_titles and must be in a single line. Except that list, do not include any python code in your reponse."""


        reranker_response = client.chat.completions.create(
            model="gpt-4-turbo",
            #model="gpt-4",
            messages=[
                {"role": "system", "content": reranker_role},
                {"role": "user", "content": prompt_rerank}
            ],
            #top_p=0.7,
            #temperature = 0.95,
        )


        reranked_str = reranker_response.choices[0].message.content

        #print(reranked_str)

        offset = reranked_str.index("sorted_titles =") if "sorted_titles =" in reranked_str else reranked_str.index("sorted_titles=")
        start_idx_lst = reranked_str.index("[",offset)
        end_idx_lst = reranked_str.index("]",start_idx_lst)

        #print(reranked_str[start_idx_lst:end_idx_lst+1])
        #print("|n")
        sorted_titles = reranked_str[start_idx_lst:end_idx_lst+1]
        #print(sorted_titles[0])
        #print(sorted_titles[-1])

        sorted_titles = eval(reranked_str[start_idx_lst:end_idx_lst+1].strip())

        #print(sorted_titles)


        reranked_jsons = []
        for title in sorted_titles[:5]:
            for proj in jsons:
                #print(title)
                #print(proj["title"])
                if set(proj["title"].lower().split(" ")) - {"", " "} == set(title.lower().split(" ")) - {"", " "}:
                    #print("OK")
                    reranked_jsons.append(proj)
                    break

        jsons = reranked_jsons

        ##########################################################################################










        #print(next_pass)
        #print(new_query_keys)
        if next_pass and new_query_keys:
            info_need = new_query_keys[0] if len(new_query_keys)==1 else " and ".join(new_query_keys)
            ###prompt_next = f""" First pass retrieval is successfully completed and xml files holding project informations are converted to json files. The json files embodying detailed information about relevant projects are as follows: {jsons}. Now, as you identified at the first stage, we need to make further queries to reply the question asked at the very beginning. To remind, the question is: {question}. Please generate new queries answers of which are required to answer the question. You previously identified that we should check {info_need} to be able to form those new queries. If you need you may check other fields as well. Please give your queries line by line, one at each line. Also, at each line, write which fields of information are needed from the json file retrieved as the result of that query. If you think no additional queries needed and you are sure, say: NOTHING and explain why not more queries are needed."""
            #prompt_next = f""" First pass retrieval is successfully completed and xml files holding project informations are converted to json files. The json files embodying detailed information about relevant projects are as follows: {jsons}. Now, as you identified at the first stage, we need to make further queries to reply the question asked at the very beginning. To remind, the question is: {question}. Please generate new queries answers of which are required to answer the question. You previously identified that we should check {info_need} to be able to form those new queries. If you need you may check other fields as well. Please give your queries line by line, one at each line. Also, at each line, write which fields of information are needed from the json file retrieved as the result of that query."""
            #prompt_next = f""" First pass retrieval is successfully completed and xml files holding project informations are converted to json files. The json files embodying detailed information about relevant projects are as follows: {jsons}. Now, as you identified at the first stage, we need to make further queries to reply the question asked at the very beginning. To remind, the question is: {question}. Please generate new queries answers of which are required to answer the question. Consider each of the json files, generate queries for each. You previously identified that we should check {info_need} to be able to form those new queries. If you need you may check other fields as well. As in the first stage, the queries may consist of names, topics, keywords, used methods and technologies of the projects as well as information related to participating organizations such as name, country, type, personnel of the institution. Occassionally, they may also include start and end dates of the projects. Each of the queries must be Boolean queries. For example, if you generate a query asking METU's aerospace projects with Hungarian partners, your query should be ["METU", "aerospace", "Hungary"]. Also, other query format rules given for the first stage queries are valid for the current queries. However, give each query a list of its parts connected with AND. Resultingly, the queries list must be a list of lists. Please give your queries line by line, one at each line."""
            # only last sentence deleted from the above one:
            #prompt_next = f""" First pass retrieval is successfully completed and xml files holding project informations are converted to json files. The json files embodying detailed information about relevant projects are as follows: {jsons}. Now, as you identified at the first stage, we need to make further queries to reply the question asked at the very beginning. To remind, the question is: {question}. Please generate new queries answers of which are required to answer that question. Consider each of the json files, generate queries for each. You previously identified that we should check {info_need} to be able to form those new queries. If you need, you may check other fields as well. As in the first stage, the queries may consist of names, topics, keywords, used methods and technologies of the projects as well as information related to participating organizations such as name, country, type, personnel of the institution. Occassionally, they may also include start and end dates of the projects. Each of the queries must be Boolean queries. For example, if you generate a query asking METU's aerospace projects with Hungarian partners, your query should be ["METU", "aerospace", "Hungary"]. Never write the type of required information in a query. That is, ["METU", "aerospace", "Hungary", publications] and ["METU", "aerospace", "Hungary", participant_names] are WRONG queries! The correct version is: ["METU", "aerospace", "Hungary"]. For keyword type words in queries, apply slight query expansion so as to add very similar keywords. For example, to a query having the word "AI", add the words "machine learning" and "artificial intelligence"; or to query having the word chatbot, add the words "natural language processing" and "artificial intelligence". Also, other query format rules given for the first stage queries are valid for the current queries. However, give each query a list of its parts connected with AND. Resultingly, the queries list must be a list of lists.  Lastly, sort the queries in the query list according to their relevance to the question, actuality, and overall importance. Also output the sorted query list in the same format with the name sorted_queries. Please provide the queries list as a whole including its parantheses in a single line. That is, the query list must be in the form: queries = [[query1], [query2], ... , [queryN]], given at a single line. Sorted queries list also must given at a single line. Before writing the sorted query list, make sure that you have done the sorting properly."""
            
            prompt_next = f""" First pass retrieval is successfully completed and xml files holding project informations are converted to json files. I will provide json files soon. However, before seeing the files, check whether second stage queries are really needed to effectively reply the question. To remind, the question is: {question} and you previously identified that we should check {info_need} types of information in the retrieved json files to be able to form the second stage queries. If you decide that the second stage queries are is not required, reply the question relying on the given json files and set second_stage = False. DO NOT try facilitating efficient use of the data already retrieved. If the second stage retrieval may be beneficial, do not set the second_stage variable to False. So, if you think the second stage queries are really required, follow the instructions: Consider each of the json files, generate queries for each. Do not include any of the elements of ranking_criteria list in your queries. The json files embodying detailed information about retrieved projects are as follows: {jsons}. Note that if you ask for participant related information in a query, you generally do not need keywords. As in the first stage, the queries may consist of names, topics, keywords, used methods and technologies of the projects as well as information related to participating organizations such as name, country, type, employees of the institution. Occassionally, they may also include start and end dates of the projects. Each of the queries must be Boolean queries. But do not use negated queries (i.e. do not use NOT and non- type queries). For example, if you generate a query asking METU's aerospace projects with Hungarian partners, your query should be ["METU", "aerospace", "Hungary"]. Never write the type of required information in a query. That is, ["METU", "aerospace", "Hungary", "keywords"] and ["METU", "aerospace", "Hungary", "participant_names"] and ["METU", "aerospace", "Hungary", "research areas"] and ["METU", "aerospace", "Hungary", "other projects"] are WRONG queries, do not form such queries! The correct version is: ["METU", "aerospace", "Hungary"]. Similarly, you are not allowed write ranking criteria in a query. That is, ["METU", "aerospace", "Hungary", "recency"] and ["METU", "aerospace", "Hungary", "high budget"] and ["METU", "aerospace", "Hungary", "impact"] and ["METU", "aerospace", "Hungary", "recent"] and ["METU", "aerospace", "Hungary", "impactful"] are WRONG queries, do not form such queries! Again, the correct version is: ["METU", "aerospace", "Hungary"]. Also, other query format rules given for the first stage queries are valid for the current queries. However, give each query a list of its parts connected with AND. Resultingly, the queries list must be a list of lists. The query list must be in the form: queries = [[query1], [query2], ... , [queryN]]. Before providing the queries justify your query formulation method and your queries."""
            #prompt_next = f""" First pass retrieval is successfully completed and xml files holding project informations are converted to json files. I will provide json files soon. However, before seeing the files, check whether second stage queries are really needed to effectively reply the question. To remind, the question is: {question}. First of all, think whether this second stage is required. If the second stage queries are is not required, reply the question relying on the given json files and set second_stage = False. DO NOT try facilitating efficient use of the data already retrieved. If the second stage retrieval may be beneficial, do not set the second_stage variable to False. So, if you think this second stage is required, please generate new queries answers of which are required to answer that question. Consider each of the json files, generate queries for each. The json files embodying detailed information about retrieved projects are as follows: {jsons}. You previously identified that we should check {info_need} to be able to form those new queries, however, some of these fields may be unnecessary. Check carefully and discard the unnecesary fields. Note that if you ask for participant related information in a query, you generally do not need keywords. As in the first stage, the queries may consist of names, topics, keywords, used methods and technologies of the projects as well as information related to participating organizations such as name, country, type, employees of the institution. Occassionally, they may also include start and end dates of the projects. Each of the queries must be Boolean queries. For example, if you generate a query asking METU's aerospace projects with Hungarian partners, your query should be ["METU", "aerospace", "Hungary"]. Never write the type of required information in a query. That is, ["METU", "aerospace", "Hungary", "keywords"] and ["METU", "aerospace", "Hungary", "participant_names"] and ["METU", "aerospace", "Hungary", "research areas"] and ["METU", "aerospace", "Hungary", "other projects"] are WRONG queries! The correct version is: ["METU", "aerospace", "Hungary"]. Similarly, never write ranking criteria in a query. That is, ["METU", "aerospace", "Hungary", "recency"] and ["METU", "aerospace", "Hungary", "high budget"] and ["METU", "aerospace", "Hungary", "impact"] are WRONG queries! Again, the correct version is: ["METU", "aerospace", "Hungary"]. Also, other query format rules given for the first stage queries are valid for the current queries. However, give each query a list of its parts connected with AND. Resultingly, the queries list must be a list of lists. The query list must be in the form: queries = [[query1], [query2], ... , [queryN]]. Before providing the queries justify your query formulation method and your queries."""

            #******** ADD A SENTENCE FOR DISCARDING SOME UNNECESSARY QUERIES. EX: IF WE ASK FOR OTHER GERMAN PARTNERS OF OUR CURRENT PARTNERS, NO NEED FOR QUERIES FOR GERMAN ORGANIZATIONS

            conversation_history.append({"role": "user", "content": prompt_next})

            response = client.chat.completions.create(
                model="gpt-4-turbo",
                messages=conversation_history,
                top_p=0.7,
                temperature = 0.75,
                n=3
            )


            ans_lines = response.choices[1].message.content.splitlines()
            #print("\n")
            #print("2nd STAGE ANS:")
            #print(response.choices[1].message.content)
            #print("\n")
            queries = []
            st_idx = -1
            quit_flag = False
            for i,line in enumerate(ans_lines):
                if line.strip() == "second_stage = False" or line.strip() == "second_stage=False":
                    quit_flag = True
            if not quit_flag:
                for i,line in enumerate(ans_lines):
                    #if "sorted_queries=" in line or "sorted_queries =" in line:
                    if "queries=" in line or "queries =" in line:
                        #print("\n")
                        #print(line)
                        #print("\n")
                        st_idx = i
                        break
                q_list = ""
                if "[]" not in ans_lines[st_idx:]:
                    for j,line in enumerate(ans_lines[st_idx:]):
                            if "=" in line and j!=0:
                                break
                            if "=" in line or "[" in line or "]" in line:
                                q_list += line.strip()
                else:
                    queries = []
                #print(q_list)
                queries = eval(q_list[q_list.find("["):])
                #print(queries)

                
                cordis_links = [createCordisLink(query) for query in queries[:5]]
                project_links = getProjectsParallel(cordis_links,3,5)


                #print(project_links)


                #getProjectsParallel does the work, instead of the commented-out section below
                """
                links = []
                for query in queries[:3]:
                    cordis_link = createCordisLink(query)
                    links.extend(getProjects(cordis_link,3))
                    if len(links)>=6:
                        break


                print(links)
                """

                all_project_links_xml = [link+"?format=xml" for link in project_links]
                jsons = fetch_all_contents_batched(all_project_links_xml, batch_size=5, parallel_workers=5)

                #print(len(jsons))












                

                #fetch_all_contents_batched does the work, instead of the commented-out section below
                """
                jsons = []
                for link in links[:6]:
                    link += "?format=xml"
                    xml = fetch_webpage_content(link)
                    #f = open("xmlfile.txt", "w")
                    #f.write(xml)
                    #f.close()
                    to_json = extract_project_data(xml)
                    jsons.append(to_json)
                """


                #if "NOTHING" in response.choices[0].message.content.strip():
                #    print("HERE!!!!!!!!!!!!")
                #    prompt_final = f"""xml files holding final project informations are converted to json files. The json files embodying detailed information about relevant projects are as follows: {jsons}. Reply the question asked in the beginning accordingly. You may discard some projects if you think they are not really relevant to the question. To remind, the question is: {question}. Give your answer as a free text. Never say "provided json file" directly. If you need you may refer to the provided json file by "retrieved information"."""
                #    conversation_history.append({"role": "user", "content": prompt_final})
                #    response = client.chat.completions.create(model="gpt-4-turbo", messages=conversation_history, temperature=0.5)


        #else:
        #print("HERE!!!")
        #print(len(jsons))
        
        #prompt_final = f"""xml files holding final project informations are converted to json files. The json files embodying detailed information about relevant projects are as follows: {jsons}. Reply the question asked in the beginning accordingly. You may discard some projects if you think they are not really relevant to the question. To remind, the question is: {question}. Give your answer as a free text. Never say "provided json file" directly. If you need you may refer to the provided json file by "retrieved information"."""
        prompt_final = f"""xml files holding final project informations are converted to json files. The json files embodying detailed information about relevant projects are as follows: {jsons}. Read those files carefully and accordingly reply the question asked in the very beginning. To remind, the question is: {question}. Refer as many of the json files (i.e. projects) as you need. If you mention a project, you must write its name explcitly. You may discard some projects if you find them irrelevant. Give your answer as a free text. Never say "provided json files" directly. If you need you may refer to some or all of the provided json files by "retrieved information". Further, remind that you are responding to a lay user, not to a developer. Therefore, in case the provided json files are empty or somehow problematic, do not directly say that problem, instead, underline the possible problems the lay user or the search procedure might have caused."""

        conversation_history.append({"role": "user", "content": prompt_final})

        response = client.chat.completions.create(
            model="gpt-4-turbo",
            messages=conversation_history
        )


        #print(response.choices[0].message.content)
        return response.choices[0].message.content

        #for f in jsons:
        #    print(f["title"])
        #    print(f["budget"])





if __name__ == "__main__":
    question = input("Ask boss!:")
    print(mapitAI(question))
import os
import openai
import time
import json
import requests
import xml.etree.ElementTree as ET
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup

# Load environment variables
load_dotenv()

class CordisRAG:
    """
    Retrieval-Augmented Generation system for European research projects using CORDIS database.
    """
    
    def __init__(self):
        """Initialize the CordisRAG system."""
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OpenAI API key not found. Please set the OPENAI_API_KEY environment variable.")
        self.client = openai.OpenAI(api_key=api_key)
        
    def get_ai_response(self, user_text: str) -> str:
        """
        Process a user query through the RAG pipeline.
        
        Args:
            user_text: The user's question about European research projects
            
        Returns:
            str: The AI-generated response based on retrieved CORDIS data
        """
        try:
            # System role definition
            role = self._get_system_role()
            
            # Generate queries from user question
            queries, required_info = self._extract_queries(role, user_text)
            
            # Search CORDIS database
            search_links = self._search_cordis(queries)
            
            # Retrieve and process project data
            project_data = self._retrieve_project_data(search_links)
            
            # Generate final response
            return self._generate_answer(role, user_text, project_data)
            
        except Exception as e:
            return f"An error occurred while processing your request: {str(e)}"
    
    def _get_system_role(self) -> str:
        """Define the system role for the AI."""
        return """You play the role of a knowledge steward providing the research and innovation landscape of European research projects. You are helping a research university or institute or SME to retrieve information from the corpus of previously funded projects.
        Your scenario of operation is as such: 
        You will receive a question. In two or three stages, you extract queries from the question. At the first stage, you should extract queries to retrieve information about projects required to answer the questions. The first stage queries will be input to a xml retriever. Those queries may be names, topics, keywords, used methods and technologies of the projects as well as information related to participating organizations such as name, country, type, personnel of the institution. Occasionally, it may be start and end dates of projects, a budget interval or the name or code of a project call. 
        The xml retriever will retrieve xml files that include information about the project. At the second stage, according to information in the xml files and the information need in the question, you will extract information from the retrieved xml files.
        In rare cases, a third stage in which additional queries are sent to the xml retriever may be required."""
    
    def _extract_queries(self, role: str, question: str) -> tuple:
        """
        Extract search queries from the user question using GPT-4.
        
        Args:
            role: The system role
            question: The user's question
            
        Returns:
            tuple: (queries, required_information)
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
                The last remark for you: If the question ask for filtering projects according to a metric such as best projects, worst projects, most successful projects etc., we need some restrictions about the projects we will consider, such as topics, participants, keywords etc. of the project. Otherwise we cannot reply the question. However, if the set of projects we should consider is sufficiently restricted, then we can devise a metric to answer such questions, therefore, no problem. For example, we cannot answer the question of most successful project, however, we may answer the questions of most successful machine learning project or the most successful project conducted in Central Europe in the last decade. 
                """
        
        response = self.client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": role},
                {"role": "user", "content": quest}
            ],
            temperature=0.9
        )
        
        ans = response.choices[0].message.content
        ans_lines = ans.splitlines()
        
        # Extract queries
        queries = []
        required_information = []
        problem_flag = False
        
        for line in ans_lines:
            if "problem_flag" in line and "True" in line:
                problem_flag = True
                break
            if "queries=" in line or "queries =" in line:
                lst = line[line.index("["):line.index("]")+1]
                queries = eval(lst)
            if "required_information" in line:
                try:
                    lst = line[line.index("["):line.index("]")+1]
                    required_information = eval(lst)
                except:
                    pass
        
        if problem_flag:
            problem_message = [line for line in ans_lines if line.startswith("<problem>")]
            if problem_message:
                raise ValueError(problem_message[0].replace("<problem>", "").replace("</problem>", ""))
        
        return queries, required_information
    
    def _search_cordis(self, queries: List[str], max_results: int = 10) -> List[str]:
        """
        Search the CORDIS database with the extracted queries.
        
        Args:
            queries: List of search queries
            max_results: Maximum number of results to retrieve
            
        Returns:
            List[str]: URLs of projects found
        """
        # Build CORDIS search URL
        cordis_search_link_head = "https://cordis.europa.eu/search?q=contenttype%3D%27project%27%20AND%20language%3D%27en%27%20AND%20"
        cordis_search_link_tail = f"&p=1&num={max_results}&srt=Relevance:decreasing&archived=true"
        
        body = ""
        dates = []
        
        for query in queries:
            query2L = query.split("OR")
            
            for idx, elm in enumerate(query2L):
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
        
        datefilter = ""
        for q in dates:
            if "=" in q:
                q = q.replace("=", "")
            if "<" in q:
                q = q.replace("<", "%3C")
            if ">" in q:
                q = q.replace(">", "%3E")
            datefilter = "%20" + q + "%20" + datefilter
        
        body = datefilter + body
        cordis_link = cordis_search_link_head + body + cordis_search_link_tail
        
        # Set up headless Chrome
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        
        links = []
        
        try:
            driver = webdriver.Chrome(options=chrome_options)
            driver.get(cordis_link)
            time.sleep(6)  # Allow page to load
            
            results = driver.find_elements(By.CSS_SELECTOR, "app-card-search")[:max_results]
            
            for result in results:
                try:
                    title_element = result.find_element(By.CSS_SELECTOR, "a.c-card-search__title")
                    link = title_element.get_attribute("href")
                    links.append(link)
                except Exception as e:
                    print(f"Error extracting result: {e}")
            
            return links
        except Exception as e:
            print(f"Error during CORDIS search: {e}")
            return []
        finally:
            if 'driver' in locals():
                driver.quit()
    
    def _retrieve_project_data(self, links: List[str], max_projects: int = 5) -> List[Dict[str, Any]]:
        """
        Retrieve and process project data from CORDIS links.
        
        Args:
            links: List of CORDIS project URLs
            max_projects: Maximum number of projects to retrieve
            
        Returns:
            List[Dict]: List of project data dictionaries
        """
        project_data = []
        
        for link in links[:max_projects]:
            try:
                xml_link = link + "?format=xml"
                xml_content = self._fetch_webpage_content(xml_link)
                if xml_content:
                    project_json = self._extract_project_data(xml_content)
                    project_data.append(project_json)
            except Exception as e:
                print(f"Error retrieving project data from {link}: {e}")
        
        return project_data
    
    def _fetch_webpage_content(self, url: str) -> Optional[str]:
        """
        Retrieve webpage content as an XML string.
        
        Args:
            url: The URL to fetch
            
        Returns:
            Optional[str]: XML content as string or None if failed
        """
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'xml')
            
            # Remove unnecessary tags
            for tag in soup(["script", "style"]):
                tag.decompose()
            
            return str(soup)
        except Exception as e:
            print(f"Failed to fetch webpage {url}: {e}")
            return None
    
    def _remove_namespace(self, element):
        """Remove XML namespace from element tags."""
        for elem in element.iter():
            if '}' in elem.tag:
                elem.tag = elem.tag.split('}', 1)[1]
    
    def _extract_project_data(self, xml_string: str) -> Dict[str, Any]:
        """
        Extract structured data from project XML.
        
        Args:
            xml_string: XML content of a CORDIS project
            
        Returns:
            Dict: Structured project data
        """
        if not xml_string or not xml_string.strip():
            raise ValueError("Error: Provided XML string is empty!")
        
        try:
            root = ET.fromstring(xml_string.strip())
            self._remove_namespace(root)
        except ET.ParseError as e:
            raise ValueError(f"XML parsing failed: {e}")
        
        project_data = {}
        
        # Extract objective
        objective = root.find(".//objective")
        project_data["objective"] = objective.text if objective is not None else "Unknown"
        
        # Extract title
        title = root.find(".//title")
        project_data["title"] = title.text if title is not None else "Unknown"
        
        # Extract keywords
        keywords = root.find(".//keywords")
        keywords = keywords.text.split(",") if keywords is not None else ["Unknown"]
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
        
        # Extract participants
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
    
    def _generate_answer(self, role: str, question: str, project_data: List[Dict[str, Any]]) -> str:
        """
        Generate final answer based on retrieved project data.
        
        Args:
            role: System role for the AI
            question: Original user question
            project_data: Retrieved project data
            
        Returns:
            str: Generated answer
        """
        conversation_history = [
            {"role": "system", "content": role},
        ]
        
        prompt = f"""xml files holding project informations are converted to json files. The json files embodying detailed information about relevant projects are as follows: {json.dumps(project_data)}. Reply the question asked in the beginning accordingly. You may discard some projects if you think they are not really relevant to the question. To remind, the question is: {question}. Give your answer as a free text. Never say "provided json file" directly. If you need you may refer to the provided json file by "retrieved information". You may ignore some parts of the retrieved information. If you do so, do not say you ignored them. Just do not mention the ignored parts."""
        
        conversation_history.append({"role": "user", "content": prompt})
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4-turbo",
                messages=conversation_history,
                temperature=0.25
            )
            
            return response.choices[0].message.content
        except Exception as e:
            return f"Error generating answer: {str(e)}"


# For direct execution of the module
if __name__ == "__main__":
    # Example usage
    rag = CordisRAG()
    question = "What are some recent AI projects in healthcare with German participants?"
    print(rag.get_ai_response(question))

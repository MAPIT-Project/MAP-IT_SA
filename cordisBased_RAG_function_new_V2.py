import os
import requests
import xml.etree.ElementTree as ET
from dotenv import load_dotenv
import openai # Ensure openai is imported
from typing import List, Dict, Any, Optional

# Update to use google-genai instead of google-generativeai
from google import genai as google_genai_sdk
from google.genai import types

# Load environment variables
load_dotenv()

class CordisRAG:
    """
    Retrieval-Augmented Generation system for European research projects using CORDIS database.
    """
    
    def __init__(self, openai_api_key: Optional[str] = None, gemini_api_key: Optional[str] = None, 
                 ai_provider: str = "openai", 
                 openai_model_name: str = "gpt-4-turbo",
                 gemini_model_name: str = "gemini-2.5-flash-lite-preview-06-17"):
        """
        Initialize the RAG system.
        
        Args:
            openai_api_key: OpenAI API key. If None, attempts to load from .env.
            gemini_api_key: Gemini API key. If None, attempts to load from .env.
            ai_provider: The AI provider to use ("openai" or "gemini"). Defaults to "openai".
            openai_model_name: The OpenAI model to use. Defaults to "gpt-4-turbo".
            gemini_model_name: The Gemini model to use. Defaults to "gemini-2.5-flash-lite-preview-06-17".
        """
        load_dotenv()
        self.ai_provider = ai_provider.lower()
        self.openai_model_name = openai_model_name
        self.gemini_model_name = gemini_model_name  # Add this attribute for consistent use
        self.gemini_model_name_configured = gemini_model_name  # Keep for backward compatibility
        self.gemini_client = None # Initialize gemini_client
        # self.gemini_model = None # Remove gemini_model initialization

        if self.ai_provider == "openai":
            used_openai_api_key = openai_api_key if openai_api_key else os.getenv("OPENAI_API_KEY")
            if not used_openai_api_key:
                raise ValueError("OpenAI API key not provided and not found in .env file.")
            self.openai_client = openai.OpenAI(api_key=used_openai_api_key)
            print("CordisRAG initialized with OpenAI.")
        elif self.ai_provider == "gemini":
            used_gemini_api_key = gemini_api_key if gemini_api_key else os.getenv("GEMINI_API_KEY")
            if not used_gemini_api_key:
                raise ValueError("Gemini API key not provided and not found in .env file.")
            try:
                # Initialize client as per the demo
                self.gemini_client = google_genai_sdk.Client(api_key=used_gemini_api_key)
                print(f"CordisRAG initialized with Gemini (model: {self.gemini_model_name}). Client created.")
            except AttributeError as ae:
                # This specific AttributeError for 'configure' should no longer occur with Client() usage
                print(f"AttributeError during Gemini client initialization: {ae}. This might indicate an issue with the google-generativeai library version or installation, or an incorrect API usage pattern.")
                raise
            except Exception as e:
                print(f"Error configuring Gemini API or creating model: {e}")
                raise
        else:
            raise ValueError("Invalid AI provider specified. Choose 'openai' or 'gemini'.")

    def get_ai_response(self, question: str, max_projects_to_process: int = 5, max_cordis_results: int = 10) -> str:
        """
        Process a user query through the RAG pipeline.
        
        Args:
            question: The user's question about European research projects
            
        Returns:
            str: The AI-generated response based on retrieved CORDIS data
        """
        # Remove the try-catch block to let exceptions bubble up to FastAPI
        # System role definition
        role = self._get_system_role()
        
        # Generate queries from user question
        queries, required_info = self._extract_queries(role, question)
        
        # Search CORDIS database
        search_links = self._search_cordis(queries, max_results=max_cordis_results)
        
        # Retrieve and process project data
        project_data = self._retrieve_project_data(search_links, max_projects=max_projects_to_process)
        
        # Generate final response
        return self._generate_answer(role, question, project_data)
    
    def _get_system_role(self) -> str:
        """Define the system role for the AI."""
        return """You are an AI assistant specialized in processing information from the CORDIS database about European research projects. 
Your goal is to answer user questions based on the project data provided to you.
When generating queries, be concise and use boolean logic as specified.
When generating answers, synthesize the information from multiple projects if necessary and clearly state if the provided data is insufficient."""

    def _extract_queries(self, role: str, question: str) -> tuple:
        """
        Extract search queries from the user question using the configured AI provider.
        
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
        
        ans = ""
        if self.ai_provider == "openai":
            # print(f"Prompt for query extraction (OpenAI): Role: {role}, Question: {quest}") # For debugging
            completion = self.openai_client.chat.completions.create(
                model=self.openai_model_name, # Use configured OpenAI model
                messages=[
                    {"role": "system", "content": role},
                    {"role": "user", "content": quest}
                ],
                temperature=0.3 # Lower temperature for more deterministic query generation
            )
            ans = completion.choices[0].message.content
            # print(f"Raw response from OpenAI for query extraction: {ans}") # For debugging
        elif self.ai_provider == "gemini":
            if not self.gemini_client:
                raise RuntimeError("Gemini client not initialized.")
            
            gemini_contents = [
                types.Content(role="user", parts=[types.Part.from_text(text=role)]),
                types.Content(role="model", parts=[types.Part.from_text(text="Okay, I understand my role. I will generate queries based on the user\\\'s question.")]),
                types.Content(role="user", parts=[types.Part.from_text(text=quest)])
            ]

            # Using a simpler config for query extraction, adjust if needed
            generation_config_params = types.GenerateContentConfig(
                temperature=0.2, # Query generation should be more deterministic
                response_mime_type="text/plain" # Expecting XML-like text
            )
            
            try:
                # Change parameter name from generation_config to config
                response = self.gemini_client.models.generate_content(
                    model=self.gemini_model_name,
                    contents=gemini_contents,
                    config=generation_config_params
                )
                ans = response.text
            except Exception as e:
                print(f"Error during Gemini query extraction: {e}")
                # Fallback or re-raise, depending on desired error handling
                raise RuntimeError(f"Gemini API error during query extraction: {e}") from e
        
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
                except Exception:  # Catch specific exceptions instead of a bare except
                    pass
        
        if problem_flag:
            # Look for problem message in XML-like tags or any line containing problem information
            problem_message = ""
            
            # Try to find message between <problem> tags
            full_response = "\n".join(ans_lines)
            if "<problem>" in full_response and "</problem>" in full_response:
                start_idx = full_response.find("<problem>") + len("<problem>")
                end_idx = full_response.find("</problem>")
                problem_message = full_response[start_idx:end_idx].strip()
            else:
                # Fallback: look for lines that might contain the problem description
                for line in ans_lines:
                    line_stripped = line.strip()
                    if line_stripped and not line_stripped.startswith("<") and "problem_flag" not in line and "queries" not in line:
                        if "problem" in line_stripped.lower() or "too general" in line_stripped.lower() or "irrelevant" in line_stripped.lower():
                            problem_message = line_stripped
                            break
                
                # If still no message found, provide a default
                if not problem_message:
                    problem_message = "The question appears to be too general or not relevant to European research projects. Please provide a more specific question about research topics, countries, or time periods."
            
            raise ValueError(f"Question cannot be processed: {problem_message}")

        return queries, required_information
    
    def _search_cordis(self, queries: List[str], max_results: int = 10) -> List[Dict[str, Any]]: # Modified return type
        """
        Search the CORDIS database with the extracted queries using the CORDIS API.
        
        Args:
            queries: List of search queries (can be keyword groups with OR, or date conditions)
            max_results: Maximum number of results to retrieve
            
        Returns:
            List[Dict[str, Any]]: List of project data dictionaries from API results
        """
        base_api_url = "https://cordis.europa.eu/api/search/results"
        
        # Construct the 'q' parameter for the API
        api_q_parts = ["contenttype='project'", "language='en'"]

        for item_query in queries:
            item_query_stripped = item_query.strip()
            if not item_query_stripped: # Skip empty queries
                continue

            item_query_lower = item_query_stripped.lower()
            
            # Check if it's a date-related query
            if "startdate" in item_query_lower or "enddate" in item_query_lower:
                # Assumes date queries from _extract_queries are in a format like:
                # "startDate>YYYY-MM-DD" or "endDate<=YYYY-MM-DD"
                # These are used directly in the CORDIS API q-string.
                # Example: startDate>2018-01-01
                # Remove spaces for safety, e.g. "startDate > 2020-01-01" -> "startDate>2020-01-01"
                date_str = item_query_stripped.replace(" ", "")
                api_q_parts.append(date_str)
            else:
                # It's a keyword query, e.g., "term1 OR term2" or "term3"
                or_terms = item_query_stripped.split("OR")
                
                # Filter out empty strings that might result from splitting (e.g. "term1 OR ") and strip terms
                valid_or_terms = [term.strip() for term in or_terms if term.strip()]
                
                if not valid_or_terms: # Skip if no valid terms after splitting and stripping
                    continue
                
                # Quote each term: 'term'
                quoted_or_terms = [f"'{term}'" for term in valid_or_terms]
                
                # Join OR terms and enclose in parentheses: ('term1' OR 'term2') or ('term3')
                keyword_part = f"({ ' OR '.join(quoted_or_terms) })"
                api_q_parts.append(keyword_part)
        
        q_value = " AND ".join(api_q_parts)
        
        # API parameters
        updated_fields = "uri,rcn,title,id,code,startDate,endDate,teaser,contentUpdateDate,name,relatedImage,availableLanguages,language,issueNumber,issueDate,issueLastDate,issue,archivedDate,acronym,legalName,euCode,city,country,iprPrefix,iprNumber,iprDate,iprAwarded,description,doi,journalTitle,journalNumber,publishedYear,publishedPages,authors,periodFrom,periodTo,webItem,webItem/_ATTR_*,physUrl,webLink,webLink/_ATTR_*,physUrl,frameworkProgramme,totalCost,projectTotalCost,keywords,subjects,programme,participants"

        params = {
            "q": q_value,
            "p": 1,  # Page number, defaulting to 1
            "num": max_results,
            "srt": "Relevance:decreasing", # Sort order
            "fields": updated_fields, # Use the updated fields string
            "archived": "true"
        }
        
        # links = [] # No longer returning just links
        project_items: List[Dict[str, Any]] = [] # To store full project item dictionaries

        try:
            response = requests.get(base_api_url, params=params, timeout=30) 
            print(f"CORDIS API URL called: {response.url}") # Log URL
            print(f"CORDIS API response status code: {response.status_code}") # Log status code
            # Log a snippet of the response content for inspection
            content_snippet = response.content[:500] if response.content else "N/A"
            print(f"CORDIS API response content snippet: {content_snippet}")

            response.raise_for_status()  # Raise an exception for HTTP errors (4xx or 5xx)
            
            try:
                # Attempt to parse as JSON first, as the API might return JSON
                json_data = response.json()
                print("Successfully parsed CORDIS API response as JSON.") # Log JSON parsing success
                if json_data.get("payload") and "results" in json_data["payload"]:
                    results_list = json_data["payload"]["results"]
                    if not results_list:
                        print("JSON payload has an empty 'results' list.")
                    else:
                        print(f"Directly using {len(results_list)} items from 'results' list as project data.")
                        project_items = results_list # Assign the list of dictionaries
                    # The loop for creating 'links' by constructing URIs is removed.
                    # We now return the 'results_list' (assigned to project_items) directly.
                elif not json_data.get("payload"):
                    print("JSON response does not contain 'payload' key.")
                elif "results" not in json_data.get("payload", {}): # Added default {} for get to be safe
                     print("JSON 'payload' does not contain 'results' key.")
                else:
                    print("JSON response from CORDIS API did not contain expected payload structure. Attempting XML parse for URIs (limited data).")
                    # Fallback to XML (current XML parsing only extracts URIs, so project_items would be empty or contain minimal data)
                    # This path would mean limited data for the new extraction method.
                    xml_root = ET.fromstring(response.content)
                    self._remove_namespace(xml_root)
                    # Try to find <uri> tags directly within the XML structure
                    for uri_element in xml_root.findall(".//uri"): # More general search for URI tags
                        if uri_element.text:
                            uri_text = uri_element.text.strip()
                            if uri_text:
                                project_items.append({"uri": uri_text})  # Append as a dict

            except requests.exceptions.JSONDecodeError as json_err:
                print(f"Failed to parse CORDIS API response as JSON: {json_err}. Attempting XML parsing (limited data).")
                # If JSON decoding fails, assume it\'s XML
                try:
                    xml_root = ET.fromstring(response.content)
                    self._remove_namespace(xml_root)
                    # Current XML parsing only extracts URIs. For full data, this would need enhancement.
                    # For now, project_items will likely remain empty if this path is taken and not adapted.
                    temp_links_from_xml = []
                    for uri_element in xml_root.findall(".//uri"): 
                        if uri_element.text:
                            uri_text = uri_element.text.strip()
                            if uri_text:
                                temp_links_from_xml.append(uri_text)
                    print(f"Successfully parsed CORDIS API response as XML after JSON failure (extracted {len(temp_links_from_xml)} URIs). Full project data might be unavailable through this path.")
                    # If we wanted to populate project_items here, we'd need to convert these URIs or parse more from XML.
                    # For now, project_items remains empty, relying on the JSON path for full data.
                except ET.ParseError as xml_err_after_json_fail:
                    print(f"Critical Error: Failed to parse CORDIS API response as JSON and also as XML: {xml_err_after_json_fail}. Content: {response.content[:500]}")

            # print(f"Found {len(links)} project links via CORDIS API: {links}") # Old log
            print(f"Retrieved {len(project_items)} project detail items from CORDIS API.")


        except requests.exceptions.Timeout:
            print(f"Error: CORDIS API request timed out for URL: {base_api_url} with params: {params}")
        except requests.exceptions.HTTPError as e:
            print(f"Error: CORDIS API request failed with HTTP status {e.response.status_code} for URL: {response.url if 'response' in locals() and hasattr(response, 'url') else base_api_url}")
        except requests.exceptions.RequestException as e:
            print(f"Error during CORDIS API request: {e}")
        except ET.ParseError as e:
            print(f"Error parsing CORDIS API XML response: {e}. Content snippet: {response.content[:500] if 'response' in locals() else 'N/A'}")
        except Exception as e: # Catch any other unexpected errors
            print(f"An unexpected error occurred in _search_cordis: {e}")
            
        # return links # Old return
        return project_items # New return
    
    # def _retrieve_project_data(self, links: List[str], max_projects: int = 5) -> List[Dict[str, Any]]: # Old signature
    def _retrieve_project_data(self, project_items: List[Dict[str, Any]], max_projects: int = 5) -> List[Dict[str, Any]]: # New signature
        """
        Process project data from CORDIS search results.
        
        Args:
            project_items: List of project data dictionaries from CORDIS API search.
            max_projects: Maximum number of projects to process
            
        Returns:
            List[Dict]: List of structured project data dictionaries
        """
        # project_data = [] # Old name
        processed_project_data: List[Dict[str, Any]] = [] # New name for clarity
        
        # for link in links[:max_projects]: # Old loop
        for item in project_items[:max_projects]: # New loop, item is a dict
            try:
                # xml_link = link + "?format=xml" # Removed
                # xml_content = self._fetch_webpage_content(xml_link) # Removed
                # if xml_content: # Removed
                #     project_json = self._extract_project_data(xml_content) # Old call, passing XML string
                #     project_data.append(project_json)
                
                # New logic: item is already a dictionary with project details
                if item and isinstance(item, dict): # Ensure item is a valid dictionary
                    extracted_data = self._extract_project_data(item) # Pass the project dictionary
                    processed_project_data.append(extracted_data)
                else:
                    print(f"Skipping invalid or empty project item: {item}")

            except Exception as e:
                rcn = item.get('rcn', 'Unknown RCN') if isinstance(item, dict) else 'Unknown RCN'
                # print(f"Error retrieving project data from {link}: {e}") # Old log
                print(f"Error processing project data for RCN {rcn}: {e}")
        
        # return project_data
        return processed_project_data
    
    # def _fetch_webpage_content(self, url: str) -> Optional[str]:
    #     """
    #     Retrieve webpage content as an XML string.
    #     
    #     Args:
    #         url: The URL to fetch
    #     """
    #     try:
    #         response = requests.get(url, timeout=30)
    #         response.raise_for_status()
    #         return response.text
    #     except requests.exceptions.RequestException as e:
    #         print(f"Error fetching {url}: {e}")
    #         return None
    
    def _extract_project_data(self, project_json: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract and structure project data from a CORDIS project item dictionary.
        
        Args:
            project_json: A dictionary containing raw project data from CORDIS API search result item.
        
        Returns:
            Dict[str, Any]: A dictionary with structured project data.
        """
        data = {}
        data['rcn'] = project_json.get('rcn', 'N/A')
        data['title'] = project_json.get('title', 'N/A')
        data['acronym'] = project_json.get('acronym', 'N/A')
        
        # Objective: Prioritize 'description', then 'teaser'
        data['objective'] = project_json.get('description', project_json.get('teaser', 'N/A'))
        if not data['objective'] or data['objective'] == 'N/A': # If both are empty or N/A
             data['objective'] = project_json.get('teaser', 'N/A')


        data['startDate'] = self._format_date(project_json.get('startDate', 'N/A'))
        data['endDate'] = self._format_date(project_json.get('endDate', 'N/A'))
        
        # Budget: Attempt to extract from 'totalCost'. This field must be requested in _search_cordis.
        raw_budget = project_json.get('totalCost', project_json.get('projectTotalCost')) # Trying common field names
        if isinstance(raw_budget, dict) and 'value' in raw_budget: # e.g., {'value': 10000, 'currency': 'EUR'}
            currency = raw_budget.get('currency', '')
            value = raw_budget.get('value')
            data['budget'] = f"{value} {currency}".strip() if value is not None else 'N/A'
        elif raw_budget is not None:
            data['budget'] = str(raw_budget)
        else:
            data['budget'] = 'N/A'

        # Keywords: Attempt to extract from 'keywords'. This field must be requested in _search_cordis.
        keywords_data = project_json.get('keywords', project_json.get('subjects')) # Trying common field names
        if isinstance(keywords_data, list):
            data['keywords'] = ', '.join(str(k.get('label', k) if isinstance(k, dict) else k) for k in keywords_data if k)
        elif isinstance(keywords_data, str):
            data['keywords'] = keywords_data
        elif isinstance(keywords_data, dict): # e.g. if keywords are {'keyword': ['a', 'b']}
            data['keywords'] = ', '.join(str(v) for v in keywords_data.values() if v)
        else:
            data['keywords'] = 'N/A'
            
        # Call Info: From 'programme'
        programme_info_list = project_json.get('programme')
        if isinstance(programme_info_list, list) and len(programme_info_list) > 0:
            # Assuming the first programme in the list is the primary one
            main_programme = programme_info_list[0]
            if isinstance(main_programme, dict):
                call_title = main_programme.get('title', '')
                call_code = main_programme.get('code', '')
                data['call_info'] = f"{call_title} ({call_code})".strip() if call_title or call_code else 'N/A'
            else:
                data['call_info'] = str(main_programme) # Fallback if structure is unexpected
        else:
            data['call_info'] = 'N/A'
            
        # Participants:
        # The 'fields' list in _search_cordis requests 'legalName' and 'country',
        # which might be for the coordinator.
        # If a 'participants' array is available in project_json, use that.
        participant_names_list = []
        participant_countries_list = []

        participants_data = project_json.get('participants')
        if isinstance(participants_data, list):
            for p_entry in participants_data:
                if isinstance(p_entry, dict):
                    name = p_entry.get('name', p_entry.get('legalName', p_entry.get('shortName')))
                    country = p_entry.get('country') 
                    if isinstance(country, dict): # e.g. country: {'isoCode': 'ES', 'label': 'Spain'}
                        country = country.get('isoCode', country.get('label'))
                    
                    if name:
                        participant_names_list.append(str(name))
                    if country:
                        participant_countries_list.append(str(country))
        
        if not participant_names_list: # Fallback to top-level coordinator info if no 'participants' array
            coordinator_name = project_json.get('legalName') # 'legalName' is in the API fields list
            if coordinator_name:
                participant_names_list.append(str(coordinator_name))
            
            coordinator_country = project_json.get('country') # 'country' is in the API fields list
            if isinstance(coordinator_country, dict): # e.g. country: {'isoCode': 'ES', 'label': 'Spain'}
                 coordinator_country = coordinator_country.get('isoCode', coordinator_country.get('label'))
            if coordinator_country:
                participant_countries_list.append(str(coordinator_country))

        data['participant_names'] = participant_names_list
        data['participant_countries'] = participant_countries_list
        
        # Publications (example, improve if more details on 'authors' structure are known)
        # The 'fields' list includes 'authors', 'journalTitle', etc.
        authors_list = project_json.get('authors') # This could be a list of strings or dicts
        pub_details = []
        if isinstance(authors_list, list) and authors_list:
            # Assuming authors_list could be complex, e.g. list of author dicts or strings
            author_names = []
            for author_entry in authors_list:
                if isinstance(author_entry, dict):
                    author_names.append(author_entry.get('fullName', author_entry.get('name', 'Unknown Author')))
                else:
                    author_names.append(str(author_entry))
            if author_names:
                 pub_details.append(f"Authors: {', '.join(author_names)}")

        journal_title = project_json.get('journalTitle')
        if journal_title:
            pub_details.append(f"Journal: {journal_title}")
        
        published_year = project_json.get('publishedYear')
        if published_year:
            pub_details.append(f"Year: {published_year}")

        data['publications'] = '. '.join(pub_details) if pub_details else 'N/A'
            
        return data
    
    def _format_date(self, date_str: str) -> str:
        """
        Convert a date string to a standard format (YYYY-MM-DD).
        
        Args:
            date_str: The original date string
        
        Returns:
            str: The formatted date string
        """
        try:
            # Assuming the input date is in the format YYYY-MM-DD or similar
            # This can be adjusted based on the actual date formats encountered
            return "-".join(date_str.split("-")[:3])
        except Exception as e:
            print(f"Error formatting date '{date_str}': {e}")
            return date_str  # Return original string if formatting fails
    
    def _generate_answer(self, role: str, user_text: str, project_data: List[Dict[str, Any]]) -> str:
        """
        Generate a final answer using the configured AI provider based on retrieved data.
        
        Args:
            role: The system role
            user_text: The original user question
            project_data: List of structured project data dictionaries
            
        Returns:
            str: The AI-generated answer
        """
        if not project_data:
            return "I couldn't find any specific project data relevant to your query in the CORDIS database. You might want to try rephrasing your question or making it more specific."

        # Prepare the project data as a string for the prompt
        project_data_str_parts = []
        for i, proj in enumerate(project_data):
            # Ensure all expected keys are present, providing defaults if not
            title = proj.get('title', 'N/A')
            objective = proj.get('objective', 'N/A') # This should now be populated by _extract_project_data
            keywords = proj.get('keywords', 'N/A') # This too
            call_info = proj.get('call_info', 'N/A') # And this
            budget = proj.get('budget', 'N/A') # And this
            # Format participants
            participants_str = "N/A"
            participant_names = proj.get('participant_names', [])
            participant_countries = proj.get('participant_countries', [])

            if participant_names:
                if participant_countries and len(participant_names) == len(participant_countries):
                    participants_details = [f"{name} ({country})" for name, country in zip(participant_names, participant_countries)]
                    participants_str = ", ".join(participants_details)
                else:
                    participants_str = "Names: " + ", ".join(participant_names)
                    if participant_countries:
                        participants_str += "; Countries: " + ", ".join(participant_countries)
            elif participant_countries: # Only countries available
                 participants_str = "Countries: " + ", ".join(participant_countries)
            
            rcn = proj.get('rcn', 'N/A')

            project_data_str_parts.append(
                f"Project {i+1} (RCN: {rcn}):\\n"
                f"  Title: {title}\\n"
                f"  Objective: {objective}\\n"
                f"  Keywords: {keywords}\\n"
                f"  Call Info: {call_info}\\n"
                f"  Budget: {budget}\\n"
                f"  Participants: {participants_str}\\n" # Use the new formatted string
            )
        project_data_str = "\\n".join(project_data_str_parts)

        # Construct the prompt for the AI
        prompt_content = f"""Based on the following information retrieved from the CORDIS database about European research projects, please answer the user\'s question.

User Question: {user_text}

Retrieved Project Data:
{project_data_str}

Please synthesize this information to provide a comprehensive answer. If the retrieved data is insufficient, acknowledge that.
"""
        
        answer = ""
        if self.ai_provider == "openai":
            # print(f"Prompt for AI (OpenAI): {prompt_content}") # For debugging
            completion = self.openai_client.chat.completions.create(
                model=self.openai_model_name, # Use configured OpenAI model
                messages=[
                    {"role": "system", "content": role},
                    {"role": "user", "content": prompt_content}
                ],
                temperature=0.7
            )
            answer = completion.choices[0].message.content
        elif self.ai_provider == "gemini":
            if not self.gemini_client:
                raise RuntimeError("Gemini client not initialized.")
            answer = ""
            try:
                gemini_contents = [
                    types.Content(role="user", parts=[types.Part.from_text(text=role)]),
                    types.Content(role="model", parts=[types.Part.from_text(text="Okay, I understand my role. I will answer the user\\\'s question based on the provided CORDIS project data.")]),
                    types.Content(role="user", parts=[types.Part.from_text(text=prompt_content)])
                ]
                
                # Use types.GenerateContentConfig
                gen_config = types.GenerateContentConfig(
                    temperature=0.7
                    # You can add other parameters here if needed, e.g., response_mime_type="text/plain"
                    # based on the Gemini API documentation or your specific requirements.
                )
                
                # Change parameter name from generation_config to config
                response = self.gemini_client.models.generate_content(
                    model=self.gemini_model_name,
                    contents=gemini_contents,
                    config=gen_config 
                )
                answer = response.text # Get text from the non-streaming response
            except Exception as e:
                print(f"Error during Gemini answer generation: {e}")
                # Re-raise the exception to get more detailed traceback for debugging
                raise
        return answer

if __name__ == "__main__":

    # Test with OpenAI (default)
    # print("--- Testing with OpenAI ---")
    # rag_system_openai = CordisRAG() # Defaults to OpenAI, will use OPENAI_API_KEY from .env
    # test_question_openai = "What are some projects related to renewable energy?"
    # print(f"Testing CordisRAG (OpenAI) with question: '{test_question_openai}'")
    # try:
    #     ai_response_openai = rag_system_openai.get_ai_response(test_question_openai)
    #     print("\nAI Response (OpenAI):")
    #     print(ai_response_openai)
    # except Exception as e:
    #     print(f"An error occurred during the OpenAI test: {e}")

    print("\n--- Testing with Gemini ---")
    # Test with Gemini, allowing model specification
    try:
        # User can specify the model like: "gemini-2.5-flash-lite-preview-06-17"
        # If not specified, __init__ default is used.
        rag_system_gemini = CordisRAG(ai_provider="gemini") # Will use GEMINI_API_KEY from .env
                                                            # and default gemini_model_name from __init__
        
        test_question_gemini = "Tell me about projects focusing on solar panel efficiency."
        print(f"Testing CordisRAG (Gemini with model {rag_system_gemini.gemini_model_name}) with question: '{test_question_gemini}'")
        
        ai_response_gemini = rag_system_gemini.get_ai_response(test_question_gemini)
        print("\nAI Response (Gemini):")
        print(ai_response_gemini)
    except ValueError as ve: # Catch API key errors from __init__
        print(f"Skipping Gemini test due to configuration error: {ve}")
    except ImportError:
        print("Skipping Gemini test: google.generativeai library not found. Please install it.")
    except AttributeError as ae: # Catch issues like model not found if genai.GenerativeModel fails
        print(f"Skipping Gemini test due to attribute error (possibly model name issue): {ae}")
    except Exception as e:
        print(f"An error occurred during the Gemini test: {e}")

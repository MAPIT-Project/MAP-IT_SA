import os
import requests
import re
import json
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from datetime import datetime
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
import openai
from google import genai as google_genai_sdk
from google.genai import types
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import psycopg2
from psycopg2.extras import DictCursor
import psycopg2.pool
from urllib.parse import urlparse

# Load environment variables
load_dotenv()

class CordisRAG:
    """
    Retrieval-Augmented Generation system for European research projects using CORDIS database.
    V5: Enhanced with local Supabase database integration for faster and richer data retrieval.
    """
    def __init__(self, openai_api_key: Optional[str] = None, gemini_api_key: Optional[str] = None, 
                 ai_provider: str = "openai", 
                 openai_model_name: str = "gpt-4-turbo",
                 gemini_model_name: str = "gemini-2.5-flash-preview-05-20",
                 use_local_db: bool = False,
                 database_url: Optional[str] = None):
        load_dotenv()
        self.ai_provider = ai_provider.lower()
        self.openai_model_name = openai_model_name
        self.gemini_model_name = gemini_model_name
        self.gemini_client = None
        self.use_local_db = use_local_db
        
        # Database connection setup
        self.db_pool = None
        if self.use_local_db:
            db_url = database_url or os.getenv("DATABASE_URL")
            if not db_url:
                raise ValueError("DATABASE_URL required when use_local_db=True")
            
            try:
                self.db_pool = psycopg2.pool.SimpleConnectionPool(
                    1, 20,  # min and max connections
                    db_url
                )
                print("✅ Local database connection established")
            except Exception as e:
                print(f"❌ Database connection failed: {e}")
                raise
        
        # Performance optimizations
        self._xml_cache = {}  # Cache for XML data
        self._api_cache = {}  # Cache for API responses
        self._db_cache = {}  # Cache for database queries
        self._cache_ttl = 3600  # Cache TTL in seconds (1 hour)
        
        if self.ai_provider == "openai":
            used_openai_api_key = openai_api_key if openai_api_key else os.getenv("OPENAI_API_KEY")
            if not used_openai_api_key:
                raise ValueError("OpenAI API key not provided and not found in .env file.")
            self.openai_client = openai.OpenAI(api_key=used_openai_api_key)
        elif self.ai_provider == "gemini":
            used_gemini_api_key = gemini_api_key if gemini_api_key else os.getenv("GEMINI_API_KEY")
            if not used_gemini_api_key:
                raise ValueError("Gemini API key not provided and not found in .env file.")
            self.gemini_client = google_genai_sdk.Client(api_key=used_gemini_api_key)
        else:
            raise ValueError("Invalid AI provider specified. Choose 'openai' or 'gemini'.")

    def get_ai_response(self, question: str, max_projects_to_process: int = 5, max_cordis_results: int = 10) -> str:
        """
        Get AI response with performance monitoring and optimizations.
        V5: Enhanced with local database option for faster data retrieval.
        """
        total_start_time = time.time()
        data_source = "Local Database" if self.use_local_db else "CORDIS API"
        print(f"🚀 Starting V5 RAG pipeline using {data_source} for: '{question}'")
        
        # 1. Phase 1: Query extraction
        phase_start = time.time()
        role, quest = self._get_phase1_prompt(question)
        queries, end_flag, new_query_keys, rerank_criteria, problem_text, next_pass = self._extract_queries(role, quest)
        print(f"📝 Phase 1 (Query extraction) completed in {time.time() - phase_start:.2f}s")
        
        if end_flag:
            return problem_text
        
        # 2. Phase 2: Data retrieval (Database or API)
        phase_start = time.time()
        if self.use_local_db:
            project_data = self._search_local_database(queries, max_results=max_projects_to_process)
            print(f"🔍 Phase 2 (Local DB search) completed in {time.time() - phase_start:.2f}s")
        else:
            project_items = self._search_cordis_api(queries, max_results=max_cordis_results)
            print(f"🔍 Phase 2 (CORDIS API search) completed in {time.time() - phase_start:.2f}s")
            
            # 3. Phase 3: Project data extraction (only for API mode)
            phase_start = time.time()
            project_data = [self._extract_project_data(item) for item in project_items[:max_projects_to_process]]
            print(f"📊 Phase 3 (Data extraction) completed in {time.time() - phase_start:.2f}s")
            
            # 3.5. Phase 3.5: XML enrichment (only for API mode)
            phase_start = time.time()
            project_data = self._enrich_with_xml_data(project_data)
            print(f"🔗 Phase 3.5 (XML enrichment) completed in {time.time() - phase_start:.2f}s")
        
        # 4. Phase 4: Reranking (if rerank_criteria present)
        if rerank_criteria:
            phase_start = time.time()
            project_data = self._rerank_projects(project_data, rerank_criteria, question, role)
            print(f"📈 Phase 4 (Reranking) completed in {time.time() - phase_start:.2f}s")
        
        # 5. Phase 6: Final answer generation
        phase_start = time.time()
        answer = self._generate_answer(role, question, project_data)
        print(f"💬 Phase 6 (Answer generation) completed in {time.time() - phase_start:.2f}s")
        
        total_time = time.time() - total_start_time
        print(f"✅ V5 RAG pipeline completed in {total_time:.2f}s total")
        
        return answer

    def _get_phase1_prompt(self, question: str):
        # Get current year for dynamic date calculations
        current_year = datetime.now().year
        recent_start_year = current_year - 5  # Last 5 years for "recent"
        very_recent_start_year = current_year - 3  # Last 3 years for "very recent"
        
        role = f"""You play the role of a knowledge steward providing the research and innovation landscape of European research projects. You are helping to a research university or an institute or an SME to retrieve information from the corpus of previously funded projects.\nYour scenario of operation is as such: \nYou will receive a question. In two stages, you will extract queries from the question. At the first stage, you should extract queries to retrieve information about projects required to answer the questions. The first stage queries will be input to a xml retriever. Those queries may be names, topics, keywords, used methods and technologies of the projects as well as information related to participating organizations such as name, country, type, employees of the institution. Occasionally, they may be start and end dates of projects, a budget interval or the name or the acronym of a project call. \nThe xml retriever will retrieve xml files that include information about the project. If needed, at the second stage, according to information in the xml files and the information need in the question, you will generate new queries called second stage queries that will be input to the xml retriever.\n"""
        quest = f"""The question is: {question}\nPlease generate the first stage queries to input to the xml retriever to retrieve projects relevant to the question. Generate neat and concise textual boolean queries. If you need to connect parts of a query with \"AND\" connective, give them as seperate queries. That is, for example, if the query is \"word1 AND word2\" give it as two seperate queries which are \"word1\" and \"word2\". However, if you need to connect parts of a query with \"OR\" do it explicitly and do not seperate it into multiple queries in this case. That is, \"word1 OR word2\" should be given as it is. If you generate a query about dates, write in the format \"startDate>YEAR-MONTH-DAY\", \"endDate>YEAR-MONTH-DAY\". If you generate a query about budget, write in the format totalCost<1000, totalCost>1000. Moreover, if you are given a budget interval between a lower limit ans an upper limit write it in the format totalCost=lower-upper. Note that date related information need may be implicitly given in the question using words recent, first, last etc. For \"recent\" projects, use startDate>{recent_start_year}-01-01 to capture projects from the last 5 years. For \"very recent\" or \"latest\", use startDate>{very_recent_start_year}-01-01. If you generate a query about geographical locations, only include country names and no other region names, no continent names, no city names. Explain your reasoning step by step. Do not provide the queries or relations about which you are not sure. Give your whole answer in xml format with the fields <explanation>,<code>, and <problem>. Your explanations goes under <explanations> key. Under the <code> key, provide the queries as a Python code in the following format:   \"\nqueries= []\nproblem_flag = False\nrequired_information = []\nsecond_stage = False\nranking_criteria = []\n\"\nGive the code in exactly five lines.\nThe list of queries you generate must be at the first line. For example, for the question \"What are the machine learning related projects?\" the queries list should be queries = [machine learning OR deep learning OR artificial intelligence] and for the question \"What are the machine learning related projects in which Turkish organizations participated?\" the queries list should be queries = [machine learning OR deep learning OR artificial intelligence, Turkey]. Please keep this format. Note that queries should only include texts in natural language and the logical connectives. If no queries can be generated from given information, take the question itself as the query and add it to the queries list. Also, do not forget that queries include be names, topics, keywords, used methods and technologies of the projects as well as information related to participating organizations such as name, country, type of the institution. Occasionally, they may include start and end dates of projects, a budget interval or the name or the acronym of a project call. \nYou must put the variable problem_flag to the second line. problem_flag is set True when such a problem in the question exists: If you think the question is problematic (irrelevant or too general or we have no sufficient information sources to answer the question), set the problem_flag to True in the code and write the problem and a brief guiding sentence for the user under the <problem> key.\nThe third line must contain the list named required_information. As you know, some xml files each holding information about one project will be returned as response to your queries. Remember that a second stage of query generation may be run on those xml files. So, decide that which type of information should be requested by the second stage queries. Fill the required_information list with the required types of information that will be asked in second stage queries. Available types of information are project_objective, keywords, call_scope, budget, participant_names, participant_properties, participant_countries. For example, if countries of participants are required for the second stage, the required information list should be required_information = [participant_countries]. Note that if you need participant related information for the second stage, you generally do not need keywords. If no second stage queries are required, leave required_information list empty and set second_stage=False.\nAs underlined in the provided code format, the variable second_stage must be at the fourth line.\nAt the fifth line we have another list named ranking_criteria. Let me explain the expected content of that list: After the first stage retrieval, we need to rerank the retrieved documents according to some criteria such that documents that are more relevant to the intention of the first stage retrieval ranked higher. However, those reranking criteria should be dynamically inferred from the question. Those criteria are expected to be recency, novelty, actuality, impact, success, budget level of the project. For example, when the first stage retrieval aims to retrieve most successful projects, the ranking criteria may be ranking_criteria = [high success, high impact, high novelty, high budget], similarly, when the the first stage retrieval aims to retrieve the most unrealistic projects, the ranking criteria may be ranking_criteria = [low success, low impact, low actuality]. Beware that in the list of queries you are absolutely forbidden to include reranking criteria such as impact, success, recency, novelty, actuality! For example, [\"machine learning\", \"successful\"] and [\"machine learning\", \"high impact\"] are WRONG queries because they respectively include the words \"successful\" and \"high impact\". \nBefore giving the code, in your explanation, explicitly write to what the question reduced after receiving the reply to the first stage query. That reduced question will help you to formulate the required information and to decide the ranking criteria. Then, try justifying that reduced question. If you cannot justify it, change the reduced question. Additionally, in your explanation, explicitly write why you selected the required information types and ranking criteria you selected. Then, try justifying your selections, and change the selections you cannot justify.\nThe last remarks for you: Firstly, if the second stage will not require retrieving information about projects or participating organizations, such a second stage is unnecessary. So, for such cases, set second_stage = False. Secondly, if the question asks for filtering projects according to a metric such as best projects, worst projects, most successful projects etc., we need some restrictions about the projects we will consider, such as topics, participants, keywords etc. of the project. Otherwise we cannot reply the question, so you must set problem_flag = True in this case. Also, if the only restriction is about time, we can still not reply, so set problem_flag = True in this case as well. However, if the set of projects we should consider is sufficiently restricted, then we can devise a metric to answer such questions, therefore, no problem in this case. For example, we cannot answer the questions most successful project or the most successful recent project, however, we can answer the questions of most successful machine learning project or the most successful project conducted in Central Europe in the last decade. \n"""
        return role, quest

    def _extract_queries(self, role, quest):
        ans = ""
        if self.ai_provider == "openai":
            completion = self.openai_client.chat.completions.create(
                model=self.openai_model_name,
                messages=[{"role": "system", "content": role}, {"role": "user", "content": quest}],
                temperature=0.9,
                n=3
            )
            ans = completion.choices[1].message.content
        elif self.ai_provider == "gemini":
            gemini_contents = [
                types.Content(role="user", parts=[types.Part.from_text(text=role)]),
                types.Content(role="user", parts=[types.Part.from_text(text=quest)])
            ]
            gen_config = types.GenerateContentConfig(temperature=0.9)
            response = self.gemini_client.models.generate_content(
                model=self.gemini_model_name,
                contents=gemini_contents,
                config=gen_config
            )
            ans = response.text
        ans_lines = ans.splitlines()
        end_flag = False
        queries = []
        next_pass = 0
        new_query_keys = []
        rerank_criteria = []
        problem_text = ""
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
                # Handle cases where words might already be quoted or have mixed quoting
                # First, normalize by removing any existing quotes
                lst_normalized = lst.replace('"', '').replace("'", '')
                # Then add proper quotes around bare words
                lst_quoted = re.sub(r'\b([a-zA-Z_][a-zA-Z0-9_\s]*)\b', r'"\1"', lst_normalized)
                # Clean up any double quotes that might result from the replacement
                lst_quoted = re.sub(r'""', r'"', lst_quoted)
                try:
                    rerank_criteria = eval(lst_quoted)
                except (SyntaxError, ValueError) as e:
                    print(f"Error parsing rerank_criteria: {lst} -> {lst_quoted}. Error: {e}")
                    rerank_criteria = []  # Fallback to empty list
        if end_flag:
            full = "\n".join(ans_lines)
            if "<problem>" in full and "</problem>" in full:
                start_problem = full.index("<problem>")
                end_problem = full.index("</problem>")
                problem_text = full[start_problem+9:end_problem]
            else:
                problem_text = "Problematic question."
        return queries, end_flag, new_query_keys, rerank_criteria, problem_text, next_pass

    def _search_cordis_api(self, queries: List[str], max_results: int = 10) -> List[Dict[str, Any]]:
        # Create cache key from queries
        cache_key = self._get_cache_key((queries, max_results))
        
        # Check cache first
        cached_result = self._get_from_cache(self._api_cache, cache_key)
        if cached_result is not None:
            print(f"Using cached CORDIS API results for {len(queries)} queries")
            return cached_result
        
        base_api_url = "https://cordis.europa.eu/api/search/results"
        api_q_parts = ["contenttype='project'", "language='en'"]
        for item_query in queries:
            item_query_stripped = item_query.strip()
            if not item_query_stripped:
                continue
            item_query_lower = item_query_stripped.lower()
            if "startdate" in item_query_lower or "enddate" in item_query_lower:
                date_str = item_query_stripped.replace(" ", "")
                api_q_parts.append(date_str)
            else:
                or_terms = item_query_stripped.split("OR")
                valid_or_terms = [term.strip() for term in or_terms if term.strip()]
                if not valid_or_terms:
                    continue
                quoted_or_terms = [f"'{term}'" for term in valid_or_terms]
                keyword_part = f"({ ' OR '.join(quoted_or_terms) })"
                api_q_parts.append(keyword_part)
        q_value = " AND ".join(api_q_parts)
        updated_fields = "uri,rcn,title,id,code,startDate,endDate,teaser,contentUpdateDate,name,relatedImage,availableLanguages,language,issueNumber,issueDate,issueLastDate,issue,archivedDate,acronym,legalName,euCode,city,country,iprPrefix,iprNumber,iprDate,iprAwarded,description,doi,journalTitle,journalNumber,publishedYear,publishedPages,authors,periodFrom,periodTo,webItem,webItem/_ATTR_*,physUrl,webLink,webLink/_ATTR_*,physUrl,frameworkProgramme,totalCost,projectTotalCost,keywords,subjects,programme,participants"
        params = {
            "q": q_value,
            "p": 1,
            "num": max_results,
            "srt": "Relevance:decreasing",
            # "fields": updated_fields,
            "archived": "true"
        }
        project_items: List[Dict[str, Any]] = []
        try:
            start_time = time.time()
            response = requests.get(base_api_url, params=params, timeout=30)
            response.raise_for_status()
            json_data = response.json()
            if json_data.get("payload") and "results" in json_data["payload"]:
                project_items = json_data["payload"]["results"]
            
            # Cache the result
            self._set_cache(self._api_cache, cache_key, project_items)
            print(f"CORDIS API call completed in {time.time() - start_time:.2f}s, found {len(project_items)} projects")
            
        except Exception as e:
            print(f"CORDIS API error: {e}")
        return project_items

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
        
        # Enhanced project ID extraction for better link generation
        project_id = None
        # Try multiple possible ID fields
        for id_field in ['id', 'reference', 'projectId', 'code']:
            if project_json.get(id_field):
                project_id = str(project_json[id_field]).strip()
                if project_id and project_id != 'N/A':
                    break
        
        # If still no ID, try extracting from URI field
        if not project_id or project_id == 'N/A':
            uri = project_json.get('uri', '')
            if uri and '/project/id/' in uri:
                try:
                    project_id = uri.split('/project/id/')[-1].split('/')[0]
                except:
                    pass
        
        data['id'] = project_id if project_id else 'N/A'
        data['title'] = project_json.get('title', 'N/A')
        data['acronym'] = project_json.get('acronym', 'N/A')
        data['objective'] = project_json.get('description', project_json.get('teaser', 'N/A'))
        if not data['objective'] or data['objective'] == 'N/A':
            data['objective'] = project_json.get('teaser', 'N/A')
        data['startDate'] = project_json.get('startDate', 'N/A')
        data['endDate'] = project_json.get('endDate', 'N/A')
        raw_budget = project_json.get('totalCost', project_json.get('projectTotalCost'))
        if isinstance(raw_budget, dict) and 'value' in raw_budget:
            currency = raw_budget.get('currency', '')
            value = raw_budget.get('value')
            data['budget'] = f"{value} {currency}".strip() if value is not None else 'N/A'
        elif raw_budget is not None:
            data['budget'] = str(raw_budget)
        else:
            data['budget'] = 'N/A'
        keywords_data = project_json.get('keywords', project_json.get('subjects'))
        if isinstance(keywords_data, list):
            data['keywords'] = ', '.join(str(k.get('label', k) if isinstance(k, dict) else k) for k in keywords_data if k)
        elif isinstance(keywords_data, str):
            data['keywords'] = keywords_data
        elif isinstance(keywords_data, dict):
            data['keywords'] = ', '.join(str(v) for v in keywords_data.values() if v)
        else:
            data['keywords'] = 'N/A'
        programme_info_list = project_json.get('programme')
        if isinstance(programme_info_list, list) and len(programme_info_list) > 0:
            main_programme = programme_info_list[0]
            if isinstance(main_programme, dict):
                call_title = main_programme.get('title', '')
                call_code = main_programme.get('code', '')
                data['call_info'] = f"{call_title} ({call_code})".strip() if call_title or call_code else 'N/A'
            else:
                data['call_info'] = str(main_programme)
        else:
            data['call_info'] = 'N/A'
        participant_names_list = []
        participant_countries_list = []
        participants_data = project_json.get('participants')
        if isinstance(participants_data, list):
            for p_entry in participants_data:
                if isinstance(p_entry, dict):
                    name = p_entry.get('name', p_entry.get('legalName', p_entry.get('shortName')))
                    country = p_entry.get('country')
                    if isinstance(country, dict):
                        country = country.get('isoCode', country.get('label'))
                    if name:
                        participant_names_list.append(str(name))
                    if country:
                        participant_countries_list.append(str(country))
        if not participant_names_list:
            coordinator_name = project_json.get('legalName')
            if coordinator_name:
                participant_names_list.append(str(coordinator_name))
            coordinator_country = project_json.get('country')
            if isinstance(coordinator_country, dict):
                coordinator_country = coordinator_country.get('isoCode', coordinator_country.get('label'))
            if coordinator_country:
                participant_countries_list.append(str(coordinator_country))
        data['participant_names'] = participant_names_list
        data['participant_countries'] = participant_countries_list
        authors_list = project_json.get('authors')
        pub_details = []
        if isinstance(authors_list, list) and authors_list:
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

    def _rerank_projects(self, project_data, rerank_criteria, question, role):
        # Use LLM to rerank the projects according to rerank_criteria
        prompt_rerank = f"""The json files embodying detailed information about relevant projects are as follows: {json.dumps(project_data)}. Sort those json files according to the criteria in the following list: {rerank_criteria}. Also consider their relevance to the question and their overall importance. At the very and of your response, give the sorted list of titles of projects. The titles you put in the list must be written totally the same as they are in the json file. The list must be a python list named sorted_titles and must be in a single line. Except that list, do not include any python code in your reponse."""
        if self.ai_provider == "openai":
            reranker_response = self.openai_client.chat.completions.create(
                model=self.openai_model_name,
                messages=[{"role": "system", "content": role}, {"role": "user", "content": prompt_rerank}]
            )
            reranked_str = reranker_response.choices[0].message.content
        elif self.ai_provider == "gemini":
            gemini_contents = [
                types.Content(role="user", parts=[types.Part.from_text(text=role)]),
                types.Content(role="user", parts=[types.Part.from_text(text=prompt_rerank)])
            ]
            gen_config = types.GenerateContentConfig(temperature=0.7)
            response = self.gemini_client.models.generate_content(
                model=self.gemini_model_name,
                contents=gemini_contents,
                config=gen_config
            )
            reranked_str = response.text
        offset = reranked_str.index("sorted_titles =") if "sorted_titles =" in reranked_str else reranked_str.index("sorted_titles=")
        start_idx_lst = reranked_str.index("[",offset)
        end_idx_lst = reranked_str.index("]",start_idx_lst)
        sorted_titles = eval(reranked_str[start_idx_lst:end_idx_lst+1].strip())
        reranked_jsons = []
        for title in sorted_titles[:5]:
            for proj in project_data:
                if set(proj["title"].lower().split(" ")) - {"", " "} == set(title.lower().split(" ")) - {"", " "}:
                    reranked_jsons.append(proj)
        return reranked_jsons

    def _generate_answer(self, role: str, user_text: str, project_data: List[Dict[str, Any]]) -> str:
        if not project_data:
            return "I couldn't find any specific project data relevant to your query in the CORDIS database. You might want to try rephrasing your question or making it more specific."
        
        # Create enhanced project summaries with richer database information
        project_summaries = []
        for proj in project_data:
            title = proj.get('title', 'Unknown Title')
            acronym = proj.get('acronym', '')
            objective = proj.get('objective', 'No description available')
            budget = proj.get('budget', 'Budget not specified')
            start_date = proj.get('startDate', 'Unknown')
            end_date = proj.get('endDate', 'Unknown')
            participant_names = proj.get('participant_names', [])
            participant_countries = proj.get('participant_countries', [])
            project_id = proj.get('id', '')
            rcn = proj.get('rcn', '')
            status = proj.get('status', 'N/A')
            
            # Enhanced information from local database
            coordinator_name = proj.get('coordinator_name', 'N/A')
            coordinator_country = proj.get('coordinator_country', 'N/A')
            participant_count = proj.get('participant_count', 0)
            country_count = proj.get('country_count', 0)
            sme_count = proj.get('sme_count', 0)
            framework_programme = proj.get('frameworkProgramme', 'N/A')
            funding_scheme = proj.get('fundingScheme', 'N/A')
            
            # Format duration and status info
            duration_info = ""
            if start_date != 'Unknown' and end_date != 'Unknown':
                duration_info = f" ({start_date} to {end_date})"
            elif start_date != 'Unknown':
                duration_info = f" (started {start_date})"
            
            if status != 'N/A':
                duration_info += f" - Status: {status}"
            
            # Enhanced participant information
            participant_info = ""
            if coordinator_name != 'N/A':
                coord_info = f"Coordinated by {coordinator_name}"
                if coordinator_country != 'N/A':
                    coord_info += f" ({coordinator_country})"
                participant_info += coord_info + ". "
            
            if participant_count > 0:
                participant_info += f"Total of {participant_count} participants"
                if country_count > 1:
                    participant_info += f" from {country_count} countries"
                if sme_count > 0:
                    participant_info += f" (including {sme_count} SMEs)"
                participant_info += ". "
            
            if participant_countries:
                unique_countries = list(set(participant_countries))
                if len(unique_countries) <= 5:
                    participant_info += f"Countries involved: {', '.join(unique_countries)}. "
                else:
                    participant_info += f"Countries involved: {', '.join(unique_countries[:5])} and {len(unique_countries) - 5} others. "
            
            # Create enhanced project summary
            summary = f"**{title}"
            if acronym and acronym != 'N/A':
                summary += f" ({acronym})"
            summary += f"**{duration_info}"
            
            # Add programme information
            if framework_programme != 'N/A':
                summary += f"\n🏛️ **Programme:** {framework_programme}"
                if funding_scheme != 'N/A' and funding_scheme != framework_programme:
                    summary += f" ({funding_scheme})"
            
            # Add budget information
            if budget != 'N/A' and budget != 'Budget not specified':
                summary += f"\n💰 **Budget:** {budget}"
            
            # Enhanced CORDIS project link generation with multiple fallbacks
            cordis_link_added = False
            
            # Primary: Use project ID if available
            if project_id and project_id != 'N/A' and project_id.strip():
                summary += f"\n🔗 **CORDIS Link:** https://cordis.europa.eu/project/id/{project_id}"
                cordis_link_added = True
            
            # Fallback 1: Use RCN if project ID not available
            elif rcn and rcn != 'N/A' and rcn.strip():
                summary += f"\n🔗 **CORDIS Link:** https://cordis.europa.eu/project/rcn/{rcn}"
                cordis_link_added = True
            
            # Fallback 2: Search link using project title
            elif title and title != 'Unknown Title':
                search_title = title.replace(' ', '+').replace('&', '%26')
                summary += f"\n🔍 **CORDIS Search:** https://cordis.europa.eu/search?q={search_title}&p=1&num=10&srt=Relevance:decreasing"
                cordis_link_added = True
            
            # Always add a link, even if we have to use a general search
            if not cordis_link_added:
                summary += f"\n🔍 **CORDIS Database:** https://cordis.europa.eu/search"
            
            # Add project description
            summary += f"\n{objective[:350]}{'...' if len(objective) > 350 else ''}"
            
            # Add enhanced participant information
            if participant_info:
                summary += f"\n🤝 **Consortium:** {participant_info}"
            
            project_summaries.append(summary)
        
        # Create enhanced prompt for answer generation
        projects_text = "\n\n".join(project_summaries)
        data_source_note = "from our local CORDIS database" if self.use_local_db else "from the CORDIS database"
        
        prompt = f"""Based on the following European research projects {data_source_note}, provide a comprehensive and natural answer to the user's question.

User Question: {user_text}

Retrieved Projects:
{projects_text}

Instructions:
- Write in a conversational, informative tone
- ALWAYS mention and include the provided CORDIS links for each project you discuss
- Highlight the most relevant and recent projects first
- Include specific details like budgets, timelines, consortium information, and key participants when available
- Note the programme frameworks (Horizon, FP7, etc.) when relevant
- Group related projects or identify common themes
- If projects span different time periods, organize chronologically or by relevance
- Make sure to preserve all the 🔗 CORDIS Link and 🔍 CORDIS Search links in your response
- Encourage users to visit the CORDIS links for more detailed information
- Don't use template phrases like "Stage 1" or "based on retrieved information"
- Write as if you're explaining to someone interested in the research landscape
- If any projects seem outdated for the question (e.g., asking for "recent" but showing old projects), acknowledge this
- Leverage the rich consortium information (coordinators, SME participation, geographic distribution) when relevant
"""
        
        if self.ai_provider == "openai":
            response = self.openai_client.chat.completions.create(
                model=self.openai_model_name,
                messages=[{"role": "system", "content": role}, {"role": "user", "content": prompt}],
                temperature=0.25  # Lower temperature for more accurate, factual responses
            )
            final_response = response.choices[0].message.content
        elif self.ai_provider == "gemini":
            gemini_contents = [
                types.Content(role="user", parts=[types.Part.from_text(text=role)]),
                types.Content(role="user", parts=[types.Part.from_text(text=prompt)])
            ]
            gen_config = types.GenerateContentConfig(temperature=0.25)  # Lower temperature for more accurate, factual responses
            response = self.gemini_client.models.generate_content(
                model=self.gemini_model_name,
                contents=gemini_contents,
                config=gen_config
            )
            final_response = response.text
        
        # Ensure links are preserved in the final response
        if 'cordis.europa.eu' not in final_response.lower():
            final_response += f"\n\n🔗 **For more detailed information, visit the CORDIS database:** https://cordis.europa.eu/"
        
        return final_response

    def _search_local_database(self, queries: List[str], max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Search local Supabase database for projects matching the queries.
        Returns enriched project data directly from the database.
        """
        # Create cache key from queries
        cache_key = self._get_cache_key((queries, max_results, "local_db"))
        
        # Check cache first
        cached_result = self._get_from_cache(self._db_cache, cache_key)
        if cached_result is not None:
            print(f"Using cached database results for {len(queries)} queries")
            return cached_result
        
        if not self.db_pool:
            print("❌ Database pool not available")
            return []
        
        try:
            conn = self.db_pool.getconn()
            cursor = conn.cursor(cursor_factory=DictCursor)
            
            # Build SQL query from text queries
            where_conditions = []
            params = []
            
            for query in queries:
                query = query.strip()
                if not query:
                    continue
                    
                # Handle OR conditions within a single query
                or_terms = [term.strip() for term in query.split('OR') if term.strip()]
                if len(or_terms) > 1:
                    # Multiple OR terms
                    or_conditions = []
                    for term in or_terms:
                        or_conditions.append("""
                            (LOWER(p.title) LIKE LOWER(%s) OR 
                             LOWER(p.objective) LIKE LOWER(%s) OR 
                             LOWER(p.acronym) LIKE LOWER(%s) OR
                             LOWER(p.topics) LIKE LOWER(%s))
                        """)
                        term_pattern = f"%{term}%"
                        params.extend([term_pattern, term_pattern, term_pattern, term_pattern])
                    
                    where_conditions.append(f"({' OR '.join(or_conditions)})")
                else:
                    # Single term
                    term = or_terms[0] if or_terms else query
                    where_conditions.append("""
                        (LOWER(p.title) LIKE LOWER(%s) OR 
                         LOWER(p.objective) LIKE LOWER(%s) OR 
                         LOWER(p.acronym) LIKE LOWER(%s) OR
                         LOWER(p.topics) LIKE LOWER(%s) OR
                         LOWER(o.name) LIKE LOWER(%s) OR
                         LOWER(o.country) LIKE LOWER(%s))
                    """)
                    term_pattern = f"%{term}%"
                    params.extend([term_pattern, term_pattern, term_pattern, term_pattern, term_pattern, term_pattern])
            
            # Base SQL query with comprehensive joins and aggregations
            # Fixed: Use correct case-sensitive column name "projectID" instead of "projectid"
            sql_query = f"""
                SELECT DISTINCT
                    p.id,
                    p.acronym,
                    p.title,
                    p.objective,
                    p."startDate",
                    p."endDate",
                    p."totalCost",
                    p."ecMaxContribution",
                    p.status,
                    p.topics,
                    p."frameworkProgramme",
                    p."fundingScheme",
                    p."legalBasis",
                    p.rcn,
                    p."grantDoi",
                    -- Aggregated organization data
                    COUNT(o."organisationID") as participant_count,
                    ARRAY_AGG(DISTINCT o.name) FILTER (WHERE o.name IS NOT NULL) as participant_names,
                    ARRAY_AGG(DISTINCT o.country) FILTER (WHERE o.country IS NOT NULL) as participant_countries,
                    ARRAY_AGG(DISTINCT o.city) FILTER (WHERE o.city IS NOT NULL) as participant_cities,
                    SUM(o."ecContribution") as total_ec_contribution,
                    SUM(o."netEcContribution") as total_net_ec_contribution,
                    SUM(o."totalCost") as total_org_costs,
                    -- Coordinator information (role = 'coordinator')
                    MAX(CASE WHEN o.role = 'coordinator' THEN o.name END) as coordinator_name,
                    MAX(CASE WHEN o.role = 'coordinator' THEN o.country END) as coordinator_country,
                    MAX(CASE WHEN o.role = 'coordinator' THEN o.city END) as coordinator_city,
                    -- SME information
                    COUNT(CASE WHEN o."SME" = true THEN 1 END) as sme_count,
                    -- Geographic diversity
                    COUNT(DISTINCT o.country) as country_count,
                    ARRAY_AGG(DISTINCT o."nutsCode") FILTER (WHERE o."nutsCode" IS NOT NULL) as nuts_codes,
                    -- Organization types
                    ARRAY_AGG(DISTINCT o."activityType") FILTER (WHERE o."activityType" IS NOT NULL) as activity_types
                FROM projects p
                LEFT JOIN organizations o ON p.id = o."projectID"
                WHERE p.id IS NOT NULL
            """
            
            if where_conditions:
                sql_query += f" AND ({' AND '.join(where_conditions)})"
            
            sql_query += f"""
                GROUP BY p.id, p.acronym, p.title, p.objective, p."startDate", p."endDate", 
                         p."totalCost", p."ecMaxContribution", p.status, p.topics, 
                         p."frameworkProgramme", p."fundingScheme", p."legalBasis", p.rcn, p."grantDoi"
                ORDER BY p."startDate" DESC NULLS LAST, p."totalCost" DESC NULLS LAST
                LIMIT %s
            """
            params.append(max_results)
            
            start_time = time.time()
            cursor.execute(sql_query, params)
            rows = cursor.fetchall()
            
            # Convert to structured project data
            projects = []
            for row in rows:
                project = self._format_db_project_data(dict(row))
                projects.append(project)
            
            # Cache the result
            self._set_cache(self._db_cache, cache_key, projects)
            
            print(f"Database query completed in {time.time() - start_time:.2f}s, found {len(projects)} projects")
            
            return projects
            
        except Exception as e:
            print(f"Database query error: {e}")
            return []
        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                self.db_pool.putconn(conn)

    def _format_db_project_data(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format database row into standardized project data structure.
        Enhanced with richer database information.
        """
        # Format dates - fix case sensitivity
        start_date = row.get('startDate', 'Unknown')
        if start_date and start_date != 'Unknown':
            start_date = str(start_date)
        
        end_date = row.get('endDate', 'Unknown')
        if end_date and end_date != 'Unknown':
            end_date = str(end_date)
        
        # Format budget information with enhanced details - fix case sensitivity
        total_cost = row.get('totalCost')
        ec_contribution = row.get('ecMaxContribution')
        total_ec_contrib = row.get('total_ec_contribution')
        total_net_ec_contrib = row.get('total_net_ec_contribution')
        
        budget_parts = []
        if total_cost:
            budget_parts.append(f"Total Cost: €{total_cost:,.2f}")
        if ec_contribution:
            budget_parts.append(f"EU Contribution: €{ec_contribution:,.2f}")
        if total_ec_contrib and total_ec_contrib != ec_contribution:
            budget_parts.append(f"Partners EU Funding: €{total_ec_contrib:,.2f}")
        
        budget_str = " | ".join(budget_parts) if budget_parts else 'N/A'
        
        # Enhanced participant information
        participant_names = row.get('participant_names') or []
        participant_countries = row.get('participant_countries') or []
        participant_cities = row.get('participant_cities') or []
        
        # Remove None values and ensure lists
        participant_names = [str(name) for name in participant_names if name]
        participant_countries = [str(country) for country in participant_countries if country]
        participant_cities = [str(city) for city in participant_cities if city]
        
        # Enhanced project data structure - fix case sensitivity
        project_data = {
            'id': str(row.get('id', 'N/A')),
            'rcn': row.get('rcn', 'N/A'),
            'title': row.get('title', 'N/A'),
            'acronym': row.get('acronym', 'N/A'),
            'objective': row.get('objective', 'N/A'),
            'startDate': start_date,
            'endDate': end_date,
            'budget': budget_str,
            'status': row.get('status', 'N/A'),
            'topics': row.get('topics', 'N/A'),
            'frameworkProgramme': row.get('frameworkProgramme', 'N/A'),
            'fundingScheme': row.get('fundingScheme', 'N/A'),
            'legalBasis': row.get('legalBasis', 'N/A'),
            'grantDoi': row.get('grantDoi', 'N/A'),
            
            # Enhanced participant information
            'participant_names': participant_names,
            'participant_countries': participant_countries,
            'participant_cities': participant_cities,
            'participant_count': row.get('participant_count', 0),
            'country_count': row.get('country_count', 0),
            'sme_count': row.get('sme_count', 0),
            
            # Coordinator information
            'coordinator_name': row.get('coordinator_name', 'N/A'),
            'coordinator_country': row.get('coordinator_country', 'N/A'),
            'coordinator_city': row.get('coordinator_city', 'N/A'),
            
            # Geographic and activity information
            'nuts_codes': row.get('nuts_codes') or [],
            'activity_types': row.get('activity_types') or [],
            
            # Financial details
            'total_ec_contribution': total_ec_contrib,
            'total_net_ec_contribution': total_net_ec_contrib,
            'total_org_costs': row.get('total_org_costs'),
            
            # Additional metadata
            'keywords': row.get('topics', 'N/A'),  # Use topics as keywords for compatibility
            'call_info': f"{row.get('frameworkProgramme', 'N/A')} - {row.get('fundingScheme', 'N/A')}",
            'publications': 'N/A'  # Not available in current schema
        }
        
        return project_data

    def _rerank_projects(self, project_data, rerank_criteria, question, role):
        # Use LLM to rerank the projects according to rerank_criteria
        prompt_rerank = f"""The json files embodying detailed information about relevant projects are as follows: {json.dumps(project_data)}. Sort those json files according to the criteria in the following list: {rerank_criteria}. Also consider their relevance to the question and their overall importance. At the very and of your response, give the sorted list of titles of projects. The titles you put in the list must be written totally the same as they are in the json file. The list must be a python list named sorted_titles and must be in a single line. Except that list, do not include any python code in your reponse."""
        if self.ai_provider == "openai":
            reranker_response = self.openai_client.chat.completions.create(
                model=self.openai_model_name,
                messages=[{"role": "system", "content": role}, {"role": "user", "content": prompt_rerank}]
            )
            reranked_str = reranker_response.choices[0].message.content
        elif self.ai_provider == "gemini":
            gemini_contents = [
                types.Content(role="user", parts=[types.Part.from_text(text=role)]),
                types.Content(role="user", parts=[types.Part.from_text(text=prompt_rerank)])
            ]
            gen_config = types.GenerateContentConfig(temperature=0.7)
            response = self.gemini_client.models.generate_content(
                model=self.gemini_model_name,
                contents=gemini_contents,
                config=gen_config
            )
            reranked_str = response.text
        offset = reranked_str.index("sorted_titles =") if "sorted_titles =" in reranked_str else reranked_str.index("sorted_titles=")
        start_idx_lst = reranked_str.index("[",offset)
        end_idx_lst = reranked_str.index("]",start_idx_lst)
        sorted_titles = eval(reranked_str[start_idx_lst:end_idx_lst+1].strip())
        reranked_jsons = []
        for title in sorted_titles[:5]:
            for proj in project_data:
                if set(proj["title"].lower().split(" ")) - {"", " "} == set(title.lower().split(" ")) - {"", " "}:
                    reranked_jsons.append(proj)
        return reranked_jsons

    def _generate_answer(self, role: str, user_text: str, project_data: List[Dict[str, Any]]) -> str:
        if not project_data:
            return "I couldn't find any specific project data relevant to your query in the CORDIS database. You might want to try rephrasing your question or making it more specific."
        
        # Create enhanced project summaries with richer database information
        project_summaries = []
        for proj in project_data:
            title = proj.get('title', 'Unknown Title')
            acronym = proj.get('acronym', '')
            objective = proj.get('objective', 'No description available')
            budget = proj.get('budget', 'Budget not specified')
            start_date = proj.get('startDate', 'Unknown')
            end_date = proj.get('endDate', 'Unknown')
            participant_names = proj.get('participant_names', [])
            participant_countries = proj.get('participant_countries', [])
            project_id = proj.get('id', '')
            rcn = proj.get('rcn', '')
            status = proj.get('status', 'N/A')
            
            # Enhanced information from local database
            coordinator_name = proj.get('coordinator_name', 'N/A')
            coordinator_country = proj.get('coordinator_country', 'N/A')
            participant_count = proj.get('participant_count', 0)
            country_count = proj.get('country_count', 0)
            sme_count = proj.get('sme_count', 0)
            framework_programme = proj.get('frameworkProgramme', 'N/A')
            funding_scheme = proj.get('fundingScheme', 'N/A')
            
            # Format duration and status info
            duration_info = ""
            if start_date != 'Unknown' and end_date != 'Unknown':
                duration_info = f" ({start_date} to {end_date})"
            elif start_date != 'Unknown':
                duration_info = f" (started {start_date})"
            
            if status != 'N/A':
                duration_info += f" - Status: {status}"
            
            # Enhanced participant information
            participant_info = ""
            if coordinator_name != 'N/A':
                coord_info = f"Coordinated by {coordinator_name}"
                if coordinator_country != 'N/A':
                    coord_info += f" ({coordinator_country})"
                participant_info += coord_info + ". "
            
            if participant_count > 0:
                participant_info += f"Total of {participant_count} participants"
                if country_count > 1:
                    participant_info += f" from {country_count} countries"
                if sme_count > 0:
                    participant_info += f" (including {sme_count} SMEs)"
                participant_info += ". "
            
            if participant_countries:
                unique_countries = list(set(participant_countries))
                if len(unique_countries) <= 5:
                    participant_info += f"Countries involved: {', '.join(unique_countries)}. "
                else:
                    participant_info += f"Countries involved: {', '.join(unique_countries[:5])} and {len(unique_countries) - 5} others. "
            
            # Create enhanced project summary
            summary = f"**{title}"
            if acronym and acronym != 'N/A':
                summary += f" ({acronym})"
            summary += f"**{duration_info}"
            
            # Add programme information
            if framework_programme != 'N/A':
                summary += f"\n🏛️ **Programme:** {framework_programme}"
                if funding_scheme != 'N/A' and funding_scheme != framework_programme:
                    summary += f" ({funding_scheme})"
            
            # Add budget information
            if budget != 'N/A' and budget != 'Budget not specified':
                summary += f"\n💰 **Budget:** {budget}"
            
            # Enhanced CORDIS project link generation with multiple fallbacks
            cordis_link_added = False
            
            # Primary: Use project ID if available
            if project_id and project_id != 'N/A' and project_id.strip():
                summary += f"\n🔗 **CORDIS Link:** https://cordis.europa.eu/project/id/{project_id}"
                cordis_link_added = True
            
            # Fallback 1: Use RCN if project ID not available
            elif rcn and rcn != 'N/A' and rcn.strip():
                summary += f"\n🔗 **CORDIS Link:** https://cordis.europa.eu/project/rcn/{rcn}"
                cordis_link_added = True
            
            # Fallback 2: Search link using project title
            elif title and title != 'Unknown Title':
                search_title = title.replace(' ', '+').replace('&', '%26')
                summary += f"\n🔍 **CORDIS Search:** https://cordis.europa.eu/search?q={search_title}&p=1&num=10&srt=Relevance:decreasing"
                cordis_link_added = True
            
            # Always add a link, even if we have to use a general search
            if not cordis_link_added:
                summary += f"\n🔍 **CORDIS Database:** https://cordis.europa.eu/search"
            
            # Add project description
            summary += f"\n{objective[:350]}{'...' if len(objective) > 350 else ''}"
            
            # Add enhanced participant information
            if participant_info:
                summary += f"\n🤝 **Consortium:** {participant_info}"
            
            project_summaries.append(summary)
        
        # Create enhanced prompt for answer generation
        projects_text = "\n\n".join(project_summaries)
        data_source_note = "from our local CORDIS database" if self.use_local_db else "from the CORDIS database"
        
        prompt = f"""Based on the following European research projects {data_source_note}, provide a comprehensive and natural answer to the user's question.

User Question: {user_text}

Retrieved Projects:
{projects_text}

Instructions:
- Write in a conversational, informative tone
- ALWAYS mention and include the provided CORDIS links for each project you discuss
- Highlight the most relevant and recent projects first
- Include specific details like budgets, timelines, consortium information, and key participants when available
- Note the programme frameworks (Horizon, FP7, etc.) when relevant
- Group related projects or identify common themes
- If projects span different time periods, organize chronologically or by relevance
- Make sure to preserve all the 🔗 CORDIS Link and 🔍 CORDIS Search links in your response
- Encourage users to visit the CORDIS links for more detailed information
- Don't use template phrases like "Stage 1" or "based on retrieved information"
- Write as if you're explaining to someone interested in the research landscape
- If any projects seem outdated for the question (e.g., asking for "recent" but showing old projects), acknowledge this
- Leverage the rich consortium information (coordinators, SME participation, geographic distribution) when relevant
"""
        
        if self.ai_provider == "openai":
            response = self.openai_client.chat.completions.create(
                model=self.openai_model_name,
                messages=[{"role": "system", "content": role}, {"role": "user", "content": prompt}],
                temperature=0.25  # Lower temperature for more accurate, factual responses
            )
            final_response = response.choices[0].message.content
        elif self.ai_provider == "gemini":
            gemini_contents = [
                types.Content(role="user", parts=[types.Part.from_text(text=role)]),
                types.Content(role="user", parts=[types.Part.from_text(text=prompt)])
            ]
            gen_config = types.GenerateContentConfig(temperature=0.25)  # Lower temperature for more accurate, factual responses
            response = self.gemini_client.models.generate_content(
                model=self.gemini_model_name,
                contents=gemini_contents,
                config=gen_config
            )
            final_response = response.text
        
        # Ensure links are preserved in the final response
        if 'cordis.europa.eu' not in final_response.lower():
            final_response += f"\n\n🔗 **For more detailed information, visit the CORDIS database:** https://cordis.europa.eu/"
        
        return final_response

    def _search_local_database(self, queries: List[str], max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Search local Supabase database for projects matching the queries.
        Returns enriched project data directly from the database.
        """
        # Create cache key from queries
        cache_key = self._get_cache_key((queries, max_results, "local_db"))
        
        # Check cache first
        cached_result = self._get_from_cache(self._db_cache, cache_key)
        if cached_result is not None:
            print(f"Using cached database results for {len(queries)} queries")
            return cached_result
        
        if not self.db_pool:
            print("❌ Database pool not available")
            return []
        
        try:
            conn = self.db_pool.getconn()
            cursor = conn.cursor(cursor_factory=DictCursor)
            
            # Build SQL query from text queries
            where_conditions = []
            params = []
            
            for query in queries:
                query = query.strip()
                if not query:
                    continue
                    
                # Handle OR conditions within a single query
                or_terms = [term.strip() for term in query.split('OR') if term.strip()]
                if len(or_terms) > 1:
                    # Multiple OR terms
                    or_conditions = []
                    for term in or_terms:
                        or_conditions.append("""
                            (LOWER(p.title) LIKE LOWER(%s) OR 
                             LOWER(p.objective) LIKE LOWER(%s) OR 
                             LOWER(p.acronym) LIKE LOWER(%s) OR
                             LOWER(p.topics) LIKE LOWER(%s))
                        """)
                        term_pattern = f"%{term}%"
                        params.extend([term_pattern, term_pattern, term_pattern, term_pattern])
                    
                    where_conditions.append(f"({' OR '.join(or_conditions)})")
                else:
                    # Single term
                    term = or_terms[0] if or_terms else query
                    where_conditions.append("""
                        (LOWER(p.title) LIKE LOWER(%s) OR 
                         LOWER(p.objective) LIKE LOWER(%s) OR 
                         LOWER(p.acronym) LIKE LOWER(%s) OR
                         LOWER(p.topics) LIKE LOWER(%s) OR
                         LOWER(o.name) LIKE LOWER(%s) OR
                         LOWER(o.country) LIKE LOWER(%s))
                    """)
                    term_pattern = f"%{term}%"
                    params.extend([term_pattern, term_pattern, term_pattern, term_pattern, term_pattern, term_pattern])
            
            # Base SQL query with comprehensive joins and aggregations
            # Fixed: Use correct case-sensitive column name "projectID" instead of "projectid"
            sql_query = f"""
                SELECT DISTINCT
                    p.id,
                    p.acronym,
                    p.title,
                    p.objective,
                    p."startDate",
                    p."endDate",
                    p."totalCost",
                    p."ecMaxContribution",
                    p.status,
                    p.topics,
                    p."frameworkProgramme",
                    p."fundingScheme",
                    p."legalBasis",
                    p.rcn,
                    p."grantDoi",
                    -- Aggregated organization data
                    COUNT(o."organisationID") as participant_count,
                    ARRAY_AGG(DISTINCT o.name) FILTER (WHERE o.name IS NOT NULL) as participant_names,
                    ARRAY_AGG(DISTINCT o.country) FILTER (WHERE o.country IS NOT NULL) as participant_countries,
                    ARRAY_AGG(DISTINCT o.city) FILTER (WHERE o.city IS NOT NULL) as participant_cities,
                    SUM(o."ecContribution") as total_ec_contribution,
                    SUM(o."netEcContribution") as total_net_ec_contribution,
                    SUM(o."totalCost") as total_org_costs,
                    -- Coordinator information (role = 'coordinator')
                    MAX(CASE WHEN o.role = 'coordinator' THEN o.name END) as coordinator_name,
                    MAX(CASE WHEN o.role = 'coordinator' THEN o.country END) as coordinator_country,
                    MAX(CASE WHEN o.role = 'coordinator' THEN o.city END) as coordinator_city,
                    -- SME information
                    COUNT(CASE WHEN o."SME" = true THEN 1 END) as sme_count,
                    -- Geographic diversity
                    COUNT(DISTINCT o.country) as country_count,
                    ARRAY_AGG(DISTINCT o."nutsCode") FILTER (WHERE o."nutsCode" IS NOT NULL) as nuts_codes,
                    -- Organization types
                    ARRAY_AGG(DISTINCT o."activityType") FILTER (WHERE o."activityType" IS NOT NULL) as activity_types
                FROM projects p
                LEFT JOIN organizations o ON p.id = o."projectID"
                WHERE p.id IS NOT NULL
            """
            
            if where_conditions:
                sql_query += f" AND ({' AND '.join(where_conditions)})"
            
            sql_query += f"""
                GROUP BY p.id, p.acronym, p.title, p.objective, p."startDate", p."endDate", 
                         p."totalCost", p."ecMaxContribution", p.status, p.topics, 
                         p."frameworkProgramme", p."fundingScheme", p."legalBasis", p.rcn, p."grantDoi"
                ORDER BY p."startDate" DESC NULLS LAST, p."totalCost" DESC NULLS LAST
                LIMIT %s
            """
            params.append(max_results)
            
            start_time = time.time()
            cursor.execute(sql_query, params)
            rows = cursor.fetchall()
            
            # Convert to structured project data
            projects = []
            for row in rows:
                project = self._format_db_project_data(dict(row))
                projects.append(project)
            
            # Cache the result
            self._set_cache(self._db_cache, cache_key, projects)
            
            print(f"Database query completed in {time.time() - start_time:.2f}s, found {len(projects)} projects")
            
            return projects
            
        except Exception as e:
            print(f"Database query error: {e}")
            return []
        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                self.db_pool.putconn(conn)

    def _format_db_project_data(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format database row into standardized project data structure.
        Enhanced with richer database information.
        """
        # Format dates - fix case sensitivity
        start_date = row.get('startDate', 'Unknown')
        if start_date and start_date != 'Unknown':
            start_date = str(start_date)
        
        end_date = row.get('endDate', 'Unknown')
        if end_date and end_date != 'Unknown':
            end_date = str(end_date)
        
        # Format budget information with enhanced details - fix case sensitivity
        total_cost = row.get('totalCost')
        ec_contribution = row.get('ecMaxContribution')
        total_ec_contrib = row.get('total_ec_contribution')
        total_net_ec_contrib = row.get('total_net_ec_contribution')
        
        budget_parts = []
        if total_cost:
            budget_parts.append(f"Total Cost: €{total_cost:,.2f}")
        if ec_contribution:
            budget_parts.append(f"EU Contribution: €{ec_contribution:,.2f}")
        if total_ec_contrib and total_ec_contrib != ec_contribution:
            budget_parts.append(f"Partners EU Funding: €{total_ec_contrib:,.2f}")
        
        budget_str = " | ".join(budget_parts) if budget_parts else 'N/A'
        
        # Enhanced participant information
        participant_names = row.get('participant_names') or []
        participant_countries = row.get('participant_countries') or []
        participant_cities = row.get('participant_cities') or []
        
        # Remove None values and ensure lists
        participant_names = [str(name) for name in participant_names if name]
        participant_countries = [str(country) for country in participant_countries if country]
        participant_cities = [str(city) for city in participant_cities if city]
        
        # Enhanced project data structure - fix case sensitivity
        project_data = {
            'id': str(row.get('id', 'N/A')),
            'rcn': row.get('rcn', 'N/A'),
            'title': row.get('title', 'N/A'),
            'acronym': row.get('acronym', 'N/A'),
            'objective': row.get('objective', 'N/A'),
            'startDate': start_date,
            'endDate': end_date,
            'budget': budget_str,
            'status': row.get('status', 'N/A'),
            'topics': row.get('topics', 'N/A'),
            'frameworkProgramme': row.get('frameworkProgramme', 'N/A'),
            'fundingScheme': row.get('fundingScheme', 'N/A'),
            'legalBasis': row.get('legalBasis', 'N/A'),
            'grantDoi': row.get('grantDoi', 'N/A'),
            
            # Enhanced participant information
            'participant_names': participant_names,
            'participant_countries': participant_countries,
            'participant_cities': participant_cities,
            'participant_count': row.get('participant_count', 0),
            'country_count': row.get('country_count', 0),
            'sme_count': row.get('sme_count', 0),
            
            # Coordinator information
            'coordinator_name': row.get('coordinator_name', 'N/A'),
            'coordinator_country': row.get('coordinator_country', 'N/A'),
            'coordinator_city': row.get('coordinator_city', 'N/A'),
            
            # Geographic and activity information
            'nuts_codes': row.get('nuts_codes') or [],
            'activity_types': row.get('activity_types') or [],
            
            # Financial details
            'total_ec_contribution': total_ec_contrib,
            'total_net_ec_contribution': total_net_ec_contrib,
            'total_org_costs': row.get('total_org_costs'),
            
            # Additional metadata
            'keywords': row.get('topics', 'N/A'),  # Use topics as keywords for compatibility
            'call_info': f"{row.get('frameworkProgramme', 'N/A')} - {row.get('fundingScheme', 'N/A')}",
            'publications': 'N/A'  # Not available in current schema
        }
        
        return project_data

    def _rerank_projects(self, project_data, rerank_criteria, question, role):
        # Use LLM to rerank the projects according to rerank_criteria
        prompt_rerank = f"""The json files embodying detailed information about relevant projects are as follows: {json.dumps(project_data)}. Sort those json files according to the criteria in the following list: {rerank_criteria}. Also consider their relevance to the question and their overall importance. At the very and of your response, give the sorted list of titles of projects. The titles you put in the list must be written totally the same as they are in the json file. The list must be a python list named sorted_titles and must be in a single line. Except that list, do not include any python code in your reponse."""
        if self.ai_provider == "openai":
            reranker_response = self.openai_client.chat.completions.create(
                model=self.openai_model_name,
                messages=[{"role": "system", "content": role}, {"role": "user", "content": prompt_rerank}]
            )
            reranked_str = reranker_response.choices[0].message.content
        elif self.ai_provider == "gemini":
            gemini_contents = [
                types.Content(role="user", parts=[types.Part.from_text(text=role)]),
                types.Content(role="user", parts=[types.Part.from_text(text=prompt_rerank)])
            ]
            gen_config = types.GenerateContentConfig(temperature=0.7)
            response = self.gemini_client.models.generate_content(
                model=self.gemini_model_name,
                contents=gemini_contents,
                config=gen_config
            )
            reranked_str = response.text
        offset = reranked_str.index("sorted_titles =") if "sorted_titles =" in reranked_str else reranked_str.index("sorted_titles=")
        start_idx_lst = reranked_str.index("[",offset)
        end_idx_lst = reranked_str.index("]",start_idx_lst)
        sorted_titles = eval(reranked_str[start_idx_lst:end_idx_lst+1].strip())
        reranked_jsons = []
        for title in sorted_titles[:5]:
            for proj in project_data:
                if set(proj["title"].lower().split(" ")) - {"", " "} == set(title.lower().split(" ")) - {"", " "}:
                    reranked_jsons.append(proj)
        return reranked_jsons

    def _generate_answer(self, role: str, user_text: str, project_data: List[Dict[str, Any]]) -> str:
        if not project_data:
            return "I couldn't find any specific project data relevant to your query in the CORDIS database. You might want to try rephrasing your question or making it more specific."
        
        # Create enhanced project summaries with richer database information
        project_summaries = []
        for proj in project_data:
            title = proj.get('title', 'Unknown Title')
            acronym = proj.get('acronym', '')
            objective = proj.get('objective', 'No description available')
            budget = proj.get('budget', 'Budget not specified')
            start_date = proj.get('startDate', 'Unknown')
            end_date = proj.get('endDate', 'Unknown')
            participant_names = proj.get('participant_names', [])
            participant_countries = proj.get('participant_countries', [])
            project_id = proj.get('id', '')
            rcn = proj.get('rcn', '')
            status = proj.get('status', 'N/A')
            
            # Enhanced information from local database
            coordinator_name = proj.get('coordinator_name', 'N/A')
            coordinator_country = proj.get('coordinator_country', 'N/A')
            participant_count = proj.get('participant_count', 0)
            country_count = proj.get('country_count', 0)
            sme_count = proj.get('sme_count', 0)
            framework_programme = proj.get('frameworkProgramme', 'N/A')
            funding_scheme = proj.get('fundingScheme', 'N/A')
            
            # Format duration and status info
            duration_info = ""
            if start_date != 'Unknown' and end_date != 'Unknown':
                duration_info = f" ({start_date} to {end_date})"
            elif start_date != 'Unknown':
                duration_info = f" (started {start_date})"
            
            if status != 'N/A':
                duration_info += f" - Status: {status}"
            
            # Enhanced participant information
            participant_info = ""
            if coordinator_name != 'N/A':
                coord_info = f"Coordinated by {coordinator_name}"
                if coordinator_country != 'N/A':
                    coord_info += f" ({coordinator_country})"
                participant_info += coord_info + ". "
            
            if participant_count > 0:
                participant_info += f"Total of {participant_count} participants"
                if country_count > 1:
                    participant_info += f" from {country_count} countries"
                if sme_count > 0:
                    participant_info += f" (including {sme_count} SMEs)"
                participant_info += ". "
            
            if participant_countries:
                unique_countries = list(set(participant_countries))
                if len(unique_countries) <= 5:
                    participant_info += f"Countries involved: {', '.join(unique_countries)}. "
                else:
                    participant_info += f"Countries involved: {', '.join(unique_countries[:5])} and {len(unique_countries) - 5} others. "
            
            # Create enhanced project summary
            summary = f"**{title}"
            if acronym and acronym != 'N/A':
                summary += f" ({acronym})"
            summary += f"**{duration_info}"
            
            # Add programme information
            if framework_programme != 'N/A':
                summary += f"\n🏛️ **Programme:** {framework_programme}"
                if funding_scheme != 'N/A' and funding_scheme != framework_programme:
                    summary += f" ({funding_scheme})"
            
            # Add budget information
            if budget != 'N/A' and budget != 'Budget not specified':
                summary += f"\n💰 **Budget:** {budget}"
            
            # Enhanced CORDIS project link generation with multiple fallbacks
            cordis_link_added = False
            
            # Primary: Use project ID if available
            if project_id and project_id != 'N/A' and project_id.strip():
                summary += f"\n🔗 **CORDIS Link:** https://cordis.europa.eu/project/id/{project_id}"
                cordis_link_added = True
            
            # Fallback 1: Use RCN if project ID not available
            elif rcn and rcn != 'N/A' and rcn.strip():
                summary += f"\n🔗 **CORDIS Link:** https://cordis.europa.eu/project/rcn/{rcn}"
                cordis_link_added = True
            
            # Fallback 2: Search link using project title
            elif title and title != 'Unknown Title':
                search_title = title.replace(' ', '+').replace('&', '%26')
                summary += f"\n🔍 **CORDIS Search:** https://cordis.europa.eu/search?q={search_title}&p=1&num=10&srt=Relevance:decreasing"
                cordis_link_added = True
            
            # Always add a link, even if we have to use a general search
            if not cordis_link_added:
                summary += f"\n🔍 **CORDIS Database:** https://cordis.europa.eu/search"
            
            # Add project description
            summary += f"\n{objective[:350]}{'...' if len(objective) > 350 else ''}"
            
            # Add enhanced participant information
            if participant_info:
                summary += f"\n🤝 **Consortium:** {participant_info}"
            
            project_summaries.append(summary)
        
        # Create enhanced prompt for answer generation
        projects_text = "\n\n".join(project_summaries)
        data_source_note = "from our local CORDIS database" if self.use_local_db else "from the CORDIS database"
        
        prompt = f"""Based on the following European research projects {data_source_note}, provide a comprehensive and natural answer to the user's question.

User Question: {user_text}

Retrieved Projects:
{projects_text}

Instructions:
- Write in a conversational, informative tone
- ALWAYS mention and include the provided CORDIS links for each project you discuss
- Highlight the most relevant and recent projects first
- Include specific details like budgets, timelines, consortium information, and key participants when available
- Note the programme frameworks (Horizon, FP7, etc.) when relevant
- Group related projects or identify common themes
- If projects span different time periods, organize chronologically or by relevance
- Make sure to preserve all the 🔗 CORDIS Link and 🔍 CORDIS Search links in your response
- Encourage users to visit the CORDIS links for more detailed information
- Don't use template phrases like "Stage 1" or "based on retrieved information"
- Write as if you're explaining to someone interested in the research landscape
- If any projects seem outdated for the question (e.g., asking for "recent" but showing old projects), acknowledge this
- Leverage the rich consortium information (coordinators, SME participation, geographic distribution) when relevant
"""
        
        if self.ai_provider == "openai":
            response = self.openai_client.chat.completions.create(
                model=self.openai_model_name,
                messages=[{"role": "system", "content": role}, {"role": "user", "content": prompt}],
                temperature=0.25  # Lower temperature for more accurate, factual responses
            )
            final_response = response.choices[0].message.content
        elif self.ai_provider == "gemini":
            gemini_contents = [
                types.Content(role="user", parts=[types.Part.from_text(text=role)]),
                types.Content(role="user", parts=[types.Part.from_text(text=prompt)])
            ]
            gen_config = types.GenerateContentConfig(temperature=0.25)  # Lower temperature for more accurate, factual responses
            response = self.gemini_client.models.generate_content(
                model=self.gemini_model_name,
                contents=gemini_contents,
                config=gen_config
            )
            final_response = response.text
        
        # Ensure links are preserved in the final response
        if 'cordis.europa.eu' not in final_response.lower():
            final_response += f"\n\n🔗 **For more detailed information, visit the CORDIS database:** https://cordis.europa.eu/"
        
        return final_response

    def _get_cache_key(self, data: Any) -> str:
        """Generate a cache key from data."""
        return str(hash(str(data)))
    
    def _is_cache_valid(self, timestamp: float) -> bool:
        """Check if cache entry is still valid."""
        return time.time() - timestamp < self._cache_ttl
    
    def _get_from_cache(self, cache_dict: Dict, key: str) -> Optional[Any]:
        """Get item from cache if valid."""
        if key in cache_dict:
            data, timestamp = cache_dict[key]
            if self._is_cache_valid(timestamp):
                return data
            else:
                # Remove expired entry
                del cache_dict[key]
        return None
    
    def _set_cache(self, cache_dict: Dict, key: str, data: Any) -> None:
        """Set item in cache with timestamp."""
        cache_dict[key] = (data, time.time())

    def _enrich_with_xml_data(self, project_data_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Enrich project data with additional information from XML endpoints using concurrent processing.
        This adds detailed data that's not available through the basic CORDIS API search.
        
        Performance optimized with:
        - Concurrent XML requests using ThreadPoolExecutor
        - Caching for repeated project IDs
        - Early timeout for slow requests
        
        Args:
            project_data_list: List of project dictionaries from CORDIS API
            
        Returns:
            List of enriched project dictionaries with additional XML data
        """
        if not project_data_list:
            return project_data_list
        
        print(f"Starting XML enrichment for {len(project_data_list)} projects...")
        start_time = time.time()
        
        enriched_projects = []
        
        # Prepare data for concurrent processing
        xml_tasks = []
        for i, project_data in enumerate(project_data_list):
            project_id = project_data.get('id', '')
            if not project_id or project_id == 'N/A':
                project_id = project_data.get('reference', '')
            
            if project_id and project_id != 'N/A':
                xml_tasks.append((i, project_data, project_id))
            else:
                # No valid ID, add without enrichment
                enriched_projects.append(project_data)
        
        # Process XML enrichment concurrently
        xml_results = {}
        if xml_tasks:
            with ThreadPoolExecutor(max_workers=5) as executor:  # Limit concurrent requests
                future_to_task = {
                    executor.submit(self._fetch_single_xml_data, project_id): (i, project_data)
                    for i, project_data, project_id in xml_tasks
                }
                
                for future in as_completed(future_to_task, timeout=30):  # 30s total timeout
                    i, project_data = future_to_task[future]
                    try:
                        xml_enrichment = future.result(timeout=5)  # 5s per request timeout
                        xml_results[i] = (project_data, xml_enrichment)
                    except Exception as e:
                        print(f"Error enriching project {project_data.get('title', 'Unknown')}: {e}")
                        xml_results[i] = (project_data, None)
        
        # Merge results in original order
        for i, project_data, project_id in xml_tasks:
            if i in xml_results:
                original_project, xml_enrichment = xml_results[i]
                enriched_project = self._merge_xml_data(original_project, xml_enrichment)
                enriched_projects.append(enriched_project)
            else:
                # Fallback if not processed
                enriched_projects.append(project_data)
        
        elapsed_time = time.time() - start_time
        print(f"XML enrichment completed in {elapsed_time:.2f}s for {len(project_data_list)} projects")
        
        return enriched_projects
    
    def _fetch_single_xml_data(self, project_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch and parse XML data for a single project with caching.
        
        Args:
            project_id: The project ID to fetch XML data for
            
        Returns:
            Parsed XML data or None if failed
        """
        # Check cache first
        cache_key = self._get_cache_key(project_id)
        cached_result = self._get_from_cache(self._xml_cache, cache_key)
        if cached_result is not None:
            return cached_result
        
        cookies = {
            'ppms_privacy_f0483949-d65d-4b24-a9ff-82b5105d06fe': '{%22visitorId%22:%22bf7614eb-42c9-4ee5-a9d2-9bf2466c20e7%22%2C%22domain%22:{%22normalized%22:%22cordis.europa.eu%22%2C%22isWildcard%22:false%2C%22pattern%22:%22cordis.europa.eu%22}%2C%22consents%22:{%22analytics%22:{%22status%22:1}}}',
            'consent_cookies': 'allowed',
            'PHPSESSID': 'a3f558f5fa4b198e2aa2980a6b4e3f44',
        }

        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-language': 'nl-NL,nl;q=0.9,en-US;q=0.8,en;q=0.7',
            'cache-control': 'no-cache',
            'pragma': 'no-cache',
            'priority': 'u=0, i',
            'sec-ch-ua': '"Google Chrome";v="137", "Chromium";v="137", "Not/A)Brand";v="24"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Linux"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'same-origin',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
            'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36',
        }
        
        try:
            # Fetch XML data using the correct project ID
            xml_url = f"https://cordis.europa.eu/project/id/{project_id}"
            params = {'format': 'xml'}
            
            response = requests.get(xml_url, params=params, cookies=cookies, headers=headers, timeout=8)
            response.raise_for_status()
            
            # Parse XML and extract additional data
            xml_enrichment = self._extract_xml_project_data(response.content)
            
            # Cache the result
            self._set_cache(self._xml_cache, cache_key, xml_enrichment)
            
            return xml_enrichment
            
        except Exception as e:
            print(f"Error fetching XML for project {project_id}: {e}")
            # Cache None result to avoid repeated failures
            self._set_cache(self._xml_cache, cache_key, None)
            return None
    
    def _merge_xml_data(self, project_data: Dict[str, Any], xml_enrichment: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Merge XML enrichment data with original project data.
        
        Args:
            project_data: Original project data from CORDIS API
            xml_enrichment: Enrichment data from XML or None
            
        Returns:
            Merged project data
        """
        enriched_project = project_data.copy()
        
        if not xml_enrichment:
            return enriched_project
        
        # Update with more detailed data from XML
        if xml_enrichment.get('objective') and xml_enrichment['objective'] != 'Unknown':
            enriched_project['objective'] = xml_enrichment['objective']
        
        if xml_enrichment.get('keywords') and xml_enrichment['keywords'] != 'Unknown':
            # Combine keywords from both sources
            existing_keywords = enriched_project.get('keywords', '')
            if isinstance(xml_enrichment['keywords'], list):
                xml_keywords = ', '.join(xml_enrichment['keywords'])
            else:
                xml_keywords = xml_enrichment['keywords']
            
            if existing_keywords and existing_keywords != 'N/A':
                enriched_project['keywords'] = f"{existing_keywords}, {xml_keywords}"
            else:
                enriched_project['keywords'] = xml_keywords
        
        # Add call information if available
        if xml_enrichment.get('call') and xml_enrichment['call'].get('id') != 'Unknown':
            enriched_project['call_id'] = xml_enrichment['call']['id']
        
        # Update budget information with more details
        if xml_enrichment.get('budget'):
            budget_info = xml_enrichment['budget']
            if budget_info.get('total_cost') != 'Unknown':
                enriched_project['budget'] = budget_info['total_cost']
            if budget_info.get('eu_contribution') != 'Unknown':
                enriched_project['eu_contribution'] = budget_info['eu_contribution']
        
        # Add detailed participant information
        if xml_enrichment.get('participants'):
            detailed_participants = []
            for participant in xml_enrichment['participants']:
                if participant.get('name') != 'Unknown':
                    participant_info = {
                        'name': participant.get('name', 'Unknown'),
                        'country': participant.get('country', 'Unknown'),
                        'city': participant.get('city', 'Unknown')
                    }
                    detailed_participants.append(participant_info)
            
            if detailed_participants:
                enriched_project['detailed_participants'] = detailed_participants
                # Update participant countries and names lists
                enriched_project['participant_names'] = [p['name'] for p in detailed_participants if p['name'] != 'Unknown']
                enriched_project['participant_countries'] = list(set([p['country'] for p in detailed_participants if p['country'] != 'Unknown']))
        
        return enriched_project

    def _remove_namespace(self, element):
        """
        Remove namespace from XML elements for consistent parsing.
        
        Args:
            element: XML element tree to clean
        """
        for elem in element.iter():
            if '}' in elem.tag:
                elem.tag = elem.tag.split('}', 1)[1]  # Remove namespace

    def _extract_xml_project_data(self, xml_content):
        """
        Extract project data from XML content, matching the original implementation.
        
        Extracts the same data fields as the original gpt_2Phase_Ret_CLEAN_v2_submitted.py:
        - objective (from .//objective)
        - title (from .//title)
        - keywords (from .//keywords, split by comma)
        - call information (from .//call/identifier)
        - budget information (from .//totalCost and .//ecMaxContribution)
        - participant information (from .//organization with legalName, country, city)
        
        Args:
            xml_content: Raw XML content from CORDIS endpoint
            
        Returns:
            Dictionary with extracted project data or None if parsing fails
        """
        if not xml_content:
            return None
        
        try:
            # Parse content as XML with fallback parsers
            # Try lxml parser first (fastest), then xml (built-in), then html.parser (most robust)
            soup = None
            for parser in ['lxml-xml', 'xml', 'html.parser']:
                try:
                    soup = BeautifulSoup(xml_content, parser)
                    break
                except Exception as e:
                    if parser == 'html.parser':  # Last fallback
                        print(f"All XML parsers failed. Last error: {e}")
                        return None
                    continue
            
            if soup is None:
                print("Failed to parse XML with any available parser")
                return None
            
            # Remove unnecessary tags
            for tag in soup(["script", "style"]):
                tag.decompose()
            
            # Convert to ElementTree for consistent parsing
            xml_string = str(soup)
            if not xml_string.strip():
                return None
            
            root = ET.fromstring(xml_string.strip())
            self._remove_namespace(root)  # Remove XML namespaces
            
            project_data = {}
            
            # Extract project objective
            objective = root.find(".//objective")
            project_data["objective"] = objective.text if objective is not None else "Unknown"
            
            # Extract project title
            title = root.find(".//title")
            project_data["title"] = title.text if title is not None else "Unknown"
            
            # Extract keywords
            keywords = root.find(".//keywords")
            if keywords is not None and keywords.text:
                keywords_list = keywords.text.split(",")
                project_data["keywords"] = [kw.strip() for kw in keywords_list if kw.strip()]
            else:
                project_data["keywords"] = "Unknown"
            
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
            
        except Exception as e:
            print(f"Error parsing XML content: {e}")
            return None

    def __del__(self):
        """Clean up database connections."""
        if hasattr(self, 'db_pool') and self.db_pool:
            self.db_pool.closeall()

if __name__ == "__main__":
    def test_local_database():
        """Test the local database functionality"""
        print("="*60)
        print("TESTING LOCAL DATABASE INTEGRATION")
        print("="*60)
        
        try:
            # Test with local database
            rag_local = CordisRAG(use_local_db=True)
            
            test_questions = [
                "What are some AI projects in healthcare?",
                "European renewable energy projects",
                "Projects coordinated by German organizations"
            ]
            
            for i, question in enumerate(test_questions, 1):
                print(f"\n🧪 Test {i}: {question}")
                print("-" * 50)
                
                start_time = time.time()
                response = rag_local.get_ai_response(question, max_projects_to_process=3)
                elapsed = time.time() - start_time
                
                print(f"✅ Test {i} completed in {elapsed:.2f}s")
                print(f"Response length: {len(response)} characters")
                print(f"Contains CORDIS links: {'cordis.europa.eu' in response}")
                
                # Show a snippet of the response
                print(f"Response preview: {response[:200]}...")
                
            return True
            
        except Exception as e:
            print(f"❌ Local database test failed: {e}")
            return False
    
    def compare_performance():
        """Compare performance between local database and API"""
        print("="*60)
        print("PERFORMANCE COMPARISON: LOCAL DB vs CORDIS API")
        print("="*60)
        
        question = "machine learning projects in healthcare"
        
        try:
            # Test local database
            print("\n🔍 Testing Local Database...")
            rag_local = CordisRAG(use_local_db=True)
            start_time = time.time()
            response_local = rag_local.get_ai_response(question, max_projects_to_process=3)
            local_time = time.time() - start_time
            
            print(f"✅ Local DB completed in {local_time:.2f}s")
            print(f"Local response length: {len(response_local)} characters")
            
            # Test CORDIS API
            print("\n🌐 Testing CORDIS API...")
            rag_api = CordisRAG(use_local_db=False)
            start_time = time.time()
            response_api = rag_api.get_ai_response(question, max_projects_to_process=3, max_cordis_results=5)
            api_time = time.time() - start_time
            
            print(f"✅ CORDIS API completed in {api_time:.2f}s")
            print(f"API response length: {len(response_api)} characters")
            
            # Performance comparison
            speedup = api_time / local_time if local_time > 0 else 0
            print(f"\n📊 Performance Results:")
            print(f"Local Database: {local_time:.2f}s")
            print(f"CORDIS API: {api_time:.2f}s")
            print(f"Speedup: {speedup:.1f}x faster with local database")
            
            return True
            
        except Exception as e:
            print(f"❌ Performance comparison failed: {e}")
            return False
    
    # Run tests
    print("🚀 Starting V5 Local Database Tests...")
    
    db_test_passed = test_local_database()
    print("\n" + "="*60)
    
    if db_test_passed:
        compare_performance()
        print("\n🎉 ALL V5 TESTS PASSED! Local database integration working correctly.")
    else:
        print("\n❌ Local database tests failed.")
    
    print("="*60)

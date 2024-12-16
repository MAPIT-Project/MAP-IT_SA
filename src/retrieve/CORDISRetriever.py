#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Nov 12 10:47:10 2024

@author: marco
"""
import logging
from mistralai import Mistral
from sentence_transformers import util, SentenceTransformer
import numpy as np
import os
from pdfminer.high_level import extract_text
from topic_ids_and_titles import topic_ids_and_titles
from pydgraph import json
from pydgraph import DgraphClientStub, DgraphClient
from pathlib import Path

class CORDISRetreiver:
    def __init__(self, dgraph_client, base_info_dir, api_key):
        self.dgraph = dgraph_client
        self.base_info_dir = base_info_dir
        self.base_embeddings = None
        self.base_info = []
        self.api_key = api_key
        self.topic_embeddings = None
        self.answers = []
        self.encoder = SentenceTransformer('all-mpnet-base-v2')

        for filename in os.listdir(base_info_dir):
          if filename.endswith(".pdf"):
            filepath = os.path.join(base_info_dir, filename)
            try:
              text = extract_text(filepath)
              
              #TODO we need to use paragraph chunks to (later) identify relevant paragraphs:
              #https://medium.com/@npolovinkin/how-to-chunk-text-into-paragraphs-using-python-8ae66be38ea6
              lines = (line.strip() for line in text.splitlines())
              chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
              text = '\n'.join(chunk for chunk in chunks if chunk) 
              
              chunk_size = 1024 * 2
              chunks = [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]
              
              self.base_embeddings = self.encoder.encode(chunks, convert_to_tensor=True)
              self.base_info = chunks
            
            except Exception as e:
              logging.exception(f"Error reading {filename}", e)
              
            topic_titles = [topic['title'] for topic in topic_ids_and_titles]
            self.topic_embeddings = self.encoder.encode(topic_titles, convert_to_tensor=True)
   
    def get_LLM_client(self):
        client = Mistral(api_key=self.api_key)
        return client
    
    def get_base_information(self, prompt_embedding):
        cosine_similarities = util.cos_sim(prompt_embedding, self.base_embeddings)
        cosine_similarities = cosine_similarities.cpu()
        base_top_3_indices = np.argpartition(cosine_similarities.flatten(), -3)[-3:]

        # Retrieve the 3 most similar chunks
        top_3_retrieved_info = [self.base_info[i] for i in base_top_3_indices]
        base_information = ""
        for info in enumerate(top_3_retrieved_info):
            base_information += f"{info}\n"

        return base_information
    
    def get_CORDIS_topic_info(self, prompt_embedding):
        
        cosine_similarities_topic = util.cos_sim(prompt_embedding, self.topic_embeddings )
        topicID_idx = np.argmax(cosine_similarities_topic)
        
        topicID = topic_ids_and_titles[topicID_idx]['topic']
        
        # query database
        topic_query = f"""{{
                var(func: has(topics)) {{
                    tp as topics
                }}
                q(func: eq(val(tp), {topicID}))
                  {{ 
                    id
                    title
                    objective 
                    }}
                 }}
           """
        res = self.dgraph.txn(read_only=True).query(topic_query)
        horizon_topics_uid = json.loads(res.json).get('q')
        project_info = ""
        
        if (len(horizon_topics_uid)):
            #mutate it with the relations
            topic_title = self.get_project_title_by_ID(topicID)
            for project in horizon_topics_uid:
                   project_info += f"""
                   Horizon project {project['id']} with title "{project['title']}" that aims for 
                   "{project['objective']}" has a similar topic: "{topic_title}".\n
                   """
        return project_info

    ##responsible for sending the prompt to the LLM
    def send_to_LLM(self, new_prompt):
        if len(new_prompt)>131072:
            #too large? chop off the first part
            new_prompt = new_prompt[-131072:]
            
        messages = [
            {
                "role": "user", "content": new_prompt
            }
        ]
        chat_response = self.get_LLM_client().chat.complete(
            model="mistral-large-latest", messages=messages
        )
        answer = (chat_response.choices[0].message.content)
        return answer
        

    def prompting(self, prompt):
        
        prompt_embedding = self.encoder.encode(prompt, convert_to_tensor=True)
        
        context = ""
        context_base  = self.get_base_information(prompt_embedding)
        context_topic = self.get_CORDIS_topic_info(prompt_embedding)
        context_answers = self.get_relevant_history(prompt_embedding)
        
        sim, context_best = self.get_best_project_info(prompt_embedding)
        
        # TODO context += self.get_CORDIS_keywords(prompt_embedding) # make a keywords query
        context_keywords = self.get_CORDIS_keywords(prompt_embedding)

        if sim > .8:
            context = context_best
            
        else:
            context = "\n".join([context_best, context_base, context_topic, context_answers, context_keywords])
        
        
        new_prompt = f"""
        Context information is below.
        ---------------------
        {context}
        ---------------------
        Given the context information and not prior knowledge, answer the query. 
        When the context is empty use your knowledge.
        Query: {prompt}
        Answer:
        """
        answer = self.send_to_LLM(new_prompt)
        if len(self.answers) > 9:
            #get the last nine
            del self.answers[9]
        self.answers.insert(0, answer)
        return answer
    
    def get_relevant_history(self, prompt_embedding):
        if len(self.answers) > 3:
            cosine_similarities = util.cos_sim(prompt_embedding, 
                    self.encoder.encode(self.answers, convert_to_tensor=True))
            
            answer_top_3_indices = np.argpartition(cosine_similarities.flatten(), -3)[-3:]
    
            # Retrieve the 3 most similar chunks
            top_3_retrieved_info = [self.answers[i] for i in answer_top_3_indices]
            information = top_3_retrieved_info.join('\n')            
            return information
        else:
            return ""
            
    
    def get_best_project_info(self, prompt_embedding):
        cosine_similarities_topic = util.cos_sim(prompt_embedding, 
                self.encoder.encode("What is the best Horizon project", convert_to_tensor=True))
        
        print(cosine_similarities_topic.item())
        if cosine_similarities_topic.item() > 0.79:
            return 1, """MOBILIZING ADVANCED PARTNERSHIPS FOR DIGITAL INNOVATION AND TRANSFORMATION 
        (MAPIT) because Marco, Erik, Anton, Burak and Atakan programmed me!""" 
        else:
            return 0,""
        
    def get_project_title_by_ID(self, topicID):
        """
        return a list of project IDs that match the title.
        """
        return [topic['title'] for topic in topic_ids_and_titles if topic['topic'] == topicID]    
 
    def get_CORDIS_keywords(self, prompt_embedding):
        """
        Query the Dgraph database to find relevant information based on keywords.
        """
        # Convert the prompt embedding to a keyword query
        keywords_query = """
        {
            var(func: has(keywords)) {
                kw as keywords
            }
            q(func: eq(val(kw), "%s")) {
                id
                title
                objective
                keywords
            }
        }
        """ % prompt_embedding

        try:
            # Execute the query on the Dgraph database
            res = self.dgraph.txn(read_only=True).query(keywords_query)
            keyword_results = json.loads(res.json).get('q', [])

            # Format the results into a readable string
            keyword_info = ""
            for result in keyword_results:
                keyword_info += f"""
                Project ID: {result['id']}
                Title: {result['title']}
                Objective: {result['objective']}
                Keywords: {result['keywords']}
                ----
                """

            return keyword_info if keyword_info else "No relevant keywords found in the database."

        except Exception as e:
            logging.exception("Error querying keywords from Dgraph", e)
            return "An error occurred while retrieving keyword information."

if __name__ == "__main__":
    #initiate logging as quickly as possible!
    Path('./log/').mkdir(exist_ok=True)
    logger = logging.getLogger(__name__)
    logging.basicConfig(filename='log/MAPIT.log', filemode="a", encoding='utf-8', 
                        level=logging.INFO, format='%(asctime)s %(message)s')
    
    dgraph_url = "localhost:9080"
    if 'DGRAPH_URL' in os.environ:
        dgraph_url = os.environ['DGRAPH_URL']
        
    #TODO temporaly key by marco (wil expire soon). We need a MAPIT key
    api_key = "QfQwLoMaW1z2C56UNHSv8pX5Bqq9Oh9V"
    if 'MAPIT_LLM_KEY' in os.environ:
        api_key = os.environ['MAPIT_LLM_KEY']
        
    base_info_dir = "/home/marco/CORDIS/Small/"
    if 'MAPIT_BASE_INFO_DIR' in os.environ:
        base_info_dir = os.environ['MAPIT_BASE_INFO_DIR']
        
         
    logging.info(f"Using {dgraph_url} as DGRAPH_URL environment variable, specify if needed!")
        
    # Create a Dgraph client stub
    client_stub = DgraphClientStub(dgraph_url)  # Replace with your Dgraph configuration
    
    # Create a Dgraph client
    client = DgraphClient(client_stub)
    
    retreiver = CORDISRetreiver(client, "/home/marco/CORDIS/Small/", api_key)
    print(retreiver.prompting("What is the best Horizon project and why?"))
    
    
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CORDIS Retriever - Core RAG engine for MAPIT AI.

This module implements Retrieval-Augmented Generation (RAG) for querying
EU research funding data from the CORDIS database.

Created on Tue Nov 12 10:47:10 2024
@author: marco
"""
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from mistralai import Mistral
from sentence_transformers import util, SentenceTransformer
import numpy as np
from pdfminer.high_level import extract_text
from topic_ids_and_titles import topic_ids_and_titles
from pydgraph import json
from pydgraph import DgraphClientStub, DgraphClient

from core.logging_config import get_logger, LogContext, set_correlation_id

# Module logger
logger = get_logger('retrieve.cordis')

class CORDISRetreiver:
    """
    CORDIS Retriever implementing RAG for EU funding queries.

    This class handles:
    - Loading and embedding PDF base information
    - Semantic similarity search across multiple sources
    - LLM prompt construction and response generation
    - Conversation history management
    """

    def __init__(self, dgraph_client, base_info_dir: str, api_key: str):
        """
        Initialize the CORDIS Retriever.

        Args:
            dgraph_client: Dgraph database client
            base_info_dir: Directory containing PDF base information
            api_key: Mistral API key for LLM access
        """
        logger.info(f"Initializing CORDISRetriever with base_info_dir={base_info_dir}")

        self.dgraph = dgraph_client
        self.base_info_dir = base_info_dir
        self.base_embeddings = None
        self.base_info = []
        self.api_key = api_key
        self.topic_embeddings = None
        self.answers = []

        # Initialize sentence transformer model
        logger.info("Loading SentenceTransformer model: all-mpnet-base-v2")
        self.encoder = SentenceTransformer('all-mpnet-base-v2')

        # Load and embed PDF documents
        pdf_count = 0
        for filename in os.listdir(base_info_dir):
            if filename.endswith(".pdf"):
                filepath = os.path.join(base_info_dir, filename)
                try:
                    logger.debug(f"Processing PDF: {filename}")
                    text = extract_text(filepath)

                    # Clean and chunk text
                    lines = (line.strip() for line in text.splitlines())
                    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                    text = '\n'.join(chunk for chunk in chunks if chunk)

                    chunk_size = 1024 * 2
                    chunks = [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]

                    self.base_embeddings = self.encoder.encode(chunks, convert_to_tensor=True)
                    self.base_info = chunks
                    pdf_count += 1
                    logger.debug(f"Loaded {len(chunks)} chunks from {filename}")

                except Exception as e:
                    logger.exception(f"Error reading PDF file: {filename}")

        logger.info(f"Loaded {pdf_count} PDF files with {len(self.base_info)} total chunks")

        # Embed topic titles
        topic_titles = [topic['title'] for topic in topic_ids_and_titles]
        self.topic_embeddings = self.encoder.encode(topic_titles, convert_to_tensor=True)
        logger.info(f"Embedded {len(topic_titles)} topic titles")
   
    def get_LLM_client(self):
        """Get a new Mistral LLM client instance."""
        logger.debug("Creating Mistral client")
        client = Mistral(api_key=self.api_key)
        return client

    def get_base_information(self, prompt_embedding):
        """
        Retrieve the most relevant base information chunks.

        Args:
            prompt_embedding: Encoded user query

        Returns:
            String containing the top 3 most relevant chunks
        """
        if self.base_embeddings is None:
            logger.warning("No base embeddings available")
            return ""

        cosine_similarities = util.cos_sim(prompt_embedding, self.base_embeddings)
        cosine_similarities = cosine_similarities.cpu()
        base_top_3_indices = np.argpartition(cosine_similarities.flatten(), -3)[-3:]

        max_similarity = float(cosine_similarities.flatten()[base_top_3_indices].max())
        logger.debug(f"Base info retrieval: max_similarity={max_similarity:.3f}")

        # Retrieve the 3 most similar chunks
        top_3_retrieved_info = [self.base_info[i] for i in base_top_3_indices]
        base_information = ""
        for info in enumerate(top_3_retrieved_info):
            base_information += f"{info}\n"

        return base_information
    
    def get_CORDIS_topic_info(self, prompt_embedding):
        """
        Query Dgraph for projects matching similar topics.

        Args:
            prompt_embedding: Encoded user query

        Returns:
            String describing projects with similar topics
        """
        if self.topic_embeddings is None:
            logger.warning("No topic embeddings available")
            return ""

        cosine_similarities_topic = util.cos_sim(prompt_embedding, self.topic_embeddings)
        cosine_similarities_topic = cosine_similarities_topic.cpu()

        topicID_idx = np.argmax(cosine_similarities_topic)
        max_similarity = float(cosine_similarities_topic.flatten()[topicID_idx])

        topicID = topic_ids_and_titles[topicID_idx]['topic']
        logger.debug(f"Topic matching: topicID={topicID}, similarity={max_similarity:.3f}")

        # Query database for projects with this topic
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

        try:
            res = self.dgraph.txn(read_only=True).query(topic_query)
            horizon_topics_uid = json.loads(res.json).get('q', [])
            logger.debug(f"Found {len(horizon_topics_uid)} projects for topic {topicID}")
        except Exception as e:
            logger.exception(f"Error querying Dgraph for topic {topicID}")
            return ""

        project_info = ""

        if len(horizon_topics_uid):
            topic_title = self.get_project_title_by_ID(topicID)
            for project in horizon_topics_uid:
                project_info += f"""
                   Horizon project {project['id']} with title "{project['title']}" that aims for
                   "{project['objective']}" has a similar topic: "{topic_title}".\n
                   """

        return project_info

    def send_to_LLM(self, new_prompt: str) -> str:
        """
        Send a prompt to the Mistral LLM and get a response.

        Args:
            new_prompt: The constructed prompt to send

        Returns:
            The LLM's response text
        """
        prompt_length = len(new_prompt)
        logger.info(f"Sending prompt to LLM: length={prompt_length} chars")

        if prompt_length > 131072:
            logger.warning(f"Prompt too long ({prompt_length}), truncating to 131072 chars")
            new_prompt = new_prompt[-131072:]

        messages = [
            {"role": "user", "content": new_prompt}
        ]

        try:
            with LogContext(logger, "LLM API call"):
                chat_response = self.get_LLM_client().chat.complete(
                    model="mistral-large-latest", messages=messages
                )

            response_text = str(chat_response.choices[0].message.content)
            logger.info(f"LLM response received: length={len(response_text)} chars")
            return response_text

        except Exception as e:
            logger.exception("Error calling Mistral LLM API")
            raise
        

    def prompting(self, prompt: str) -> str:
        """
        Main entry point for processing user queries.

        This method orchestrates the RAG pipeline:
        1. Encode the user query
        2. Retrieve relevant context from multiple sources
        3. Construct augmented prompt
        4. Get LLM response
        5. Store in conversation history

        Args:
            prompt: User's natural language query

        Returns:
            LLM-generated response
        """
        # Set correlation ID for request tracing
        correlation_id = set_correlation_id()
        logger.info(f"Processing query: '{prompt[:100]}...' (length={len(prompt)})")

        with LogContext(logger, "Query processing"):
            # Encode the prompt
            prompt_embedding = self.encoder.encode(prompt, convert_to_tensor=True)
            logger.debug("Query encoded successfully")

            # Retrieve context from multiple sources
            context_base = self.get_base_information(prompt_embedding)
            context_topic = self.get_CORDIS_topic_info(prompt_embedding)
            context_answers = self.get_relevant_history(prompt_embedding)
            sim, context_best = self.get_best_project_info(prompt_embedding)

            # TODO: Add keyword-based retrieval
            # context_keywords = self.get_CORDIS_keywords(prompt_embedding)

            # Select best context based on similarity
            if sim > 0.8:
                context = context_best
                logger.debug(f"Using best project context (similarity={sim:.3f})")
            else:
                context = "\n".join([context_best, context_base, context_topic, context_answers])
                logger.debug(f"Using combined context (best_sim={sim:.3f})")

            context_length = len(context)
            logger.info(f"Context assembled: {context_length} chars")

            # Build augmented prompt
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

            # Get LLM response
            answer = self.send_to_LLM(new_prompt)

            # Update conversation history
            if len(self.answers) > 9:
                del self.answers[9]
            self.answers.insert(0, answer)
            logger.debug(f"Answer stored in history (history_size={len(self.answers)})")

        return answer
    
    def get_relevant_history(self, prompt_embedding):
        """
        Retrieve relevant conversation history based on similarity.

        Args:
            prompt_embedding: Encoded user query

        Returns:
            String containing relevant previous answers
        """
        if len(self.answers) > 3:
            cosine_similarities = util.cos_sim(
                prompt_embedding,
                self.encoder.encode(self.answers, convert_to_tensor=True)
            )
            cosine_similarities = cosine_similarities.cpu()

            answer_top_3_indices = np.argpartition(cosine_similarities.flatten(), -3)[-3:]
            max_similarity = float(cosine_similarities.flatten()[answer_top_3_indices].max())
            logger.debug(f"History retrieval: found {len(answer_top_3_indices)} relevant, max_sim={max_similarity:.3f}")

            # Retrieve the 3 most similar chunks
            top_3_retrieved_info = [self.answers[i] for i in answer_top_3_indices]
            information = "\n".join(top_3_retrieved_info)
            return information
        else:
            logger.debug(f"History too short ({len(self.answers)} answers), skipping")
            return ""

    def get_best_project_info(self, prompt_embedding):
        """
        Check if the query is asking about the best project (Easter egg).

        Args:
            prompt_embedding: Encoded user query

        Returns:
            Tuple of (similarity_score, response_text)
        """
        cosine_similarities_topic = util.cos_sim(
            prompt_embedding,
            self.encoder.encode("What is the best Horizon project", convert_to_tensor=True)
        )
        cosine_similarities_topic = cosine_similarities_topic.cpu()

        similarity = cosine_similarities_topic.item()
        logger.debug(f"Best project check: similarity={similarity:.3f}")

        if similarity > 0.79:
            return 1, """MOBILIZING ADVANCED PARTNERSHIPS FOR DIGITAL INNOVATION AND TRANSFORMATION
        (MAPIT) because Marco, Erik, Anton, Burak and Atakan programmed me!"""
        else:
            return 0, ""

    def get_project_title_by_ID(self, topicID: str) -> list:
        """
        Get project titles matching a topic ID.

        Args:
            topicID: The topic ID to search for

        Returns:
            List of matching project titles
        """
        return [topic['title'] for topic in topic_ids_and_titles if topic['topic'] == topicID]    
 
    def get_CORDIS_keywords(self, prompt_embedding):
        """
        Query the Dgraph database to find relevant information based on keywords.

        Note: This method is currently a TODO/work in progress.

        Args:
            prompt_embedding: Encoded user query

        Returns:
            String containing keyword-matched project information
        """
        logger.debug("Executing keyword search (experimental)")

        # Get all tags from database
        tags_query = """{
                          var(func: type(Project)) {
                            tags
                          }
                          result(func: uid(tags)) @groupby(tags) {
                            tags: val(tags)
                          }
                        }"""

        try:
            res = self.dgraph.txn(read_only=True).query(tags_query)
            keyword_results = json.loads(res.json).get('result', [])
            logger.debug(f"Retrieved {len(keyword_results)} keywords from database")
        except Exception as e:
            logger.exception("Error retrieving keywords from Dgraph")
            return "An error occurred while retrieving keywords."

        if not keyword_results:
            logger.warning("No keywords found in database")
            return "No keywords found in the database."

        # Get most similar keywords
        try:
            cosine_similarities = util.cos_sim(prompt_embedding, keyword_results)
            cosine_similarities = cosine_similarities.cpu()
            top_3_keywords = np.argpartition(cosine_similarities.flatten(), -3)[-3:].join(" ")
        except Exception as e:
            logger.exception("Error computing keyword similarities")
            return "Error processing keywords."

        # Find projects with matching keywords
        keywords_query = f"""
                                {{
                                    var(func: has(keywords)) {{
                                        kw as keywords
                                    }}
                                    q(func: anyoftext(val(kw), "{top_3_keywords}")) {{
                                        id
                                        title
                                        objective
                                        keywords
                                    }}
                                }}
        """

        try:
            res = self.dgraph.txn(read_only=True).query(keywords_query)
            keyword_results = json.loads(res.json).get('q', [])
            logger.debug(f"Found {len(keyword_results)} projects matching keywords")

            # Format results
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
            logger.exception("Error querying keywords from Dgraph")
            return "An error occurred while retrieving keyword information."


if __name__ == "__main__":
    from core.logging_config import setup_logging

    # Initialize structured logging
    setup_logging(log_level="DEBUG", log_dir="./log", log_file="mapit.log")

    logger.info("Starting CORDISRetriever standalone test")

    # Get configuration from environment
    dgraph_url = os.environ.get('DGRAPH_URL', 'localhost:9080')
    api_key = os.environ.get('MAPIT_LLM_KEY', '')
    base_info_dir = os.environ.get('MAPIT_BASE_INFO_DIR', '/home/mdumont/CORDIS/pdfs')

    if not api_key:
        logger.error("MAPIT_LLM_KEY environment variable not set")
        sys.exit(1)

    logger.info(f"Configuration: dgraph_url={dgraph_url}, base_info_dir={base_info_dir}")

    try:
        # Create Dgraph client
        client_stub = DgraphClientStub(dgraph_url)
        client = DgraphClient(client_stub)
        logger.info("Dgraph client connected")

        # Initialize retriever
        retriever = CORDISRetreiver(client, base_info_dir, api_key)

        # Test query
        test_query = "What is the best Horizon project and why?"
        logger.info(f"Test query: {test_query}")
        response = retriever.prompting(test_query)
        print(f"\nResponse:\n{response}")

    except Exception as e:
        logger.exception("Error during standalone test")
        sys.exit(1)

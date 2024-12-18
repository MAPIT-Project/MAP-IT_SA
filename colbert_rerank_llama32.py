from transformers import AutoTokenizer, AutoModel
import torch
import time
import bm25s


from langchain_ollama import OllamaLLM



def maxsim(query_embedding, document_embedding):
    # Expand dimensions
    expanded_query = query_embedding.unsqueeze(2)
    expanded_doc = document_embedding.unsqueeze(1)

    # Compute cosine similarity
    sim_matrix = torch.nn.functional.cosine_similarity(expanded_query, expanded_doc, dim=-1)

    # sim_matrix shape: [batch_size, query_length, doc_length]
    max_sim_scores, _ = torch.max(sim_matrix, dim=2)

    # Average these maximum scores across all query tokens
    avg_max_sim = torch.mean(max_sim_scores, dim=1)
    return avg_max_sim


if __name__=="__main__":

	llm = OllamaLLM(model="llama3.2")	# Mistral API access is not cheap. Then, either GPT4 or Llama-70B (hardware?)...
	
	
	corpus=[]
	with open("small_dat_refined","r") as f:
		x = f.read()
		corpus = eval(x)


	retriever = bm25s.BM25(corpus=corpus)
	retriever.index(bm25s.tokenize(corpus))

	# Query the corpus and get top-k results
	#query = "Which projects concern public health?"  
	#query = "What are the most prevalent applications of machine learning?" -> NON-STATIC, CONFIDENCE-SCORE-BASED TOP-K SELECTION IS A MUST!
	#query = "Which projects are about production technologies?" -> BAD!!!
	#query = "Which projects are related to production technologies?"  -> bad but relatively better.
	#query = "Which projects are about dissemination of knowledge?"
	#query = "Which projects are related to dissemination of knowledge?" 
	#query = "Which projects are about electronic devices?"
	
	#query = "Who invented the red hot flying car?" -> good answer.
	#query = "Who invented deep learning?"
	#query = "Which projects focus on body building?" -> good answer.

	#query = "List 2 most important projects. Why are those 2 projects that important?" -> QUERY AUGMENTATION IS A MUST!

	#query = "How is the weather?" -> acceptable answer for this.
	#query = "Who is the boss?"  -> initial performance was bad. solved by adding the "Further, use your internal knowledge to understand..." sentence to the prompt.

	#query = "In which projects is METU involved?"
	#query = Which projects might have been conducted by METU? -> Bad for now, but not too bad. Even promising.
	#query = Which projects might have been conducted by MIT?
	#query = Which projects might have been conducted by the Beatles?
	
	while True:

		query = input("Ask boss!:")

		results, scores = retriever.retrieve(bm25s.tokenize(query), k=10)
		
		print("Retrieving relevant passages...")

		docs = results[0] #bm25_ranked

		"""
		for i,doc in enumerate(docs):
			print(i)
			print(doc)

		print("\n")
		print("RERANK:..")
		"""

		print("Reranking with ColBERT...")

		# Initialize tokenizer and model
		tokenizer = AutoTokenizer.from_pretrained("colbert-ir/colbertv2.0")
		model = AutoModel.from_pretrained("colbert-ir/colbertv2.0")

		#tokenizer = AutoTokenizer.from_pretrained("jinaai/jina-colbert-v2")
		#model = AutoModel.from_pretrained("jinaai/jina-colbert-v2")



		# Encode the query
		#query = "your query text here"  # Replace with your actual query
		#docs = ["doc1", "doc2"]  # Replace with your actual documents
		scores = []  # Initialize scores as a list
		start = time.time()

		# Tokenize and encode the query
		query_encoding = tokenizer(query, return_tensors='pt')
		query_embedding = model(**query_encoding).last_hidden_state.mean(dim=1)

		# Get score for each document
		for document in docs:
		    # Tokenize and encode the document
		    document_encoding = tokenizer(document, return_tensors='pt', truncation=True)
		    document_embedding = model(**document_encoding).last_hidden_state

		    # Calculate MaxSim score
		    score = maxsim(query_embedding.unsqueeze(0), document_embedding)
		    scores.append({
			"score": score.item(),
			"document": document,
		    })

		# Print the time taken to re-rank documents
		print(f"Passages re-ranked in {time.time() - start} seconds with ColBERT.")

		# Sort and print the scores
		sorted_data = sorted(scores, key=lambda x: x['score'], reverse=True)
		#print(sorted_data[0])


		"""
		for i,doc in enumerate(sorted_data):
			print(i)
			print(doc["document"])
		"""	
			





		prompt2 = f"""
		Most relevant retrieved context information is below.
		---------------------
		Retrieved project 1: {sorted_data[0]["document"]}
		---------------------
		Additional retrieved context information is as such:
		---------------------
		Retrieved project 2: {sorted_data[1]["document"]}
		Retrieved project 3: {sorted_data[2]["document"]}
		Retrieved project 4: {sorted_data[3]["document"]}
		Retrieved project 5: {sorted_data[4]["document"]}
		---------------------
		The instructions for you to follow are those:
		You play the role of a knowledge steward providing the research and innovation landscape of European research projects. You are helping to a research university or institute to retrieve information from the corpus of previously funded projects.
		Following your designated role and the given context information, answer the query that will be provided at the end.
		If the given query is irrelevant to your designated role and to the task of searching sophisticated information about research projects, just say that and do not give other details. In that case, do not mention anything about the provided context. Further, use your internal knowledge to understand whether the query is relevant to the provided context information and to your role. If it is not relevant, say that and terminate your answer. If so, do not mention anything in the provided context information. If it is relevant, continue by obeying the following instructions:
		The provided projects in the context information are ranked from more confident to the less confident. Take this ordering into account while grounding your answer. Nevertheless, you may change the ordering of the retrieved projects if you really need to. Do not explicitly mention the rankings. Also do not mention the number of passages or number of projects in the context. You may give multiple retrieved projects and multiple passages as the answer. 
		Explain the relation of your answer with the context information step by step, with a few steps. Further, at each step, briefly comment on why you find them related. If you explicitly refer to a retrieved project or a passage in your explanations, refer it with the name of the project instead of the project number, and at the end give the whole passage you referred. Make sure you are providing the correct passage. If you are not confident about you are providing the correct passage, do not provide it.
		If you find some of the retrieved projects or passages mildly irrelevant, say those retrieved projects or passages may seem relevant at first sight, however, they are not. Then, explain why you do not find them relevant. If you find some or all retrieved projects and passages are strictly irrelevant, do not mention those irrelevant retrieved projects and passages. 
		On the other hand, if all of the context information is strictly irrelevant, give a brief answer conveying the meaning "Either your question is not relevant to the scope or there are no related projects.". In this case, do not explicitly mention the context information, do not refer or cite any retrieved projects or passages. Further, if that is the case, do not show your reasoning steps. Instead, give a very brief explanation without complex reasoning.
		Lastly, if the query seem relevant to the provided context but its answer is not present in the provided context, say "I cannot retrieve the answer of your question.", then give a very brief explanation without complex reasoning. 
		Always keep your answer compact and precise.
		Query: {query}
		Answer:
		"""

		#EXCLUDED FROM THE PROMPT:  Use as less prior knowledge as possible.
		
		# *** A relevance check for the questions may require (to eliminate questions unrelated to the purpose). We may also provide that functionality by prompt-tuning.

		print("Generating answer...")



		#llm = OllamaLLM(model="llama3.2")
		response = llm.invoke(prompt2)
		print("\n\n")
		print(response)
		print("\n\n")
		
		# IN THE USER INTERFACE: Show retrieved passages - button
		#			 Remember the previous answer - button
		#			 Was the answer related? - selection
		



		 











from mistralai import Mistral
from sentence_transformers import util, SentenceTransformer
import numpy as np
import os
from pdfminer.high_level import extract_text
from topic_ids_and_titles import topic_ids_and_titles
from pydgraph import json
from pydgraph import DgraphClientStub, DgraphClient

api_key="iF2n1vbiburOLKJkZDJaGONFxzodiQPV"
client = Mistral(api_key=api_key)


base_info = []


def read_pdfs_from_directory(directory):
  """
    Read the text of PDFs in a directory

    Parameters
    ----------
    directory : String containing the directory

    Returns
    -------
    base_info : string with chunks

  """

  for filename in os.listdir(directory):
    if filename.endswith(".pdf"):
      filepath = os.path.join(directory, filename)
      try:
        text = extract_text(filepath)
        
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk) 
        
        chunk_size = 1024 * 2
        chunks = [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]
        base_info.append(chunks)
      except Exception as e:
        print(f"Error reading {filename}: {e}")
  return base_info

# Replace "pdf_directory" with pdf path
#pdf_directory = "/home/marco/CORDIS/Manuals/"
pdf_directory = "/home/marco/CORDIS/Small/" 
base_info = read_pdfs_from_directory(pdf_directory)

model = SentenceTransformer('all-mpnet-base-v2')
base_embeddings = model.encode(base_info, convert_to_tensor=True)

#query = "What is the structure of the Horizon Europe programme?"
#this query comes from the gui later on
query = "Which projects research capabilities in innovation procurement? Can you give the titles and summary of the objective?"
query_embedding = model.encode(query, convert_to_tensor=True)

# Calculate cosine similarity between all pairs of embeddings
cosine_similarities = util.cos_sim(base_embeddings, query_embedding)
most_similar_idx = np.argmax(cosine_similarities)
retrieved_chunk = base_info[most_similar_idx] 

#top_3_indices = np.argpartition(cosine_similarities.flatten(), -2)[-2:]

# Retrieve the 3 most similar chunks
#top_3_retrieved_chunks = [base_info[i] for i in top_3_indices]

# the retrieved chunks

#for i, chunk in enumerate(top_3_retrieved_chunks):
 #   print(f"Top {i+1} retrieved chunk:{chunk}\n")
 #   retrieved_chunk += f"{chunk}"

#read the database and query for projects with that topic
def get_project_title_by_ID(topicID):
    """
    return a list of project IDs that match the title.
    """
    return [topic['title'] for topic in topic_ids_and_titles if topic['topic'] == topicID]

topic_titles = [topic['title'] for topic in topic_ids_and_titles]
topic_embeddings =  model.encode(topic_titles, convert_to_tensor=True)
cosine_similarities_topic = util.cos_sim(query_embedding, topic_embeddings )
topicID_idx = np.argmax(cosine_similarities_topic)

topicID = topic_ids_and_titles[topicID_idx]['topic']

def connectToGraph():
     
    dgraph_url = "localhost:9080"
    if 'DGRAPH_URL' in os.environ:
        dgraph_url = os.environ['DGRAPH_URL']
         
#    logging.info(f"Using {dgraph_url} as DGRAPH_URL environment variable, specify if needed!")
        
    # Create a Dgraph client stub
    client_stub = DgraphClientStub(dgraph_url)  # Replace with your Dgraph configuration
    
    # Create a Dgraph client
    client = DgraphClient(client_stub)
    return client, client_stub

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
dgraph, dgraph_stub = connectToGraph()
res = dgraph.txn(read_only=True).query(topic_query)
horizon_topics_uid = json.loads(res.json).get('q')

if (len(horizon_topics_uid)):
    
    #mutate it with the relations
    topic_title = get_project_title_by_ID(topicID)     
    for project in horizon_topics_uid:
           retrieved_chunk += f"""
           Horizon project {project['id']} with title "{project['title']}" that aims for 
           "{project['objective']}" has a similar topic: "{topic_title}".\n
           """

prompt = f"""
Context information is below.
---------------------
{retrieved_chunk}
---------------------
Given the context information and not prior knowledge, answer the query.
Query: {query}
Answer:
"""

if len(prompt)>131072:
    #too large? chop off the first part
    prompt = prompt[-131072:]

def run_mistral(user_message, model="mistral-large-latest"):
    messages = [
        {
            "role": "user", "content": user_message
        }
    ]
    chat_response = client.chat.complete(
        model=model,
        messages=messages
    )
    return (chat_response.choices[0].message.content)

print (run_mistral(prompt))
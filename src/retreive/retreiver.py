#TC7m5NYvjN8t7ATwMDHSrhNvyYu2dLgi

from mistralai import Mistral
from sentence_transformers import util, SentenceTransformer
import numpy as np
import os
from pdfminer.high_level import extract_text

api_key="TC7m5NYvjN8t7ATwMDHSrhNvyYu2dLgi"
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
        
        chunk_size = 2048
        chunks = [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]
        base_info.append(chunks)
      except Exception as e:
        print(f"Error reading {filename}: {e}")
  return base_info

# Vervang "pad/naar/je/pdf/map" met het daadwerkelijke pad naar je map
pdf_directory = "/home/marco/CORDIS/Manuals/"
base_info = read_pdfs_from_directory(pdf_directory)


model = SentenceTransformer('all-mpnet-base-v2')
embeddings = model.encode(base_info, convert_to_tensor=True)

#query = "What is the structure of the Horizon Europe programme?"
query = "What are the thematic fields are covered?"
query_embedding = model.encode(query, convert_to_tensor=True)

# Calculate cosine similarity between all pairs of embeddings
cosine_similarities = util.cos_sim(embeddings, query_embedding)
most_similar_idx = np.argmax(cosine_similarities)
retrieved_chunk = base_info[most_similar_idx] 



prompt = f"""
Context information is below.
---------------------
{retrieved_chunk}
---------------------
Given the context information and not prior knowledge, answer the query.
Query: {query}
Answer:
"""

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
import sys
from flask import Flask, request, jsonify, render_template
import os
#from pathlib import Path
sys.path.append(os.path.join(os.getcwd(), "src/retrieve"))
  
from CORDISRetriever import CORDISRetreiver
from pydgraph import DgraphClientStub, DgraphClient
import logging
from pathlib import Path


# Environment variables and constants
DGRAPH_URL = os.environ.get('DGRAPH_URL', 'localhost:9080')
BASE_INFO_DIR = os.environ.get('MAPIT_BASE_INFO_DIR', '/home/marco/CORDIS/Small/')
API_KEY = os.environ.get('MAPIT_LLM_KEY', 'iF2n1vbiburOLKJkZDJaGONFxzodiQPV')
 
PORT = os.environ.get('MAPIT_PORT', '8081')
HOST = os.environ.get('MAPIT_HOST', '0.0.0.0')

# Initialize Flask app
class MyAPP(Flask):
    
    def __init__(self):
        super().__init__(__name__)
        self.retriever = None
        Path('./log/').mkdir(exist_ok=True)
        logger = logging.getLogger(__name__)
        logging.basicConfig(filename='log/MAPIT.log', filemode="a", encoding='utf-8', 
                            level=logging.INFO, format='%(asctime)s %(message)s')
        try:
            client_stub = DgraphClientStub(DGRAPH_URL)
            client = DgraphClient(client_stub)
            self.retriever = CORDISRetreiver(client, BASE_INFO_DIR, API_KEY)
        except Exception as e:
             logging.exception("Failed to initialize CORDISRetriever.", e)
    
    def get_cordis_retriever(self):
        return self.retriever
    
#get the show on the road.
app = MyAPP()

@app.route('/')
def index():
    """Render the home page."""
    return render_template('index.html')


@app.route('/query', methods=['POST'])
def query():
    """Handle POST requests to execute a query using the CORDISRetriever."""
    query = request.json.get('query', '')
    if not query:
        return jsonify({"error": "Query parameter is missing."}), 400

    retriever = app.get_cordis_retriever()

    try:
        response = retriever.prompting(query)
        logging.info(f"QR:{query}-{response}")
        return jsonify({"response": response})
    except Exception as e:
        logging.exception("error", e)
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    try:
        logging.info(f"Using {HOST}:{PORT}")
        app.run(host=HOST, port=PORT)
    except Exception as e:
        logging.exception("error starting", e)    
    

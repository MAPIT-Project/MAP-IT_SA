from flask import Flask, request, jsonify, render_template
import sys
import os

sys.path.append('/app/src/retrieve')  
from CORDISRetriever import CORDISRetreiver 
from pydgraph import DgraphClientStub, DgraphClient

# Initialize Flask app
app = Flask(__name__)

# Environment variables and constants
DGRAPH_URL = os.environ.get('DGRAPH_URL', 'localhost:9080')
BASE_INFO_DIR = os.environ.get('MAPIT_BASE_INFO_DIR', '/home/marco/CORDIS/Small/')
API_KEY = os.environ.get('MAPIT_LLM_KEY', 'iF2n1vbiburOLKJkZDJaGONFxzodiQPV')


def get_cordis_retriever():
    """Initialize and return the CORDISRetriever instance."""
    try:
        client_stub = DgraphClientStub(DGRAPH_URL)
        client = DgraphClient(client_stub)
        retriever = CORDISRetreiver(client, BASE_INFO_DIR, API_KEY)
        return retriever
    except Exception as e:
        raise RuntimeError(f"Failed to initialize CORDISRetriever: {str(e)}")


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

    retriever = get_cordis_retriever()

    try:
        response = retriever.prompting(query)
        return jsonify({"response": response})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

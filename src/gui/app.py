from flask import Flask, request, jsonify, render_template
from pydgraph import DgraphClient, DgraphClientStub

app = Flask(__name__)

def get_dgraph_client():
    stub = DgraphClientStub('dgraph:9080')  # Connect to Dgraph
    client = DgraphClient(stub)
    return client, stub

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/query', methods=['POST'])
def query():
    query = request.json.get('query', '')
    client, stub = get_dgraph_client()
    try:
        response = client.txn(read_only=True).query(query)
        return jsonify(response.json)
    except Exception as e:
        return jsonify({"error": str(e)})
    finally:
        stub.close()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

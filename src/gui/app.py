"""
MAPIT AI Flask Web Application.

Provides a web interface for querying EU research funding information
using the CORDIS Retriever RAG engine.
"""
import sys
import os
from pathlib import Path

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "retrieve"))

from flask import Flask, request, jsonify, render_template
from pydgraph import DgraphClientStub, DgraphClient

from CORDISRetriever import CORDISRetreiver
from core.logging_config import setup_logging, get_logger, set_correlation_id, LogContext

# Module logger
logger = get_logger('gui.app')

# Environment variables and constants
DGRAPH_URL = os.environ.get('DGRAPH_URL', 'localhost:9080')
BASE_INFO_DIR = os.environ.get('MAPIT_BASE_INFO_DIR', '/home/mdumont/CORDIS/Small')
API_KEY = os.environ.get('MAPIT_LLM_KEY', '')
PORT = int(os.environ.get('MAPIT_PORT', '16000'))
HOST = os.environ.get('MAPIT_HOST', '0.0.0.0')


class MAPITApp(Flask):
    """
    MAPIT Flask application with integrated CORDIS Retriever.

    This class extends Flask to include the RAG retriever as part
    of the application context.
    """

    def __init__(self):
        super().__init__(__name__)
        self.retriever = None
        self._init_retriever()

    def _init_retriever(self):
        """Initialize the CORDIS Retriever."""
        logger.info(f"Initializing MAPIT application")
        logger.info(f"Configuration: dgraph_url={DGRAPH_URL}, base_info_dir={BASE_INFO_DIR}")

        if not API_KEY:
            logger.warning("MAPIT_LLM_KEY not set - LLM features will be disabled")
            return

        try:
            with LogContext(logger, "Dgraph connection"):
                client_stub = DgraphClientStub(DGRAPH_URL)
                client = DgraphClient(client_stub)

            with LogContext(logger, "CORDISRetriever initialization"):
                self.retriever = CORDISRetreiver(client, BASE_INFO_DIR, API_KEY)

            logger.info("MAPIT application initialized successfully")

        except Exception as e:
            logger.exception("Failed to initialize CORDISRetriever")
            self.retriever = None

    def get_cordis_retriever(self):
        """Get the CORDIS Retriever instance."""
        return self.retriever


# Create application instance
app = MAPITApp()


@app.route('/')
def index():
    """Render the home page."""
    logger.debug("Serving index page")
    return render_template('index.html')


@app.route('/health')
def health():
    """Health check endpoint for monitoring."""
    retriever_status = "healthy" if app.get_cordis_retriever() is not None else "degraded"
    return jsonify({
        "status": "ok",
        "retriever": retriever_status
    })


@app.route('/query', methods=['POST'])
def query():
    """
    Handle POST requests to execute a query using the CORDISRetriever.

    Request body should contain:
        query (str): The user's natural language query

    Returns:
        JSON response with the LLM-generated answer
    """
    # Set correlation ID for request tracing
    correlation_id = set_correlation_id()

    # Validate request
    query_text = request.json.get('query', '') if request.json else ''
    if not query_text:
        logger.warning(f"Empty query received")
        return jsonify({"error": "Query parameter is missing."}), 400

    # Check if query is too long
    if len(query_text) > 10000:
        logger.warning(f"Query too long: {len(query_text)} chars")
        return jsonify({"error": "Query is too long. Maximum 10000 characters."}), 400

    logger.info(f"Query received: '{query_text[:100]}...' (length={len(query_text)})")

    retriever = app.get_cordis_retriever()
    if retriever is None:
        logger.error("Retriever not available")
        return jsonify({"error": "Service temporarily unavailable. Please try again later."}), 503

    try:
        with LogContext(logger, "Query processing"):
            response = retriever.prompting(query_text)

        logger.info(f"Query completed successfully: response_length={len(response)}")
        return jsonify({"response": response})

    except Exception as e:
        logger.exception(f"Error processing query")
        return jsonify({"error": "An error occurred while processing your query. Please try again."}), 500


if __name__ == '__main__':
    # Initialize structured logging
    setup_logging(log_level="INFO", log_dir="./log", log_file="mapit.log")

    logger.info(f"Starting MAPIT web server on {HOST}:{PORT}")

    try:
        app.run(host=HOST, port=PORT, debug=False)
    except Exception as e:
        logger.exception("Error starting MAPIT web server")
        sys.exit(1)


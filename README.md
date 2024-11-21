# MAPIT_base_HU
This is the knowledgebase for the MAPIT RAG-LLM.

---

## GUI Interface

### To get the GUI interface up and running, follow these steps:

> **NOTE:** Please make sure you have Docker installed.

---

### Steps:

1. Open a command prompt and make sure you are in the main directory (`MAP-IT_SA`).
2. In the command prompt, type the following command:
   ```bash
   docker-compose up --build
   
This will run the Docker file in the main directory to start the Flask app.

3. Once the Flask app starts successfully, it will run locally at: http://127.0.0.1:5000/

### Expected Output:
If everything is done successfully, you should see something like this in the terminal:

   ```bash
    Attaching to flask_app-1
    flask_app-1  |  * Serving Flask app 'app'
    flask_app-1  |  * Debug mode: off
    flask_app-1  | WARNING: This is a development server. Do not use it in a production deployment. Use a production WSGI server instead.
    flask_app-1  |  * Running on all addresses (0.0.0.0)
    flask_app-1  |  * Running on http://127.0.0.1:5000
    flask_app-1  |  * Running on http://172.19.0.2:5000
    flask_app-1  | Press CTRL+C to quit

MAP-IT Horizon CRISPR-PM High level overview document
Version: 1.0

Date: October 2, 2024

Author: Marco Dumont

1. Introduction
This document outlines the data science architecture for the MAP-IT Horizon project, aligning with the Cross-Industry Standard Process for Data Mining (CRISP-DM) methodology. 
It aims to provide a clear and comprehensive view of the system's structure and components, guiding the project's development and implementation.

[CRISP-DM](./CRISP_DM.png)


2. CRISP-DM Phases and Corresponding Components
    1. Business Understanding
Objective: Define project objectives and requirements from a business perspective.
For the MAP-IT  project the project goals are to assist in research managers to query the CORDIS database and other databases with similar or additional information.  This search tool is buikd with an lange model interface. So the questions are a more natural language of the research managers. 
        1. Stakeholders of this search tool are: for example:
          -  The main intended users are research managers managing EU research projects or to see what is already done.
          -  Researchers looking for funding or coordination. 
          -  Project managers looking for potentional collaboration.
          -  Innovation partners looking for research projects.
          -  ....
          -  ....

          2. **Components**:
          - [Stakeholder Analysis](./stakeholder_analysis.md): Identify and analyze key stakeholders and their needs.
          - [Objective Setting](./objectives.md): Translate business needs into concrete project goals and deliverables.
          - [Requirement Gathering](./requirements.md): Document detailed functional and non-functional requirements.


    2. **Data Understanding**
Objective: Collect, explore, and assess the quality of relevant data sources.

        1.  Components:
       - Data Acquisition Module: Retrieve data from CORDIS API, CORDIS and OPENAIR CSV files, and other sources.
       - Data Extraction Module: Perform exploratory data analysis (EDA) to understand data characteristics.
       - Data Quality Assessment Module: Identify data quality issues and plan mitigation strategies.
     3. **Data Preparation**
     Objective: Clean, transform, and integrate data to make it suitable for modeling into Dgraph.
       
     4.  **Data Integration Module** 
     Objective: Merge data from multiple sources into a unified dataset.
   
     5. **Modeling**
[Ontology](./Question_Ontology.pdf)
Objective: Select and apply appropriate data mining techniques to address project goals.
Components:
    - Model Selection Module: Choose suitable algorithms based on data characteristics and objectives.
    - Model Training Module: Train and optimize selected models using the prepared data.
    - Model Evaluation Module: Assess model performance using relevant metrics.
     6.  **Evaluation**
Objective: Evaluate the model's performance and its alignment with business objectives.
Components:
            - Result Interpretation Module: Analyze model outputs and extract meaningful insights.
            - Performance Validation Module: Compare model performance against predefined criteria. 
            - Business Goal Assessment Module: Determine if the model meets the initial business objectives.
    6.  Deployment
Objective: Deploy the model and integrate it into existing systems or processes.

     - Components:
         - Model Deployment Module: Deploy the trained model to a production environment.
         - System Integration Module: Integrate the model with existing workflows and applications.
         - Monitoring and Maintenance Module: Monitor model performance and ensure its ongoing accuracy.

7. Technology Stack
    - Programming Language: Python
    - Database: Dgraph
    - Data Analysis Libraries: pandas, scikit-learn, TensorFlow/PyTorch (if deep learning is used)
     - Visualization Libraries: matplotlib, seaborn, Plotly
     - RAG-LLM: Mistral-7B
     - Web Framework: (To be determined)
     - Cloud Environment: (To be determined)

5. Architecture overview
[Overview](./ComponentOverview.drawio.png)
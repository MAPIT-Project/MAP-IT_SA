MAP-IT Horizon Project: Docker Deployment Plan 
Version: 1.0
Date: October 2, 2024

Author: Marco Dumont

This document outlines deploying the MAP-IT Horizon project using Docker. It covers containerizing the application, building Docker images, and deploying to a target environment.

1. Project Overview
MAP-IT Horizon analyzes and visualizes research funding data from the European Commission's CORDIS database. Components include data ingestion, data storage (Dgraph), data analysis, and a user interface.

2. Deployment Environment
   - Target Environment: [Specify, e.g., cloud provider (AWS, Azure, GCP), on-premises server]
   - Operating System: [Specify, e.g., Linux distribution, Windows Server]
   - Docker Version: [Specify minimum required Docker version]
   - Orchestration Tool (Optional): [Specify if using Kubernetes, Docker Swarm, etc.]
3. Dockerization

    1. Application Components
        - Data Ingestion: Dockerfile with Python, requests, pandas.
        - Data Storage: Official Dgraph image or custom image.
        - Data Analysis: Dockerfile with Python, necessary libraries.
       - User Interface: Dockerfile with web framework (React, Flask), dependencies.
   2.  Dockerfiles
      - Base Images: Choose appropriate base images (Python, Node.js).
      - Dependencies: Install libraries/packages.
      - Application Code: Copy code into images.
      - Configuration: Define environment variables or files.
      - Expose Ports: Expose necessary ports (web server, database).
4. Image Building and Pushing
     - Build Images: docker build
     - Tag Images: Use appropriate names and versions.
     - Push Images: Push to a registry (Docker Hub, Amazon ECR, etc.).
5. Deployment
    1. Deployment Strategy
       - Single Host: All containers on one machine.
       - Multi-Host: Containers across multiple hosts.
       - Orchestration: Use Kubernetes, Docker Swarm.
   2. Deployment Steps
      - Pull Images: Pull from the registry.
      - Create Containers: docker run
      - Configure Networking: Allow container/external service communication.
      - Data Persistence: Mount volumes (Dgraph database).
      - Environment Variables: Set variables.
      - Start Containers: Start in order.
      - Verify Deployment: Check if running and accessible.
6. Monitoring and Maintenance
      - Logging: Centralized logging.
      - Monitoring Tools: Prometheus, Grafana.
      - Updates and Rollbacks: Update/rollback strategy.
      - Security: Update images, apply patches.
7. Rollback Plan
      - Backup Data: Back up Dgraph and persistent data.
      - Rollback Procedure: Define rollback steps.

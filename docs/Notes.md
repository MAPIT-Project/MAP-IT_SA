1. install docker
docker pull dgraph/standalone:latest
2. make the directory for Dgraph files: mkdir ~/dgraph

3. run docker standalone
docker run -it -p 5080:5080 -p 6080:6080 -p 8080:8080 \
  -p 9080:9080 -v ~/dgraph:/dgraph --name dgraph \
  dgraph/standalone:latest
  Note: the second time just use the command: sudo docker start dgraph
  checkout github project
  
  3.1. checkout project from Github.
  
4. create a python venv environment
  
5. pip install -r requirements.txt
  
6.  
  1. python ./src/devops/CORDISProjectSchemaInit.py 
  2. python ./src/etl/MAPITGraphBuilder.py \< dir where the project.csv is\>
  3. python ./src/etl/filter_topics.py \< dir where the list should go \(retrieve folder)\
  
  Step 2 takes a while (60 minutes)
  Step 1 also tests the docker & draph  installation
  Step 3 have fun
  
7. python src/retrieve/CORDISRetriever.py runs the retreiver (for now this takes a few minutes)
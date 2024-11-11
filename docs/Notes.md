1. install docker
docker pull dgraph/standalone:latest
2. make the directory for Dgraph files: mkdir ~/dgraph

3. run docker standalone
docker run -it -p 5080:5080 -p 6080:6080 -p 8080:8080 \
  -p 9080:9080 -v ~/dgraph:/dgraph --name dgraph \
  dgraph/standalone:latest
  
  checkout github project
  
  create a python venv environment
  
  pip install -r requirements.txt
  
  1. python ./src/devops/CORDISProjectSchemaInit.py 
  2. python ./src/etl/MAPITGraphBuilder.py \< dir where the project.csv is\>
  3. python ./src/etl/filter_topics.py \< dir where the list should go \(retrieve folder)\
  
  Step 2 takes a while (60 minutes)
  Step 1 also tests the docker & draph  installation
  Step 3 have fun
  
  python src/retreive/retreiver.py runs the retreiver (for now this takes a few minutes)
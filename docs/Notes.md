docker run -it -p 5080:5080 -p 6080:6080 -p 8080:8080 \
  -p 9080:9080 -v ~/dgraph:/dgraph --name dgraph \
  dgraph/standalone:latest
  
  
  url: localhost:5080
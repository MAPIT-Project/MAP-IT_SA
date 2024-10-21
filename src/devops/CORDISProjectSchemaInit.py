from pydgraph import DgraphClientStub, DgraphClient, Operation
import os
import logging
from pathlib import Path


def drop_create_schema_and_index(client):
  """
  Drops the database and creates the schema for the projects data and sets an index on the 'id' field.

  Args:
      client (dgraph.DgraphClient): The Dgraph client.
  """
  op = Operation(drop_all=True)
  client.alter(op)
  print("All data and schema dropped successfully!")
  
  
  
  schema = """
  id: string @index(exact) .
  acronym: string .
  status: string .
  title: string .
  startDate: datetime .
  endDate: datetime .
  totalCost: string .
  ecMaxContribution: string .
  legalBasis: string .
  topics: string .
  ecSignatureDate: datetime .
  frameworkProgramme: string .
  masterCall: string .
  subCall: string .
  fundingScheme: string .
  nature: string .
  objective: string .
  contentUpdateDate: datetime .
  rcn: string .
  grantDoi: string .
  """
  op = Operation(schema=schema)
  client.alter(op)
  print("Schema created successfully!")

if __name__ == "__main__":
  Path('./log/').mkdir(exist_ok=True)
  logger = logging.getLogger(__name__)
  logging.basicConfig(filename='log/MAPIT.log', filemode="a", encoding='utf-8', level=logging.INFO)  
    
  dgraph_url = "localhost:9080"
  if 'DGRAPH_URL' in os.environ:
      dgraph_url = os.environ['DGRAPH_URL']
    
  # Create a Dgraph client stub
  client_stub = DgraphClientStub(dgraph_url) 
  # Create a Dgraph client
  client = DgraphClient(client_stub)

  # Create schema and index
  drop_create_schema_and_index(client)

  # Close the client stub connection
  client_stub.close()
"""
Neo4j database configuration and connection management.
Provides a singleton connection pool for the Neo4j graph database.
"""

import os
import logging
from typing import Optional, List, Dict, Any
from contextlib import contextmanager

from neo4j import GraphDatabase, Session
from neo4j.exceptions import ServiceUnavailable, AuthError

logger = logging.getLogger(__name__)


class Neo4jConnection:
    """
    Manages Neo4j database connections using a singleton pattern.
    
    Usage:
        from app.core.neo4j_config import neo4j_db
        
        # Execute a query
        results = neo4j_db.execute_query("MATCH (n) RETURN n LIMIT 10")
        
        # Use a session context
        with neo4j_db.get_session() as session:
            result = session.run("MATCH (n:Project) RETURN count(n)")
    """
    
    _instance: Optional["Neo4jConnection"] = None
    _driver = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize Neo4j connection if not already done."""
        if Neo4jConnection._initialized:
            return
            
        self._uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self._user = os.getenv("NEO4J_USER", "neo4j")
        self._password = os.getenv("NEO4J_PASSWORD", "mapit_secure_password_2024")
        
        self._connect()
        Neo4jConnection._initialized = True
    
    def _connect(self) -> None:
        """Establish connection to Neo4j database."""
        try:
            self._driver = GraphDatabase.driver(
                self._uri,
                auth=(self._user, self._password),
                max_connection_lifetime=3600,
                max_connection_pool_size=50,
                connection_acquisition_timeout=60
            )
            
            # Verify connectivity
            self._driver.verify_connectivity()
            
            # Get server info
            with self._driver.session() as session:
                result = session.run("CALL dbms.components() YIELD name, versions RETURN name, versions")
                record = result.single()
                if record:
                    logger.info(f"✅ Neo4j connected: {record['name']} {record['versions']}")
                    
        except AuthError as e:
            logger.error(f"❌ Neo4j authentication failed: {e}")
            raise
        except ServiceUnavailable as e:
            logger.error(f"❌ Neo4j service unavailable: {e}")
            logger.info("💡 Hint: Is Neo4j container running? Try: docker-compose up neo4j -d")
            raise
        except Exception as e:
            logger.error(f"❌ Neo4j connection failed: {e}")
            raise
    
    @contextmanager
    def get_session(self, database: str = "neo4j"):
        """
        Get a Neo4j session as a context manager.
        
        Args:
            database: Database name (default: "neo4j")
            
        Yields:
            Neo4j Session object
        """
        session = None
        try:
            session = self._driver.session(database=database)
            yield session
        finally:
            if session:
                session.close()
    
    def execute_query(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
        database: str = "neo4j"
    ) -> List[Dict[str, Any]]:
        """
        Execute a Cypher query and return results as a list of dictionaries.
        
        Args:
            query: Cypher query string
            parameters: Query parameters (optional)
            database: Database name (default: "neo4j")
            
        Returns:
            List of result records as dictionaries
        """
        parameters = parameters or {}
        
        try:
            with self.get_session(database) as session:
                result = session.run(query, parameters)
                records = [record.data() for record in result]
                
                # Log query summary for debugging
                summary = result.consume()
                if summary.counters.nodes_created > 0:
                    logger.debug(f"Created {summary.counters.nodes_created} nodes")
                if summary.counters.relationships_created > 0:
                    logger.debug(f"Created {summary.counters.relationships_created} relationships")
                    
                return records
                
        except Exception as e:
            logger.error(f"❌ Query execution failed: {e}")
            logger.error(f"   Query: {query[:200]}...")
            raise
    
    def execute_write(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
        database: str = "neo4j"
    ) -> Dict[str, int]:
        """
        Execute a write query and return counters.
        
        Args:
            query: Cypher query string
            parameters: Query parameters (optional)
            database: Database name (default: "neo4j")
            
        Returns:
            Dictionary with operation counters
        """
        parameters = parameters or {}
        
        try:
            with self.get_session(database) as session:
                result = session.run(query, parameters)
                summary = result.consume()
                
                return {
                    "nodes_created": summary.counters.nodes_created,
                    "nodes_deleted": summary.counters.nodes_deleted,
                    "relationships_created": summary.counters.relationships_created,
                    "relationships_deleted": summary.counters.relationships_deleted,
                    "properties_set": summary.counters.properties_set,
                }
                
        except Exception as e:
            logger.error(f"❌ Write query failed: {e}")
            raise
    
    def test_connection(self) -> bool:
        """
        Test if Neo4j connection is working.
        
        Returns:
            True if connection is healthy, False otherwise
        """
        try:
            self._driver.verify_connectivity()
            result = self.execute_query("RETURN 1 as test")
            return len(result) > 0 and result[0].get("test") == 1
        except Exception as e:
            logger.error(f"❌ Connection test failed: {e}")
            return False
    
    def get_database_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the Neo4j database.
        
        Returns:
            Dictionary with node/relationship counts by label/type
        """
        try:
            # Get node counts by label
            node_query = """
            CALL db.labels() YIELD label
            CALL apoc.cypher.run('MATCH (n:`' + label + '`) RETURN count(n) as count', {}) YIELD value
            RETURN label, value.count as count
            """
            
            # Fallback if APOC not available
            simple_node_query = """
            MATCH (n)
            RETURN labels(n)[0] as label, count(n) as count
            """
            
            try:
                nodes = self.execute_query(node_query)
            except:
                nodes = self.execute_query(simple_node_query)
            
            # Get relationship counts
            rel_query = """
            MATCH ()-[r]->()
            RETURN type(r) as type, count(r) as count
            """
            relationships = self.execute_query(rel_query)
            
            return {
                "nodes": {n["label"]: n["count"] for n in nodes},
                "relationships": {r["type"]: r["count"] for r in relationships},
                "total_nodes": sum(n["count"] for n in nodes),
                "total_relationships": sum(r["count"] for r in relationships)
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get database stats: {e}")
            return {"error": str(e)}
    
    def close(self) -> None:
        """Close the Neo4j driver connection."""
        if self._driver:
            self._driver.close()
            Neo4jConnection._initialized = False
            logger.info("Neo4j connection closed")


# Global singleton instance
neo4j_db = Neo4jConnection()


# Convenience function for testing
def test_neo4j_connection() -> bool:
    """
    Test Neo4j connection and print status.
    
    Returns:
        True if connection successful
    """
    try:
        db = Neo4jConnection()
        if db.test_connection():
            stats = db.get_database_stats()
            print("✅ Neo4j connection successful!")
            print(f"   Total nodes: {stats.get('total_nodes', 'N/A')}")
            print(f"   Total relationships: {stats.get('total_relationships', 'N/A')}")
            return True
        else:
            print("❌ Neo4j connection test failed")
            return False
    except Exception as e:
        print(f"❌ Neo4j connection error: {e}")
        return False


if __name__ == "__main__":
    # Run connection test when executed directly
    test_neo4j_connection()


# TASK_01: Neo4j Container Setup

## Metadata
| Field | Value |
|-------|-------|
| **Task ID** | TASK_01 |
| **Day** | 1 |
| **Estimated Time** | 1 hour |
| **Dependencies** | None |
| **Blocks** | TASK_03, TASK_04 |
| **Priority** | Critical |

## Objective

Set up a Neo4j database container with APOC and GDS plugins, and create a Python configuration module for database connections.

## Context

NEWMAPIT currently uses PostgreSQL/Supabase for data storage. We're adding Neo4j to enable:
- Graph-based relationship traversal
- Structural similarity queries
- Multi-hop queries (e.g., "organizations that collaborated on projects in Cluster 4")

The existing project uses Docker for containerization. We'll add Neo4j to the existing `docker-compose.yml`.

## Files to Create/Modify

| Action | File Path |
|--------|-----------|
| MODIFY | `docker-compose.yml` |
| CREATE | `app/core/neo4j_config.py` |
| MODIFY | `requirements.txt` |
| CREATE | `.env` additions |

## Implementation Steps

### Step 1: Update docker-compose.yml

Add the Neo4j service to the existing docker-compose file.

**File: `docker-compose.yml`**

Add this service block (keep existing services):

```yaml
  neo4j:
    image: neo4j:5.15.0-community
    container_name: mapit-neo4j
    ports:
      - "7474:7474"  # HTTP Browser
      - "7687:7687"  # Bolt Protocol
    environment:
      - NEO4J_AUTH=neo4j/${NEO4J_PASSWORD:-mapit_secure_password_2024}
      - NEO4J_PLUGINS=["apoc", "graph-data-science"]
      - NEO4J_dbms_security_procedures_unrestricted=apoc.*,gds.*
      - NEO4J_dbms_security_procedures_allowlist=apoc.*,gds.*
      - NEO4J_dbms_memory_heap_initial__size=512m
      - NEO4J_dbms_memory_heap_max__size=2G
      - NEO4J_dbms_memory_pagecache_size=512m
    volumes:
      - neo4j_data:/data
      - neo4j_logs:/logs
      - neo4j_plugins:/plugins
      - ./neo4j/import:/var/lib/neo4j/import
    healthcheck:
      test: ["CMD", "wget", "-q", "--spider", "http://localhost:7474"]
      interval: 30s
      timeout: 10s
      retries: 5
    restart: unless-stopped

# Add to volumes section:
volumes:
  neo4j_data:
  neo4j_logs:
  neo4j_plugins:
```

### Step 2: Create Neo4j Import Directory

```bash
mkdir -p neo4j/import
```

### Step 3: Add Environment Variables

**File: `.env`** (add these lines):

```bash
# Neo4j Configuration
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=mapit_secure_password_2024
```

### Step 4: Update requirements.txt

**File: `requirements.txt`** (add these lines):

```
# Neo4j
neo4j>=5.14.0
```

### Step 5: Create Neo4j Configuration Module

**File: `app/core/neo4j_config.py`**

```python
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
```

### Step 6: Start Neo4j Container

```bash
# Start only Neo4j (or all services)
docker-compose up neo4j -d

# Check container status
docker-compose ps

# View logs
docker-compose logs neo4j
```

### Step 7: Verify Installation

```bash
# Install the neo4j Python driver
pip install neo4j>=5.14.0

# Test the connection module
python -c "from app.core.neo4j_config import test_neo4j_connection; test_neo4j_connection()"
```

## Acceptance Criteria

- [ ] Neo4j container starts successfully with `docker-compose up neo4j -d`
- [ ] Neo4j browser accessible at http://localhost:7474
- [ ] Can login with credentials from `.env`
- [ ] `neo4j_config.py` module created and importable
- [ ] `test_neo4j_connection()` returns `True`
- [ ] APOC plugin available (test with: `RETURN apoc.version()`)
- [ ] No import errors when loading the module

## Verification Commands

```bash
# 1. Check container is running
docker-compose ps | grep neo4j

# 2. Check Neo4j logs for errors
docker-compose logs neo4j | tail -20

# 3. Test Python connection
cd /home/anmar/Documents/VSCODE_REPOS/MAPIT/NEWMAPIT/MAP-IT_SA
python -c "
from app.core.neo4j_config import neo4j_db
print('Testing connection...')
if neo4j_db.test_connection():
    print('✅ Connection successful!')
    stats = neo4j_db.get_database_stats()
    print(f'Stats: {stats}')
else:
    print('❌ Connection failed')
"

# 4. Test APOC availability via Cypher
docker exec mapit-neo4j cypher-shell -u neo4j -p mapit_secure_password_2024 "RETURN apoc.version() as version"

# 5. Test GDS availability
docker exec mapit-neo4j cypher-shell -u neo4j -p mapit_secure_password_2024 "RETURN gds.version() as version"
```

## Troubleshooting

### Container won't start
```bash
# Check for port conflicts
lsof -i :7474
lsof -i :7687

# Remove old volumes and restart
docker-compose down -v
docker-compose up neo4j -d
```

### Authentication errors
```bash
# Reset password by removing data volume
docker-compose down
docker volume rm mapit_neo4j_data
docker-compose up neo4j -d
```

### APOC/GDS plugins not loading
```bash
# Check plugin directory
docker exec mapit-neo4j ls -la /var/lib/neo4j/plugins/

# Verify environment variables
docker exec mapit-neo4j env | grep NEO4J
```

## Notes for Agent

1. The existing `docker-compose.yml` may have other services - preserve them
2. Use environment variables from `.env` for credentials
3. The `neo4j_config.py` follows the same pattern as existing config files in `app/core/`
4. The singleton pattern ensures only one connection pool exists
5. Error handling should be graceful - log errors but don't crash the application


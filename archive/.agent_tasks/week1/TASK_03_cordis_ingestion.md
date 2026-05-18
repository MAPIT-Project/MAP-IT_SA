# TASK_03: CORDIS Data Ingestion to Neo4j

## Metadata
| Field | Value |
|-------|-------|
| **Task ID** | TASK_03 |
| **Day** | 2 |
| **Estimated Time** | 2 hours |
| **Dependencies** | TASK_01 (Neo4j running), TASK_02 (Data downloaded) |
| **Blocks** | TASK_04, TASK_07 |
| **Priority** | Critical |

## Objective

Create a data ingestion script that loads the CORDIS Horizon Europe dataset into Neo4j, creating nodes for Projects, Organizations, Topics, Clusters, Countries, and their relationships.

## Context

The CORDIS dataset is in CSV/JSON format. We need to transform this into a graph structure:

```
(:Organization)-[:PARTICIPATES_IN]->(:Project)-[:FUNDED_UNDER]->(:Topic)
                                          |
                                          +--[:TARGETS]->(:Cluster)
```

Key transformations:
- Extract organization data from project records
- Parse topic codes to identify clusters (e.g., `HORIZON-CL4-2024-DATA-01` → Cluster 4)
- Create Country and EntityType reference nodes
- Build PARTNERS_WITH relationships from co-participation

## Files to Create

| Action | File Path |
|--------|-----------|
| CREATE | `scripts/ingest_cordis_to_neo4j.py` |
| CREATE | `app/services/data_intelligence/__init__.py` |

## Implementation Steps

### Step 1: Create Data Intelligence Package

```bash
mkdir -p app/services/data_intelligence
touch app/services/data_intelligence/__init__.py
```

**File: `app/services/data_intelligence/__init__.py`**

```python
"""
Data Intelligence package for graph-based and hybrid search capabilities.
"""

from .graph_service import GraphSearchService

__all__ = ["GraphSearchService"]
```

### Step 2: Create Ingestion Script

**File: `scripts/ingest_cordis_to_neo4j.py`**

```python
#!/usr/bin/env python3
"""
Ingest CORDIS Horizon Europe dataset into Neo4j graph database.

This script:
1. Creates schema constraints and indexes
2. Loads reference data (clusters, entity types, countries)
3. Loads projects with their topics and clusters
4. Loads organizations and their participation relationships
5. Creates computed relationships (PARTNERS_WITH)

Usage:
    python scripts/ingest_cordis_to_neo4j.py [--data-dir DATA_DIR] [--clear]
"""

import os
import sys
import json
import re
import argparse
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass

import pandas as pd
from tqdm import tqdm

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.neo4j_config import neo4j_db

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class IngestionStats:
    """Track ingestion statistics."""
    projects_created: int = 0
    organizations_created: int = 0
    topics_created: int = 0
    clusters_linked: int = 0
    relationships_created: int = 0
    errors: int = 0
    start_time: datetime = None
    end_time: datetime = None


class CORDISIngester:
    """
    Ingests CORDIS Horizon Europe dataset into Neo4j.
    """

    # Horizon Europe cluster mapping
    CLUSTER_MAPPING = {
        "CL1": {"code": "CLUSTER-1", "name": "Health", "pillar": "Pillar II"},
        "CL2": {"code": "CLUSTER-2", "name": "Culture, Creativity and Inclusive Society", "pillar": "Pillar II"},
        "CL3": {"code": "CLUSTER-3", "name": "Civil Security for Society", "pillar": "Pillar II"},
        "CL4": {"code": "CLUSTER-4", "name": "Digital, Industry and Space", "pillar": "Pillar II"},
        "CL5": {"code": "CLUSTER-5", "name": "Climate, Energy and Mobility", "pillar": "Pillar II"},
        "CL6": {"code": "CLUSTER-6", "name": "Food, Bioeconomy, Natural Resources, Agriculture and Environment", "pillar": "Pillar II"},
    }

    # Additional programme codes
    PROGRAMME_MAPPING = {
        "ERC": {"code": "ERC", "name": "European Research Council", "pillar": "Pillar I"},
        "MSCA": {"code": "MSCA", "name": "Marie Skłodowska-Curie Actions", "pillar": "Pillar I"},
        "INFRA": {"code": "INFRA", "name": "Research Infrastructures", "pillar": "Pillar I"},
        "EIC": {"code": "EIC", "name": "European Innovation Council", "pillar": "Pillar III"},
        "EIT": {"code": "EIT", "name": "European Institute of Innovation and Technology", "pillar": "Pillar III"},
        "WIDERA": {"code": "WIDERA", "name": "Widening Participation and Strengthening ERA", "pillar": "Pillar III"},
    }

    # Entity type mapping
    ENTITY_TYPES = {
        "HES": "Higher or Secondary Education Establishments",
        "REC": "Research Organisations",
        "PRC": "Private for-profit entities (excluding HES)",
        "PUB": "Public bodies (excluding RES and HES)",
        "OTH": "Other",
    }

    # EU Member States
    EU_MEMBER_STATES = [
        "AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR",
        "DE", "GR", "HU", "IE", "IT", "LV", "LT", "LU", "MT", "NL",
        "PL", "PT", "RO", "SK", "SI", "ES", "SE"
    ]

    def __init__(self, data_dir: Path):
        """
        Initialize the ingester.

        Args:
            data_dir: Directory containing CORDIS data files
        """
        self.data_dir = Path(data_dir)
        self.db = neo4j_db
        self.stats = IngestionStats()

        # Verify data directory exists
        if not self.data_dir.exists():
            raise FileNotFoundError(f"Data directory not found: {self.data_dir}")

        logger.info(f"Initialized CORDIS ingester with data from: {self.data_dir}")

    def create_constraints_and_indexes(self) -> None:
        """Create uniqueness constraints and indexes for optimal performance."""

        logger.info("📊 Creating constraints and indexes...")

        constraints = [
            "CREATE CONSTRAINT project_id IF NOT EXISTS FOR (p:Project) REQUIRE p.id IS UNIQUE",
            "CREATE CONSTRAINT org_id IF NOT EXISTS FOR (o:Organization) REQUIRE o.id IS UNIQUE",
            "CREATE CONSTRAINT topic_code IF NOT EXISTS FOR (t:Topic) REQUIRE t.code IS UNIQUE",
            "CREATE CONSTRAINT cluster_code IF NOT EXISTS FOR (c:Cluster) REQUIRE c.code IS UNIQUE",
            "CREATE CONSTRAINT programme_code IF NOT EXISTS FOR (pr:Programme) REQUIRE pr.code IS UNIQUE",
            "CREATE CONSTRAINT country_iso IF NOT EXISTS FOR (co:Country) REQUIRE co.isoCode IS UNIQUE",
            "CREATE CONSTRAINT entity_type_code IF NOT EXISTS FOR (et:EntityType) REQUIRE et.code IS UNIQUE",
        ]

        indexes = [
            "CREATE INDEX project_acronym IF NOT EXISTS FOR (p:Project) ON (p.acronym)",
            "CREATE INDEX project_status IF NOT EXISTS FOR (p:Project) ON (p.status)",
            "CREATE INDEX org_name IF NOT EXISTS FOR (o:Organization) ON (o.name)",
            "CREATE INDEX org_country IF NOT EXISTS FOR (o:Organization) ON (o.country)",
        ]

        for constraint in constraints:
            try:
                self.db.execute_query(constraint)
                logger.debug(f"✅ Created: {constraint[:60]}...")
            except Exception as e:
                if "already exists" in str(e).lower():
                    logger.debug(f"⏭️ Already exists: {constraint[:40]}...")
                else:
                    logger.warning(f"⚠️ Constraint warning: {e}")

        for index in indexes:
            try:
                self.db.execute_query(index)
                logger.debug(f"✅ Created: {index[:60]}...")
            except Exception as e:
                if "already exists" in str(e).lower():
                    logger.debug(f"⏭️ Already exists: {index[:40]}...")
                else:
                    logger.warning(f"⚠️ Index warning: {e}")

        logger.info("✅ Constraints and indexes ready")

    def load_reference_data(self) -> None:
        """Load reference data: clusters, programmes, entity types, countries."""

        logger.info("📚 Loading reference data...")

        # Load clusters
        for code, info in self.CLUSTER_MAPPING.items():
            self.db.execute_query("""
                MERGE (c:Cluster {code: $code})
                SET c.name = $name, c.pillar = $pillar, c.shortCode = $shortCode
            """, {**info, "shortCode": code})

        # Load programmes
        for code, info in self.PROGRAMME_MAPPING.items():
            self.db.execute_query("""
                MERGE (p:Programme {code: $code})
                SET p.name = $name, p.pillar = $pillar
            """, info)

        # Load entity types
        for code, name in self.ENTITY_TYPES.items():
            self.db.execute_query("""
                MERGE (et:EntityType {code: $code})
                SET et.name = $name
            """, {"code": code, "name": name})

        # Load countries from reference file if available
        countries_file = self.data_dir / "reference" / "countries.json"
        if countries_file.exists():
            with open(countries_file, 'r') as f:
                countries = json.load(f)
                for country in countries:
                    iso = country.get("isoCode") or country.get("code")
                    name = country.get("name") or country.get("label")
                    if iso and name:
                        is_eu = iso in self.EU_MEMBER_STATES
                        self.db.execute_query("""
                            MERGE (co:Country {isoCode: $iso})
                            SET co.name = $name, co.isEU = $isEU
                        """, {"iso": iso, "name": name, "isEU": is_eu})
        else:
            # Create basic EU countries
            for iso in self.EU_MEMBER_STATES:
                self.db.execute_query("""
                    MERGE (co:Country {isoCode: $iso})
                    SET co.isEU = true
                """, {"iso": iso})

        logger.info("✅ Reference data loaded")

    def extract_cluster_from_topic(self, topic_code: str) -> Optional[str]:
        """
        Extract cluster code from topic identifier.

        Examples:
            HORIZON-CL4-2024-DATA-01 → CLUSTER-4
            HORIZON-MSCA-2024-DN-01 → MSCA
            HORIZON-ERC-2024-STG → ERC
        """
        if not topic_code:
            return None

        topic_upper = topic_code.upper()

        # Check for cluster pattern (CL1-CL6)
        match = re.search(r'HORIZON-CL(\d)', topic_upper)
        if match:
            return f"CLUSTER-{match.group(1)}"

        # Check for programme patterns
        for prog_code in self.PROGRAMME_MAPPING.keys():
            if prog_code in topic_upper:
                return prog_code

        return None

    def load_projects(self, batch_size: int = 500) -> None:
        """
        Load projects from CSV file.

        Args:
            batch_size: Number of projects to process per batch
        """
        logger.info("📥 Loading projects...")

        # Find project file
        project_file = None
        for pattern in ["project.csv", "*project*.csv", "cordis*project*.csv"]:
            matches = list(self.data_dir.glob(pattern))
            if matches:
                project_file = matches[0]
                break

        if not project_file:
            raise FileNotFoundError("No project CSV file found in data directory")

        logger.info(f"📄 Reading: {project_file}")

        # Read CSV
        df = pd.read_csv(project_file, low_memory=False, encoding='utf-8')
        total_projects = len(df)
        logger.info(f"📊 Found {total_projects} projects")

        # Process in batches
        for batch_start in tqdm(range(0, total_projects, batch_size), desc="Projects"):
            batch = df.iloc[batch_start:batch_start + batch_size]

            for _, row in batch.iterrows():
                try:
                    self._process_project(row)
                    self.stats.projects_created += 1
                except Exception as e:
                    logger.error(f"Error processing project {row.get('id', 'unknown')}: {e}")
                    self.stats.errors += 1

        logger.info(f"✅ Loaded {self.stats.projects_created} projects")

    def _process_project(self, row: pd.Series) -> None:
        """Process a single project row."""

        # Extract project data
        project_id = str(row.get('id', ''))
        if not project_id or project_id == 'nan':
            return

        # Clean and prepare data
        project_data = {
            "id": project_id,
            "acronym": self._clean_string(row.get('acronym')),
            "title": self._clean_string(row.get('title')),
            "objective": self._clean_string(row.get('objective', ''))[:5000],
            "startDate": self._clean_string(row.get('startDate')),
            "endDate": self._clean_string(row.get('endDate')),
            "totalCost": self._parse_float(row.get('totalCost')),
            "ecMaxContribution": self._parse_float(row.get('ecMaxContribution')),
            "status": self._clean_string(row.get('status')),
            "legalBasis": self._clean_string(row.get('legalBasis')),
            "fundingScheme": self._clean_string(row.get('fundingScheme')),
        }

        # Create project node
        self.db.execute_query("""
            MERGE (p:Project {id: $id})
            SET p += {
                acronym: $acronym,
                title: $title,
                objective: $objective,
                startDate: $startDate,
                endDate: $endDate,
                totalCost: $totalCost,
                ecMaxContribution: $ecMaxContribution,
                status: $status,
                legalBasis: $legalBasis,
                fundingScheme: $fundingScheme
            }
        """, project_data)

        # Process topics
        topics = row.get('topics', '')
        if pd.notna(topics) and topics:
            topic_codes = str(topics).split(';')
            for topic_code in topic_codes:
                topic_code = topic_code.strip()
                if topic_code:
                    # Create topic and link to project
                    self.db.execute_query("""
                        MATCH (p:Project {id: $project_id})
                        MERGE (t:Topic {code: $topic_code})
                        MERGE (p)-[:FUNDED_UNDER]->(t)
                    """, {"project_id": project_id, "topic_code": topic_code})
                    self.stats.topics_created += 1

                    # Link to cluster
                    cluster_code = self.extract_cluster_from_topic(topic_code)
                    if cluster_code:
                        self.db.execute_query("""
                            MATCH (p:Project {id: $project_id})
                            MATCH (c:Cluster {code: $cluster_code})
                            MERGE (p)-[:TARGETS]->(c)
                        """, {"project_id": project_id, "cluster_code": cluster_code})
                        self.stats.clusters_linked += 1

        # Process organizations (if embedded in project row)
        self._process_organizations_from_project(row, project_id)

    def _process_organizations_from_project(self, row: pd.Series, project_id: str) -> None:
        """Extract and process organizations from a project row."""

        # Coordinator
        coordinator_name = row.get('coordinatorOrganisation') or row.get('coordinator')
        coordinator_country = row.get('coordinatorCountry')

        if pd.notna(coordinator_name) and coordinator_name:
            org_id = self._generate_org_id(str(coordinator_name), str(coordinator_country or ''))

            self.db.execute_query("""
                MERGE (o:Organization {id: $org_id})
                SET o.name = $name, o.country = $country, o.isCoordinator = true
                WITH o
                MATCH (p:Project {id: $project_id})
                MERGE (o)-[r:PARTICIPATES_IN]->(p)
                SET r.role = 'coordinator'
            """, {
                "org_id": org_id,
                "name": self._clean_string(coordinator_name),
                "country": self._clean_string(coordinator_country),
                "project_id": project_id
            })
            self.stats.organizations_created += 1
            self.stats.relationships_created += 1

            # Link to country
            if coordinator_country:
                self.db.execute_query("""
                    MATCH (o:Organization {id: $org_id})
                    MERGE (co:Country {isoCode: $country})
                    MERGE (o)-[:LOCATED_IN]->(co)
                """, {"org_id": org_id, "country": str(coordinator_country).upper()})

        # Participants (may be in 'participants' column as semicolon-separated)
        participants = row.get('participants', '')
        if pd.notna(participants) and participants:
            for participant in str(participants).split(';'):
                participant = participant.strip()
                if participant and participant != coordinator_name:
                    org_id = self._generate_org_id(participant, '')

                    self.db.execute_query("""
                        MERGE (o:Organization {id: $org_id})
                        SET o.name = $name
                        WITH o
                        MATCH (p:Project {id: $project_id})
                        MERGE (o)-[r:PARTICIPATES_IN]->(p)
                        SET r.role = 'participant'
                    """, {
                        "org_id": org_id,
                        "name": self._clean_string(participant),
                        "project_id": project_id
                    })
                    self.stats.organizations_created += 1
                    self.stats.relationships_created += 1

    def load_organizations_file(self, batch_size: int = 1000) -> None:
        """Load organizations from separate CSV if available."""

        org_file = None
        for pattern in ["organization.csv", "*organization*.csv"]:
            matches = list(self.data_dir.glob(pattern))
            if matches:
                org_file = matches[0]
                break

        if not org_file:
            logger.info("No separate organization file found (orgs loaded from projects)")
            return

        logger.info(f"📥 Loading organizations from: {org_file}")

        df = pd.read_csv(org_file, low_memory=False, encoding='utf-8')
        logger.info(f"📊 Found {len(df)} organization records")

        for batch_start in tqdm(range(0, len(df), batch_size), desc="Organizations"):
            batch = df.iloc[batch_start:batch_start + batch_size]

            for _, row in batch.iterrows():
                try:
                    project_id = str(row.get('projectID', row.get('projectId', '')))
                    org_id = str(row.get('organisationID', row.get('organizationId', row.get('id', ''))))

                    if not project_id or not org_id or project_id == 'nan':
                        continue

                    org_data = {
                        "org_id": org_id,
                        "project_id": project_id,
                        "name": self._clean_string(row.get('name', row.get('legalName'))),
                        "shortName": self._clean_string(row.get('shortName')),
                        "country": self._clean_string(row.get('country')),
                        "city": self._clean_string(row.get('city')),
                        "activityType": self._clean_string(row.get('activityType')),
                        "ecContribution": self._parse_float(row.get('ecContribution')),
                        "role": self._clean_string(row.get('role', 'participant')),
                    }

                    self.db.execute_query("""
                        MERGE (o:Organization {id: $org_id})
                        SET o.name = $name,
                            o.shortName = $shortName,
                            o.country = $country,
                            o.city = $city,
                            o.activityType = $activityType
                        WITH o
                        MATCH (p:Project {id: $project_id})
                        MERGE (o)-[r:PARTICIPATES_IN]->(p)
                        SET r.role = $role, r.ecContribution = $ecContribution
                    """, org_data)

                    self.stats.organizations_created += 1
                    self.stats.relationships_created += 1

                    # Link to country
                    if org_data["country"]:
                        self.db.execute_query("""
                            MATCH (o:Organization {id: $org_id})
                            MERGE (co:Country {isoCode: $country})
                            MERGE (o)-[:LOCATED_IN]->(co)
                        """, {"org_id": org_id, "country": org_data["country"].upper()})

                    # Link to entity type
                    if org_data["activityType"]:
                        self.db.execute_query("""
                            MATCH (o:Organization {id: $org_id})
                            MERGE (et:EntityType {code: $type})
                            MERGE (o)-[:IS_TYPE]->(et)
                        """, {"org_id": org_id, "type": org_data["activityType"]})

                except Exception as e:
                    logger.error(f"Error processing organization: {e}")
                    self.stats.errors += 1

    def create_partnership_relationships(self) -> None:
        """Create PARTNERS_WITH relationships based on co-participation in projects."""

        logger.info("🔗 Creating partnership relationships...")

        # This query finds organizations that participated in the same projects
        # and creates a PARTNERS_WITH relationship with a count of shared projects
        query = """
        MATCH (o1:Organization)-[:PARTICIPATES_IN]->(p:Project)<-[:PARTICIPATES_IN]-(o2:Organization)
        WHERE o1.id < o2.id
        WITH o1, o2, COUNT(DISTINCT p) as projectCount, SUM(p.ecMaxContribution) as totalValue
        WHERE projectCount >= 1
        MERGE (o1)-[r:PARTNERS_WITH]-(o2)
        SET r.projectCount = projectCount,
            r.totalValue = totalValue,
            r.updatedAt = datetime()
        RETURN count(r) as partnerships_created
        """

        try:
            result = self.db.execute_query(query)
            partnerships = result[0].get('partnerships_created', 0) if result else 0
            logger.info(f"✅ Created {partnerships} partnership relationships")
        except Exception as e:
            logger.error(f"Error creating partnerships: {e}")

    def _clean_string(self, value) -> str:
        """Clean a string value, handling NaN and None."""
        if pd.isna(value) or value is None:
            return ""
        return str(value).strip()

    def _parse_float(self, value) -> float:
        """Parse a float value, handling various formats."""
        if pd.isna(value) or value is None:
            return 0.0
        try:
            # Handle string representations with commas
            if isinstance(value, str):
                value = value.replace(',', '').replace(' ', '')
            return float(value)
        except (ValueError, TypeError):
            return 0.0

    def _generate_org_id(self, name: str, country: str) -> str:
        """Generate a unique ID for an organization."""
        import hashlib
        key = f"{name.lower().strip()}_{country.lower().strip()}"
        return hashlib.md5(key.encode()).hexdigest()[:16]

    def clear_database(self) -> None:
        """Clear all nodes and relationships from the database."""
        logger.warning("🗑️ Clearing database...")
        self.db.execute_query("MATCH (n) DETACH DELETE n")
        logger.info("✅ Database cleared")

    def run(self, clear_first: bool = False) -> IngestionStats:
        """
        Run the complete ingestion pipeline.

        Args:
            clear_first: If True, clear the database before ingestion

        Returns:
            IngestionStats with counts and timing
        """
        self.stats.start_time = datetime.now()

        logger.info("=" * 60)
        logger.info("CORDIS → Neo4j Ingestion Pipeline")
        logger.info("=" * 60)

        if clear_first:
            self.clear_database()

        # Step 1: Create schema
        self.create_constraints_and_indexes()

        # Step 2: Load reference data
        self.load_reference_data()

        # Step 3: Load projects
        self.load_projects()

        # Step 4: Load organizations (if separate file exists)
        self.load_organizations_file()

        # Step 5: Create partnership relationships
        self.create_partnership_relationships()

        self.stats.end_time = datetime.now()

        # Print summary
        self._print_summary()

        return self.stats

    def _print_summary(self) -> None:
        """Print ingestion summary."""
        duration = (self.stats.end_time - self.stats.start_time).total_seconds()

        logger.info("\n" + "=" * 60)
        logger.info("INGESTION SUMMARY")
        logger.info("=" * 60)
        logger.info(f"⏱️ Duration: {duration:.1f} seconds")
        logger.info(f"📊 Projects created: {self.stats.projects_created}")
        logger.info(f"🏢 Organizations created: {self.stats.organizations_created}")
        logger.info(f"🏷️ Topics created: {self.stats.topics_created}")
        logger.info(f"🎯 Cluster links: {self.stats.clusters_linked}")
        logger.info(f"🔗 Relationships created: {self.stats.relationships_created}")
        logger.info(f"❌ Errors: {self.stats.errors}")

        # Get final database stats
        stats = self.db.get_database_stats()
        logger.info("\n📈 Final Database State:")
        for label, count in stats.get("nodes", {}).items():
            logger.info(f"   {label}: {count}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Ingest CORDIS data into Neo4j")
    parser.add_argument(
        "--data-dir",
        type=str,
        default="data/cordis",
        help="Directory containing CORDIS data files"
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear database before ingestion"
    )

    args = parser.parse_args()

    # Resolve path
    script_dir = Path(__file__).parent.parent
    data_dir = script_dir / args.data_dir

    try:
        ingester = CORDISIngester(data_dir)
        stats = ingester.run(clear_first=args.clear)

        if stats.errors > 0:
            logger.warning(f"Completed with {stats.errors} errors")
            return 1
        else:
            logger.info("\n✅ Ingestion completed successfully!")
            return 0

    except Exception as e:
        logger.error(f"❌ Ingestion failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
```

### Step 3: Run the Ingestion

```bash
cd /home/anmar/Documents/VSCODE_REPOS/MAPIT/NEWMAPIT/MAP-IT_SA

# First run (with clear to start fresh)
python scripts/ingest_cordis_to_neo4j.py --clear

# Subsequent runs (incremental)
python scripts/ingest_cordis_to_neo4j.py
```

## Acceptance Criteria

- [ ] Script runs without errors
- [ ] Projects loaded into Neo4j (check count > 1000)
- [ ] Organizations created with PARTICIPATES_IN relationships
- [ ] Topics created with FUNDED_UNDER relationships
- [ ] Clusters linked via TARGETS relationships
- [ ] Reference data (Countries, EntityTypes) created
- [ ] PARTNERS_WITH relationships computed
- [ ] Database stats show reasonable numbers

## Verification Commands

```bash
# 1. Run ingestion
python scripts/ingest_cordis_to_neo4j.py --clear

# 2. Check node counts via Python
python -c "
from app.core.neo4j_config import neo4j_db
stats = neo4j_db.get_database_stats()
print('Node counts:')
for label, count in stats.get('nodes', {}).items():
    print(f'  {label}: {count}')
print('Relationship counts:')
for rel_type, count in stats.get('relationships', {}).items():
    print(f'  {rel_type}: {count}')
"

# 3. Test queries via cypher-shell
docker exec mapit-neo4j cypher-shell -u neo4j -p mapit_secure_password_2024 \
    "MATCH (p:Project) RETURN count(p) as projects"

docker exec mapit-neo4j cypher-shell -u neo4j -p mapit_secure_password_2024 \
    "MATCH (o:Organization)-[:PARTICIPATES_IN]->(p:Project) RETURN count(DISTINCT o) as orgs"

docker exec mapit-neo4j cypher-shell -u neo4j -p mapit_secure_password_2024 \
    "MATCH (p:Project)-[:TARGETS]->(c:Cluster) RETURN c.code, count(p) ORDER BY c.code"

# 4. Sample project query
docker exec mapit-neo4j cypher-shell -u neo4j -p mapit_secure_password_2024 \
    "MATCH (p:Project) RETURN p.acronym, p.title LIMIT 5"
```

## Expected Database State

After successful ingestion:

```
Nodes:
  Project: 10,000-20,000+
  Organization: 20,000-50,000+
  Topic: 500-2,000+
  Cluster: 6-11
  Programme: 6+
  Country: 30-50+
  EntityType: 5

Relationships:
  PARTICIPATES_IN: 50,000-200,000+
  FUNDED_UNDER: 10,000-20,000+
  TARGETS: 10,000-20,000+
  LOCATED_IN: 20,000-50,000+
  PARTNERS_WITH: 10,000-100,000+
```

## Notes for Agent

1. The CSV column names may vary - the script handles common variations
2. Processing 15,000+ projects takes 5-15 minutes depending on hardware
3. The `--clear` flag drops all data - use carefully
4. Memory usage may be high for large batches - reduce batch_size if needed
5. Partnership creation can be slow - it's a heavy operation
6. Check logs for specific errors if counts are lower than expected

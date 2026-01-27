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

import argparse
import logging
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

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
        "HLTH": {"code": "HLTH", "name": "Health Cluster", "pillar": "Pillar II"},
        "DATA": {"code": "DATA", "name": "Data and Computing", "pillar": "Pillar II"},
        "HUMAN": {"code": "HUMAN", "name": "Human-centric AI", "pillar": "Pillar II"},
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
    
    # Associated Countries
    ASSOCIATED_COUNTRIES = [
        "NO", "IS", "IL", "UK", "CH", "TR", "UA", "MD", "ME", "RS",
        "AL", "MK", "BA", "GE", "AM", "TN", "MA", "FO", "EL"
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
                if "already exists" in str(e).lower() or "equivalent" in str(e).lower():
                    logger.debug(f"⏭️ Already exists: {constraint[:40]}...")
                else:
                    logger.warning(f"⚠️ Constraint warning: {e}")
        
        for index in indexes:
            try:
                self.db.execute_query(index)
                logger.debug(f"✅ Created: {index[:60]}...")
            except Exception as e:
                if "already exists" in str(e).lower() or "equivalent" in str(e).lower():
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
        logger.info(f"   ✅ Loaded {len(self.CLUSTER_MAPPING)} clusters")
        
        # Load programmes
        for code, info in self.PROGRAMME_MAPPING.items():
            self.db.execute_query("""
                MERGE (p:Programme {code: $code})
                SET p.name = $name, p.pillar = $pillar
            """, info)
        logger.info(f"   ✅ Loaded {len(self.PROGRAMME_MAPPING)} programmes")
        
        # Load entity types
        for code, name in self.ENTITY_TYPES.items():
            self.db.execute_query("""
                MERGE (et:EntityType {code: $code})
                SET et.name = $name
            """, {"code": code, "name": name})
        logger.info(f"   ✅ Loaded {len(self.ENTITY_TYPES)} entity types")
        
        # Load EU countries
        for iso in self.EU_MEMBER_STATES:
            self.db.execute_query("""
                MERGE (co:Country {isoCode: $iso})
                SET co.isEU = true, co.isAssociated = false
            """, {"iso": iso})
        
        # Load Associated countries
        for iso in self.ASSOCIATED_COUNTRIES:
            self.db.execute_query("""
                MERGE (co:Country {isoCode: $iso})
                SET co.isEU = false, co.isAssociated = true
            """, {"iso": iso})
        
        logger.info(f"   ✅ Loaded {len(self.EU_MEMBER_STATES)} EU + {len(self.ASSOCIATED_COUNTRIES)} associated countries")
        logger.info("✅ Reference data loaded")
    
    def extract_cluster_from_topic(self, topic_code: str) -> str | None:
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
        
        # Check for HLTH pattern (Health cluster)
        if 'HLTH' in topic_upper or 'HEALTH' in topic_upper:
            return "CLUSTER-1"
        
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
        project_file = self.data_dir / "project.csv"
        
        if not project_file.exists():
            raise FileNotFoundError(f"Project CSV not found: {project_file}")
        
        logger.info(f"📄 Reading: {project_file}")
        
        # Read CSV with semicolon delimiter, handle malformed rows
        df = pd.read_csv(
            project_file, 
            sep=';', 
            low_memory=False, 
            encoding='utf-8',
            quotechar='"',
            on_bad_lines='skip'  # Skip malformed rows
        )
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
                        # Handle both Cluster and Programme nodes
                        if cluster_code.startswith("CLUSTER"):
                            self.db.execute_query("""
                                MATCH (p:Project {id: $project_id})
                                MERGE (c:Cluster {code: $cluster_code})
                                MERGE (p)-[:TARGETS]->(c)
                            """, {"project_id": project_id, "cluster_code": cluster_code})
                        else:
                            self.db.execute_query("""
                                MATCH (p:Project {id: $project_id})
                                MERGE (pr:Programme {code: $cluster_code})
                                MERGE (p)-[:TARGETS]->(pr)
                            """, {"project_id": project_id, "cluster_code": cluster_code})
                        self.stats.clusters_linked += 1
    
    def load_organizations(self, batch_size: int = 1000) -> None:
        """Load organizations from CSV file."""
        
        org_file = self.data_dir / "organization.csv"
        
        if not org_file.exists():
            logger.warning("No organization.csv found")
            return
        
        logger.info(f"📥 Loading organizations from: {org_file}")
        
        df = pd.read_csv(
            org_file, 
            sep=';', 
            low_memory=False, 
            encoding='utf-8',
            quotechar='"',
            on_bad_lines='skip'  # Skip malformed rows
        )
        logger.info(f"📊 Found {len(df)} organization records")
        
        for batch_start in tqdm(range(0, len(df), batch_size), desc="Organizations"):
            batch = df.iloc[batch_start:batch_start + batch_size]
            
            for _, row in batch.iterrows():
                try:
                    project_id = str(row.get('projectID', ''))
                    org_id = str(row.get('organisationID', row.get('organizationID', '')))
                    
                    if not project_id or not org_id or project_id == 'nan' or org_id == 'nan':
                        continue
                    
                    country_code = self._clean_string(row.get('country', '')).upper()
                    
                    org_data = {
                        "org_id": org_id,
                        "project_id": project_id,
                        "name": self._clean_string(row.get('name', '')),
                        "shortName": self._clean_string(row.get('shortName', '')),
                        "country": country_code,
                        "city": self._clean_string(row.get('city', '')),
                        "activityType": self._clean_string(row.get('activityType', '')),
                        "ecContribution": self._parse_float(row.get('ecContribution')),
                        "role": self._clean_string(row.get('role', 'participant')),
                        "sme": str(row.get('SME', '')).lower() == 'true',
                    }
                    
                    # Create/update organization and link to project
                    self.db.execute_query("""
                        MERGE (o:Organization {id: $org_id})
                        SET o.name = $name,
                            o.shortName = $shortName,
                            o.country = $country,
                            o.city = $city,
                            o.activityType = $activityType,
                            o.sme = $sme
                        WITH o
                        MATCH (p:Project {id: $project_id})
                        MERGE (o)-[r:PARTICIPATES_IN]->(p)
                        SET r.role = $role, r.ecContribution = $ecContribution
                    """, org_data)
                    
                    self.stats.organizations_created += 1
                    self.stats.relationships_created += 1
                    
                    # Link to country
                    if country_code and len(country_code) == 2:
                        is_eu = country_code in self.EU_MEMBER_STATES
                        is_assoc = country_code in self.ASSOCIATED_COUNTRIES
                        self.db.execute_query("""
                            MATCH (o:Organization {id: $org_id})
                            MERGE (co:Country {isoCode: $country})
                            ON CREATE SET co.isEU = $isEU, co.isAssociated = $isAssoc
                            MERGE (o)-[:LOCATED_IN]->(co)
                        """, {"org_id": org_id, "country": country_code, "isEU": is_eu, "isAssoc": is_assoc})
                    
                    # Link to entity type
                    activity_type = org_data["activityType"]
                    if activity_type and activity_type in self.ENTITY_TYPES:
                        self.db.execute_query("""
                            MATCH (o:Organization {id: $org_id})
                            MERGE (et:EntityType {code: $type})
                            MERGE (o)-[:IS_TYPE]->(et)
                        """, {"org_id": org_id, "type": activity_type})
                        
                except Exception as e:
                    logger.error(f"Error processing organization: {e}")
                    self.stats.errors += 1
        
        logger.info(f"✅ Loaded {self.stats.organizations_created} organization participations")
    
    def create_partnership_relationships(self) -> None:
        """Create PARTNERS_WITH relationships based on co-participation in projects."""
        
        logger.info("🔗 Creating partnership relationships (this may take a few minutes)...")
        
        # This query finds organizations that participated in the same projects
        # and creates a PARTNERS_WITH relationship with a count of shared projects
        query = """
        MATCH (o1:Organization)-[:PARTICIPATES_IN]->(p:Project)<-[:PARTICIPATES_IN]-(o2:Organization)
        WHERE o1.id < o2.id
        WITH o1, o2, COUNT(DISTINCT p) as projectCount, SUM(p.ecMaxContribution) as totalValue
        WHERE projectCount >= 2
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
        return str(value).strip().strip('"')
    
    def _parse_float(self, value) -> float:
        """Parse a float value, handling various formats."""
        if pd.isna(value) or value is None:
            return 0.0
        try:
            # Handle string representations with commas (European format)
            if isinstance(value, str):
                value = value.replace(',', '.').replace(' ', '').strip('"')
            return float(value)
        except (ValueError, TypeError):
            return 0.0
    
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
        
        # Step 4: Load organizations
        self.load_organizations()
        
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
        logger.info(f"⏱️ Duration: {duration:.1f} seconds ({duration/60:.1f} minutes)")
        logger.info(f"📊 Projects created: {self.stats.projects_created}")
        logger.info(f"🏢 Organizations created: {self.stats.organizations_created}")
        logger.info(f"🏷️ Topics created: {self.stats.topics_created}")
        logger.info(f"🎯 Cluster links: {self.stats.clusters_linked}")
        logger.info(f"🔗 Relationships created: {self.stats.relationships_created}")
        logger.info(f"❌ Errors: {self.stats.errors}")
        
        # Get final database stats
        try:
            stats = self.db.get_database_stats()
            logger.info("\n📈 Final Database State:")
            for label, count in stats.get("nodes", {}).items():
                logger.info(f"   {label}: {count}")
            logger.info(f"\n   Total Nodes: {stats.get('total_nodes', 0)}")
            logger.info(f"   Total Relationships: {stats.get('total_relationships', 0)}")
        except Exception as e:
            logger.warning(f"Could not get final stats: {e}")


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


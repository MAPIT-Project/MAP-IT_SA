"""
Graph Search Service for Neo4j-based relationship traversal and structural queries.

Provides methods for:
- Call/Topic lookups (Query Type A)
- Eligibility checks (Query Type B)
- Budget statistics (Query Type C)
- Consortium patterns (Query Type D)
- Similar topic discovery (Query Type E)
- Organization relationship traversal

Usage:
    from app.services.data_intelligence.graph_service import GraphSearchService
    
    service = GraphSearchService()
    result = service.get_call_details("HORIZON-CL4-2025-DATA-01")
"""

import re
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict

from app.core.neo4j_config import neo4j_db

logger = logging.getLogger(__name__)


class GraphSearchService:
    """
    Neo4j-based graph search for Horizon Europe data.
    
    Provides relationship-aware queries that complement vector search
    for structured data retrieval.
    """
    
    # EU Member States for eligibility checks
    EU_MEMBER_STATES = {
        "AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR",
        "DE", "GR", "HU", "IE", "IT", "LV", "LT", "LU", "MT", "NL",
        "PL", "PT", "RO", "SK", "SI", "ES", "SE"
    }
    
    # Associated Countries (simplified list - should be updated)
    ASSOCIATED_COUNTRIES = {
        "NO", "IS", "IL", "UK", "CH", "TR", "UA", "MD", "ME", "RS",
        "AL", "MK", "BA", "GE", "AM", "TN", "MA", "FO", "EL"
    }
    
    def __init__(self):
        """Initialize the Graph Search Service."""
        self.db = neo4j_db
        
        # Verify connection
        try:
            if self.db.test_connection():
                logger.info("✅ Graph Search Service initialized")
            else:
                logger.warning("⚠️ Neo4j connection test failed")
        except Exception as e:
            logger.warning(f"⚠️ Neo4j connection not available: {e}")
    
    # ========================================================================
    # QUERY TYPE A: Call/Topic Lookup
    # ========================================================================
    
    def get_call_details(self, identifier: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific call or topic.
        
        Args:
            identifier: Topic code (e.g., "HORIZON-CL4-2025-DATA-01")
            
        Returns:
            Dictionary with topic details, related projects, and statistics
        """
        identifier = identifier.upper().strip()
        
        query = """
        // Find topic by exact match or partial match
        MATCH (t:Topic)
        WHERE t.code = $identifier 
           OR t.code CONTAINS $identifier
           OR $identifier CONTAINS t.code
        
        // Get related projects
        OPTIONAL MATCH (p:Project)-[:FUNDED_UNDER]->(t)
        
        // Get cluster or programme
        OPTIONAL MATCH (p)-[:TARGETS]->(c:Cluster)
        OPTIONAL MATCH (p)-[:TARGETS]->(pr:Programme)
        
        // Aggregate statistics
        WITH t, 
             COLLECT(DISTINCT p) as projects,
             COLLECT(DISTINCT c)[0] as cluster,
             COLLECT(DISTINCT pr)[0] as programme
        
        RETURN t.code as topicCode,
               t.title as topicTitle,
               COALESCE(cluster.code, programme.code) as clusterCode,
               COALESCE(cluster.name, programme.name) as clusterName,
               SIZE(projects) as projectCount,
               REDUCE(s = 0.0, p IN projects | s + COALESCE(p.ecMaxContribution, 0)) as totalFunding,
               [p IN projects[0..5] | {
                   id: p.id,
                   acronym: p.acronym,
                   title: p.title,
                   budget: p.ecMaxContribution,
                   status: p.status
               }] as sampleProjects
        LIMIT 1
        """
        
        try:
            results = self.db.execute_query(query, {"identifier": identifier})
            
            if not results:
                logger.info(f"No results found for topic: {identifier}")
                return None
            
            result = results[0]
            project_count = result.get("projectCount", 0)
            total_funding = result.get("totalFunding", 0)
            
            return {
                "topic_code": result.get("topicCode"),
                "topic_title": result.get("topicTitle"),
                "cluster_code": result.get("clusterCode"),
                "cluster_name": result.get("clusterName"),
                "project_count": project_count,
                "total_funding": total_funding,
                "avg_project_budget": total_funding / project_count if project_count > 0 else 0,
                "sample_projects": result.get("sampleProjects", []),
                "source": "neo4j_graph"
            }
            
        except Exception as e:
            logger.error(f"Error getting call details for {identifier}: {e}")
            return None
    
    def search_topics(self, search_term: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Search for topics by keyword.
        
        Args:
            search_term: Search term to match against topic codes and titles
            limit: Maximum number of results
            
        Returns:
            List of matching topics with basic info
        """
        query = """
        MATCH (t:Topic)
        WHERE toLower(t.code) CONTAINS toLower($search_term)
        
        OPTIONAL MATCH (p:Project)-[:FUNDED_UNDER]->(t)
        OPTIONAL MATCH (p)-[:TARGETS]->(c:Cluster)
        
        WITH t, COUNT(DISTINCT p) as projectCount, COLLECT(DISTINCT c.code)[0] as cluster
        
        RETURN t.code as code,
               t.title as title,
               cluster as clusterCode,
               projectCount
        ORDER BY projectCount DESC
        LIMIT $limit
        """
        
        try:
            return self.db.execute_query(query, {"search_term": search_term, "limit": limit})
        except Exception as e:
            logger.error(f"Error searching topics: {e}")
            return []

    def get_topics_by_cluster(self, cluster_code: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get topics that belong to a specific cluster.

        Uses the BELONGS_TO relationship between Topics and Clusters
        which was inferred from Project->Topic and Project->Cluster relationships.

        Args:
            cluster_code: Cluster code (e.g., "CLUSTER-1", "CLUSTER-4")
            limit: Maximum number of topics to return

        Returns:
            List of topics with their project counts
        """
        query = """
        MATCH (t:Topic)-[r:BELONGS_TO]->(c:Cluster {code: $cluster_code})
        RETURN t.code as code,
               t.title as title,
               r.project_count as projectCount
        ORDER BY r.project_count DESC
        LIMIT $limit
        """

        try:
            results = self.db.execute_query(query, {"cluster_code": cluster_code, "limit": limit})
            return [
                {
                    "code": r.get("code"),
                    "title": r.get("title"),
                    "projectCount": r.get("projectCount", 0)
                }
                for r in results
            ]
        except Exception as e:
            logger.error(f"Error getting topics by cluster: {e}")
            return []

    # ========================================================================
    # QUERY TYPE B: Eligibility Checks
    # ========================================================================
    
    def check_country_eligibility(
        self, 
        country_code: str, 
        cluster_code: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Check if a country is eligible to participate in Horizon Europe.
        
        Args:
            country_code: ISO country code (e.g., "CH", "DE")
            cluster_code: Optional cluster to check specific participation
            
        Returns:
            Eligibility status and participation history
        """
        country_code = country_code.upper().strip()
        
        # Determine eligibility status
        if country_code in self.EU_MEMBER_STATES:
            eligibility_status = "EU Member State - Fully Eligible"
            is_eligible = True
        elif country_code in self.ASSOCIATED_COUNTRIES:
            # Provide more specific status for key associated countries
            if country_code == "CH":
                eligibility_status = "Associated Country - Fully Eligible (Association Agreement effective since 2024)"
            elif country_code == "UK":
                eligibility_status = "Associated Country - Fully Eligible (Association Agreement effective since January 2024)"
            elif country_code == "NO" or country_code == "IS":
                eligibility_status = "Associated Country - Fully Eligible (EEA/EFTA member)"
            elif country_code == "IL":
                eligibility_status = "Associated Country - Fully Eligible"
            else:
                eligibility_status = "Associated Country - Eligible (verify specific call conditions)"
            is_eligible = True
        else:
            eligibility_status = "Third Country - Limited eligibility, check call text"
            is_eligible = False
        
        # Get participation history from graph
        query = """
        MATCH (co:Country {isoCode: $country_code})
        OPTIONAL MATCH (o:Organization)-[:LOCATED_IN]->(co)
        OPTIONAL MATCH (o)-[r:PARTICIPATES_IN]->(p:Project)
        OPTIONAL MATCH (p)-[:TARGETS]->(c:Cluster)
        
        WITH co, 
             COUNT(DISTINCT o) as orgCount,
             COUNT(DISTINCT p) as projectCount,
             SUM(r.ecContribution) as totalFunding,
             COLLECT(DISTINCT c.code) as clusters
        
        RETURN co.isoCode as countryCode,
               co.isEU as isEU,
               orgCount,
               projectCount,
               totalFunding,
               clusters
        """
        
        try:
            results = self.db.execute_query(query, {"country_code": country_code})
            
            participation = {}
            if results:
                result = results[0]
                participation = {
                    "organization_count": result.get("orgCount", 0),
                    "project_count": result.get("projectCount", 0),
                    "total_funding_received": result.get("totalFunding", 0) or 0,
                    "active_clusters": [c for c in result.get("clusters", []) if c]
                }
            
            # Generate notes based on status
            notes = []
            if country_code == "CH":
                notes.append("Switzerland is fully associated to Horizon Europe since 2024. Swiss entities participate on equal terms with EU Member States.")
            elif country_code == "UK":
                notes.append("UK is fully associated to Horizon Europe since January 2024. UK entities participate on equal terms with EU Member States.")
            elif country_code == "NO" or country_code == "IS":
                notes.append("As an EEA/EFTA member, entities participate on equal terms with EU Member States.")
            elif not is_eligible:
                notes.append("Third countries may participate under specific conditions - check call text for eligibility.")
            
            return {
                "country_code": country_code,
                "entity_type": "country",
                "is_eligible": is_eligible,
                "eligibility_status": eligibility_status,
                "participation_history": participation,
                "notes": notes,
                "source": "neo4j_graph"
            }
            
        except Exception as e:
            logger.error(f"Error checking country eligibility: {e}")
            return {
                "country_code": country_code,
                "entity_type": "country",
                "is_eligible": is_eligible,
                "eligibility_status": eligibility_status,
                "participation_history": {},
                "notes": ["Error retrieving participation history"],
                "source": "fallback"
            }
    
    def check_entity_type_eligibility(
        self, 
        entity_type: str,
        action_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Check eligibility and participation patterns for an entity type.
        
        Args:
            entity_type: Entity type code (e.g., "HES", "PRC", "REC") or name
            action_type: Optional action type filter (e.g., "RIA", "IA", "CSA")
            
        Returns:
            Eligibility info and participation statistics
        """
        # Normalize entity type
        entity_type_upper = entity_type.upper().strip()
        
        # Entity type mapping
        entity_type_info = {
            "HES": {"name": "Higher or Secondary Education", "eligible": True},
            "REC": {"name": "Research Organisations", "eligible": True},
            "PRC": {"name": "Private for-profit entities", "eligible": True},
            "PUB": {"name": "Public bodies", "eligible": True},
            "OTH": {"name": "Other entities", "eligible": True},
            "SME": {"name": "Small and Medium Enterprises", "eligible": True},
        }
        
        # Handle common aliases
        if "SME" in entity_type_upper or "SMALL" in entity_type_upper:
            entity_type_upper = "PRC"  # SMEs are typically PRC
        elif "UNIVERSITY" in entity_type_upper or "EDUCATION" in entity_type_upper:
            entity_type_upper = "HES"
        elif "RESEARCH" in entity_type_upper:
            entity_type_upper = "REC"
        
        info = entity_type_info.get(entity_type_upper, {"name": entity_type, "eligible": True})
        
        # Get participation statistics
        query = """
        MATCH (et:EntityType)
        WHERE et.code = $entity_type OR toLower(et.name) CONTAINS toLower($entity_type)
        
        OPTIONAL MATCH (o:Organization)-[:IS_TYPE]->(et)
        OPTIONAL MATCH (o)-[r:PARTICIPATES_IN]->(p:Project)
        OPTIONAL MATCH (p)-[:TARGETS]->(c:Cluster)
        
        WITH et,
             COUNT(DISTINCT o) as orgCount,
             COUNT(DISTINCT p) as projectCount,
             SUM(r.ecContribution) as totalFunding,
             COLLECT(DISTINCT c.code) as clusters,
             COUNT(CASE WHEN r.role = 'coordinator' THEN 1 END) as coordinations
        
        RETURN et.code as code,
               et.name as name,
               orgCount,
               projectCount,
               totalFunding,
               clusters,
               coordinations
        """
        
        try:
            results = self.db.execute_query(query, {"entity_type": entity_type_upper})
            
            participation = {}
            if results and results[0].get("code"):
                result = results[0]
                participation = {
                    "entity_type_code": result.get("code"),
                    "entity_type_name": result.get("name"),
                    "organization_count": result.get("orgCount", 0),
                    "project_count": result.get("projectCount", 0),
                    "total_funding": result.get("totalFunding", 0) or 0,
                    "active_clusters": [c for c in result.get("clusters", []) if c],
                    "coordinations": result.get("coordinations", 0)
                }
            
            return {
                "entity_type": entity_type_upper,
                "entity_type_name": info["name"],
                "is_eligible": info["eligible"],
                "eligibility_status": "Eligible to participate in Horizon Europe",
                "participation_history": participation,
                "notes": [],
                "source": "neo4j_graph"
            }
            
        except Exception as e:
            logger.error(f"Error checking entity type eligibility: {e}")
            return {
                "entity_type": entity_type_upper,
                "entity_type_name": info["name"],
                "is_eligible": info["eligible"],
                "eligibility_status": "Eligible to participate in Horizon Europe",
                "participation_history": {},
                "notes": ["Error retrieving participation history"],
                "source": "fallback"
            }
    
    # ========================================================================
    # QUERY TYPE C: Budget Statistics
    # ========================================================================
    
    def get_budget_statistics(
        self, 
        cluster_code: Optional[str] = None,
        action_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get budget statistics for projects, optionally filtered by cluster.
        
        Args:
            cluster_code: Optional cluster filter (e.g., "CLUSTER-4")
            action_type: Optional action type filter (e.g., "RIA", "IA")
            
        Returns:
            List of budget statistics per cluster
        """
        # Build dynamic WHERE clause
        where_clauses = []
        params = {}
        
        if cluster_code:
            where_clauses.append("c.code = $cluster_code")
            params["cluster_code"] = cluster_code.upper()
        
        if action_type:
            where_clauses.append("p.fundingScheme CONTAINS $action_type")
            params["action_type"] = action_type.upper()
        
        where_clause = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""
        
        query = f"""
        MATCH (p:Project)-[:TARGETS]->(c:Cluster)
        {where_clause}
        
        WITH c,
             COUNT(p) as projectCount,
             SUM(p.ecMaxContribution) as totalFunding,
             AVG(p.ecMaxContribution) as avgBudget,
             MIN(p.ecMaxContribution) as minBudget,
             MAX(p.ecMaxContribution) as maxBudget,
             percentileCont(p.ecMaxContribution, 0.5) as medianBudget
        
        RETURN c.code as clusterCode,
               c.name as clusterName,
               projectCount,
               totalFunding,
               avgBudget,
               minBudget,
               maxBudget,
               medianBudget
        ORDER BY c.code
        """
        
        try:
            results = self.db.execute_query(query, params)
            
            # Format results
            formatted = []
            for r in results:
                formatted.append({
                    "cluster_code": r.get("clusterCode"),
                    "cluster_name": r.get("clusterName"),
                    "project_count": r.get("projectCount", 0),
                    "total_funding": r.get("totalFunding", 0) or 0,
                    "avg_budget": r.get("avgBudget", 0) or 0,
                    "min_budget": r.get("minBudget", 0) or 0,
                    "max_budget": r.get("maxBudget", 0) or 0,
                    "median_budget": r.get("medianBudget", 0) or 0,
                    "source": "neo4j_graph"
                })
            
            return formatted
            
        except Exception as e:
            logger.error(f"Error getting budget statistics: {e}")
            return []
    
    # ========================================================================
    # QUERY TYPE D: Consortium Patterns
    # ========================================================================
    
    def get_consortium_patterns(
        self, 
        cluster_code: Optional[str] = None,
        min_partners: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Analyze consortium composition patterns for successful projects.
        
        Args:
            cluster_code: Optional cluster filter
            min_partners: Minimum number of partners to consider
            
        Returns:
            Consortium pattern statistics per cluster
        """
        where_clause = ""
        params = {"min_partners": min_partners}
        
        if cluster_code:
            where_clause = "WHERE c.code = $cluster_code"
            params["cluster_code"] = cluster_code.upper()
        
        query = f"""
        MATCH (p:Project)-[:TARGETS]->(c:Cluster)
        {where_clause}
        
        MATCH (o:Organization)-[r:PARTICIPATES_IN]->(p)
        OPTIONAL MATCH (o)-[:LOCATED_IN]->(co:Country)
        OPTIONAL MATCH (o)-[:IS_TYPE]->(et:EntityType)
        
        WITH p, c,
             COUNT(DISTINCT o) as partnerCount,
             COUNT(DISTINCT co.isoCode) as countryCount,
             COLLECT(DISTINCT et.code) as entityTypes,
             COLLECT(DISTINCT CASE WHEN r.role = 'coordinator' THEN co.isoCode END) as coordCountries
        
        WHERE partnerCount >= $min_partners
        
        WITH c,
             AVG(partnerCount) as avgPartners,
             AVG(countryCount) as avgCountries,
             COLLECT(coordCountries[0]) as allCoordCountries,
             COUNT(p) as sampleSize
        
        RETURN c.code as clusterCode,
               c.name as clusterName,
               avgPartners,
               avgCountries,
               sampleSize,
               allCoordCountries
        ORDER BY c.code
        """
        
        try:
            results = self.db.execute_query(query, params)
            
            formatted = []
            for r in results:
                # Get top coordinator countries
                coord_countries = r.get("allCoordCountries", [])
                coord_country_counts = {}
                for cc in coord_countries:
                    if cc:
                        coord_country_counts[cc] = coord_country_counts.get(cc, 0) + 1
                top_coord_countries = sorted(
                    coord_country_counts.items(), 
                    key=lambda x: x[1], 
                    reverse=True
                )[:5]
                
                formatted.append({
                    "cluster_code": r.get("clusterCode"),
                    "cluster_name": r.get("clusterName"),
                    "avg_partners": round(r.get("avgPartners", 0) or 0, 1),
                    "avg_countries": round(r.get("avgCountries", 0) or 0, 1),
                    "sample_size": r.get("sampleSize", 0),
                    "top_coordinator_countries": [c[0] for c in top_coord_countries],
                    "source": "neo4j_graph"
                })
            
            return formatted
            
        except Exception as e:
            logger.error(f"Error getting consortium patterns: {e}")
            return []
    
    # ========================================================================
    # QUERY TYPE E: Similar Topics/Calls
    # ========================================================================
    
    def find_similar_topics(
        self, 
        topic_code: str, 
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Find topics similar to a given topic based on cluster and participation overlap.
        
        Args:
            topic_code: Reference topic code
            limit: Maximum results
            
        Returns:
            List of similar topics with similarity scores
        """
        query = """
        // Find the reference topic and its cluster
        MATCH (t1:Topic {code: $topic_code})
        OPTIONAL MATCH (p1:Project)-[:FUNDED_UNDER]->(t1)
        OPTIONAL MATCH (p1)-[:TARGETS]->(c:Cluster)
        
        WITH t1, COLLECT(DISTINCT c) as refClusters
        
        // Find other topics in the same clusters
        MATCH (p2:Project)-[:TARGETS]->(c2:Cluster)
        WHERE c2 IN refClusters
        MATCH (p2)-[:FUNDED_UNDER]->(t2:Topic)
        WHERE t2.code <> t1.code
        
        // Calculate similarity based on shared clusters and project count
        WITH t1, t2, c2,
             COUNT(DISTINCT p2) as projectCount
        
        WITH t2, 
             COLLECT(DISTINCT c2.name) as clusterNames,
             SUM(projectCount) as totalProjects,
             COUNT(DISTINCT c2) as sharedClusters
        
        // Similarity score based on shared structure
        WITH t2, clusterNames, totalProjects, sharedClusters,
             (sharedClusters * 0.5 + CASE WHEN totalProjects > 5 THEN 0.5 ELSE totalProjects * 0.1 END) as similarity
        
        RETURN t2.code as topicCode,
               t2.title as topicTitle,
               totalProjects as projectCount,
               sharedClusters,
               clusterNames,
               similarity
        ORDER BY similarity DESC, totalProjects DESC
        LIMIT $limit
        """
        
        try:
            results = self.db.execute_query(
                query, 
                {"topic_code": topic_code.upper(), "limit": limit}
            )
            
            formatted = []
            for r in results:
                formatted.append({
                    "topic_code": r.get("topicCode"),
                    "topic_title": r.get("topicTitle"),
                    "project_count": r.get("projectCount", 0),
                    "shared_clusters": r.get("clusterNames", []),
                    "similarity_score": r.get("similarity", 0),
                    "source": "neo4j_graph"
                })
            
            return formatted
            
        except Exception as e:
            logger.error(f"Error finding similar topics: {e}")
            return []
    
    # ========================================================================
    # Organization Queries
    # ========================================================================
    
    def find_organization_partners(
        self, 
        org_name: str, 
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Find organizations that have collaborated with a given organization.
        
        Args:
            org_name: Organization name (partial match supported)
            limit: Maximum results
            
        Returns:
            List of partner organizations with collaboration stats
        """
        query = """
        // Find the organization
        MATCH (o1:Organization)
        WHERE toLower(o1.name) CONTAINS toLower($org_name)
           OR toLower(o1.shortName) CONTAINS toLower($org_name)
        
        // Find partners through shared projects
        MATCH (o1)-[:PARTICIPATES_IN]->(p:Project)<-[:PARTICIPATES_IN]-(o2:Organization)
        WHERE o1 <> o2
        
        // Aggregate partnership statistics
        WITH o1, o2,
             COUNT(DISTINCT p) as sharedProjects,
             SUM(p.ecMaxContribution) as totalProjectValue,
             COLLECT(DISTINCT p.acronym)[0..3] as sampleProjects
        
        OPTIONAL MATCH (o2)-[:LOCATED_IN]->(co:Country)
        
        RETURN o2.name as partnerName,
               o2.shortName as partnerShortName,
               co.isoCode as partnerCountry,
               sharedProjects,
               totalProjectValue,
               sampleProjects
        ORDER BY sharedProjects DESC
        LIMIT $limit
        """
        
        try:
            results = self.db.execute_query(query, {"org_name": org_name, "limit": limit})
            return [
                {
                    "partner_name": r.get("partnerName"),
                    "partner_short_name": r.get("partnerShortName"),
                    "partner_country": r.get("partnerCountry"),
                    "shared_projects": r.get("sharedProjects", 0),
                    "total_project_value": r.get("totalProjectValue", 0) or 0,
                    "sample_projects": r.get("sampleProjects", []),
                    "source": "neo4j_graph"
                }
                for r in results
            ]
        except Exception as e:
            logger.error(f"Error finding organization partners: {e}")
            return []
    
    def get_organization_profile(self, org_name: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed profile of an organization including participation history.
        
        Args:
            org_name: Organization name
            
        Returns:
            Organization profile with statistics
        """
        query = """
        MATCH (o:Organization)
        WHERE toLower(o.name) CONTAINS toLower($org_name)
           OR toLower(o.shortName) CONTAINS toLower($org_name)
        
        OPTIONAL MATCH (o)-[:LOCATED_IN]->(co:Country)
        OPTIONAL MATCH (o)-[:IS_TYPE]->(et:EntityType)
        OPTIONAL MATCH (o)-[r:PARTICIPATES_IN]->(p:Project)
        OPTIONAL MATCH (p)-[:TARGETS]->(c:Cluster)
        
        WITH o, co, et,
             COUNT(DISTINCT p) as projectCount,
             SUM(r.ecContribution) as totalFunding,
             COUNT(CASE WHEN r.role = 'coordinator' THEN 1 END) as coordinations,
             COLLECT(DISTINCT c.code) as clusters,
             COLLECT(DISTINCT p.acronym)[0..5] as recentProjects
        
        RETURN o.id as id,
               o.name as name,
               o.shortName as shortName,
               co.isoCode as country,
               et.code as entityType,
               et.name as entityTypeName,
               projectCount,
               totalFunding,
               coordinations,
               clusters,
               recentProjects
        ORDER BY projectCount DESC
        LIMIT 1
        """
        
        try:
            results = self.db.execute_query(query, {"org_name": org_name})
            if not results:
                return None
            
            r = results[0]
            return {
                "id": r.get("id"),
                "name": r.get("name"),
                "short_name": r.get("shortName"),
                "country": r.get("country"),
                "entity_type": r.get("entityType"),
                "entity_type_name": r.get("entityTypeName"),
                "project_count": r.get("projectCount", 0),
                "total_funding": r.get("totalFunding", 0) or 0,
                "coordinations": r.get("coordinations", 0),
                "active_clusters": [c for c in r.get("clusters", []) if c],
                "recent_projects": r.get("recentProjects", []),
                "source": "neo4j_graph"
            }
        except Exception as e:
            logger.error(f"Error getting organization profile: {e}")
            return None
    
    # ========================================================================
    # Utility Methods
    # ========================================================================
    
    def get_cluster_overview(self) -> List[Dict[str, Any]]:
        """Get overview of all clusters with project counts."""
        query = """
        MATCH (c:Cluster)
        OPTIONAL MATCH (p:Project)-[:TARGETS]->(c)
        
        WITH c, COUNT(p) as projectCount, SUM(p.ecMaxContribution) as totalFunding
        
        RETURN c.code as code,
               c.name as name,
               c.pillar as pillar,
               projectCount,
               totalFunding
        ORDER BY c.code
        """
        
        try:
            results = self.db.execute_query(query)
            return [
                {
                    "code": r.get("code"),
                    "name": r.get("name"),
                    "pillar": r.get("pillar"),
                    "project_count": r.get("projectCount", 0),
                    "total_funding": r.get("totalFunding", 0) or 0,
                    "source": "neo4j_graph"
                }
                for r in results
            ]
        except Exception as e:
            logger.error(f"Error getting cluster overview: {e}")
            return []
    
    def get_top_organizations(
        self,
        cluster_code: Optional[str] = None,
        country_code: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Get top organizations by project participation.

        Args:
            cluster_code: Optional filter by cluster
            country_code: Optional filter by country
            limit: Maximum results

        Returns:
            List of organizations with participation stats
        """
        params = {"limit": limit}

        # Build query based on filters
        # Use MATCH (not OPTIONAL MATCH) for country when filtering by country
        if country_code:
            params["country_code"] = country_code.upper()

            if cluster_code:
                params["cluster_code"] = cluster_code.upper()
                query = """
                MATCH (o:Organization)-[:LOCATED_IN]->(co:Country {isoCode: $country_code})
                MATCH (o)-[r:PARTICIPATES_IN]->(p:Project)-[:TARGETS]->(c:Cluster {code: $cluster_code})

                WITH o, co,
                     COUNT(DISTINCT p) as projectCount,
                     SUM(r.ecContribution) as totalFunding,
                     COUNT(CASE WHEN r.role = 'coordinator' THEN 1 END) as coordinations

                RETURN o.name as name,
                       o.shortName as shortName,
                       co.isoCode as country,
                       projectCount,
                       totalFunding,
                       coordinations
                ORDER BY projectCount DESC
                LIMIT $limit
                """
            else:
                query = """
                MATCH (o:Organization)-[:LOCATED_IN]->(co:Country {isoCode: $country_code})
                MATCH (o)-[r:PARTICIPATES_IN]->(p:Project)

                WITH o, co,
                     COUNT(DISTINCT p) as projectCount,
                     SUM(r.ecContribution) as totalFunding,
                     COUNT(CASE WHEN r.role = 'coordinator' THEN 1 END) as coordinations

                RETURN o.name as name,
                       o.shortName as shortName,
                       co.isoCode as country,
                       projectCount,
                       totalFunding,
                       coordinations
                ORDER BY projectCount DESC
                LIMIT $limit
                """
        elif cluster_code:
            params["cluster_code"] = cluster_code.upper()
            query = """
            MATCH (o:Organization)-[r:PARTICIPATES_IN]->(p:Project)-[:TARGETS]->(c:Cluster {code: $cluster_code})
            OPTIONAL MATCH (o)-[:LOCATED_IN]->(co:Country)

            WITH o, co,
                 COUNT(DISTINCT p) as projectCount,
                 SUM(r.ecContribution) as totalFunding,
                 COUNT(CASE WHEN r.role = 'coordinator' THEN 1 END) as coordinations

            RETURN o.name as name,
                   o.shortName as shortName,
                   co.isoCode as country,
                   projectCount,
                   totalFunding,
                   coordinations
            ORDER BY projectCount DESC
            LIMIT $limit
            """
        else:
            # No filters - get overall top organizations
            query = """
            MATCH (o:Organization)-[r:PARTICIPATES_IN]->(p:Project)
            OPTIONAL MATCH (o)-[:LOCATED_IN]->(co:Country)

            WITH o, co,
                 COUNT(DISTINCT p) as projectCount,
                 SUM(r.ecContribution) as totalFunding,
                 COUNT(CASE WHEN r.role = 'coordinator' THEN 1 END) as coordinations

            RETURN o.name as name,
                   o.shortName as shortName,
                   co.isoCode as country,
                   projectCount,
                   totalFunding,
                   coordinations
            ORDER BY projectCount DESC
            LIMIT $limit
            """
        
        try:
            results = self.db.execute_query(query, params)
            return [
                {
                    "name": r.get("name"),
                    "short_name": r.get("shortName"),
                    "country": r.get("country"),
                    "project_count": r.get("projectCount", 0),
                    "total_funding": r.get("totalFunding", 0) or 0,
                    "coordinations": r.get("coordinations", 0),
                    "source": "neo4j_graph"
                }
                for r in results
            ]
        except Exception as e:
            logger.error(f"Error getting top organizations: {e}")
            return []
    
    # ========================================================================
    # QUERY TYPE F: Project Examples with Success Metrics
    # ========================================================================
    
    def get_project_examples(
        self,
        cluster_code: Optional[str] = None,
        topic_pattern: Optional[str] = None,
        funding_scheme: Optional[str] = None,
        min_budget: float = 0,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get example projects with their details and success indicators.
        
        Args:
            cluster_code: Filter by cluster (e.g., "CLUSTER-4")
            topic_pattern: Topic code pattern to match
            funding_scheme: Filter by RIA, IA, CSA, etc.
            min_budget: Minimum budget threshold
            limit: Maximum results
            
        Returns:
            List of projects with consortium details
        """
        where_clauses = ["p.ecMaxContribution >= $min_budget"]
        params = {"limit": limit, "min_budget": min_budget}
        
        if cluster_code:
            where_clauses.append("c.code = $cluster_code")
            params["cluster_code"] = cluster_code.upper()
        
        if topic_pattern:
            where_clauses.append("t.code CONTAINS $topic_pattern")
            params["topic_pattern"] = topic_pattern.upper()
        
        if funding_scheme:
            where_clauses.append("p.fundingScheme CONTAINS $funding_scheme")
            params["funding_scheme"] = funding_scheme.upper()
        
        where_clause = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""
        
        query = f"""
        MATCH (p:Project)-[:FUNDED_UNDER]->(t:Topic)
        OPTIONAL MATCH (p)-[:TARGETS]->(c:Cluster)
        {where_clause}
        
        // Get consortium info
        OPTIONAL MATCH (o:Organization)-[r:PARTICIPATES_IN]->(p)
        OPTIONAL MATCH (o)-[:LOCATED_IN]->(co:Country)
        
        WITH p, t, c,
             COUNT(DISTINCT o) as partnerCount,
             COUNT(DISTINCT co) as countryCount,
             COLLECT(DISTINCT {{
                 name: o.name,
                 country: co.isoCode,
                 role: r.role
             }})[0..5] as partners
        
        RETURN p.id as projectId,
               p.acronym as acronym,
               p.title as title,
               left(p.objective, 500) as objective,
               p.status as status,
               p.startDate as startDate,
               p.endDate as endDate,
               p.ecMaxContribution as budget,
               p.fundingScheme as fundingScheme,
               t.code as topicCode,
               c.code as clusterCode,
               c.name as clusterName,
               partnerCount,
               countryCount,
               partners
        ORDER BY p.ecMaxContribution DESC
        LIMIT $limit
        """
        
        try:
            results = self.db.execute_query(query, params)
            return [
                {
                    "project_id": r.get("projectId"),
                    "acronym": r.get("acronym"),
                    "title": r.get("title"),
                    "objective": r.get("objective"),
                    "status": r.get("status"),
                    "start_date": r.get("startDate"),
                    "end_date": r.get("endDate"),
                    "budget": r.get("budget", 0) or 0,
                    "funding_scheme": r.get("fundingScheme"),
                    "topic_code": r.get("topicCode"),
                    "cluster_code": r.get("clusterCode"),
                    "cluster_name": r.get("clusterName"),
                    "partner_count": r.get("partnerCount", 0),
                    "country_count": r.get("countryCount", 0),
                    "partners": r.get("partners", []),
                    "source": "neo4j_graph"
                }
                for r in results
            ]
        except Exception as e:
            logger.error(f"Error getting project examples: {e}")
            return []
    
    # ========================================================================
    # QUERY TYPE G: Organization Track Record
    # ========================================================================
    
    def get_organization_track_record(
        self,
        org_name: str,
        include_partners: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Get comprehensive track record for an organization.
        
        Args:
            org_name: Organization name (partial match)
            include_partners: Include top collaboration partners
            
        Returns:
            Organization profile with project history and statistics
        """
        query = """
        MATCH (o:Organization)
        WHERE toLower(o.name) CONTAINS toLower($org_name)
           OR toLower(o.shortName) CONTAINS toLower($org_name)
        
        OPTIONAL MATCH (o)-[:LOCATED_IN]->(co:Country)
        OPTIONAL MATCH (o)-[:IS_TYPE]->(et:EntityType)
        OPTIONAL MATCH (o)-[r:PARTICIPATES_IN]->(p:Project)
        OPTIONAL MATCH (p)-[:TARGETS]->(c:Cluster)
        OPTIONAL MATCH (p)-[:FUNDED_UNDER]->(t:Topic)
        
        WITH o, co, et,
             COLLECT(DISTINCT {
                 id: p.id,
                 acronym: p.acronym,
                 title: p.title,
                 budget: p.ecMaxContribution,
                 role: r.role,
                 status: p.status,
                 cluster: c.code,
                 topic: t.code
             }) as projects
        
        // Calculate statistics
        WITH o, co, et, projects,
             SIZE(projects) as totalProjects,
             SIZE([p IN projects WHERE p.role = 'coordinator']) as coordinations,
             REDUCE(s = 0.0, p IN projects | s + COALESCE(p.budget, 0)) as totalFunding
        
        RETURN o.id as orgId,
               o.name as name,
               o.shortName as shortName,
               co.isoCode as country,
               co.name as countryName,
               et.code as entityType,
               et.name as entityTypeName,
               totalProjects,
               coordinations,
               totalFunding,
               projects[0..10] as recentProjects
        LIMIT 1
        """
        
        try:
            results = self.db.execute_query(query, {"org_name": org_name})
            
            if not results:
                return None
            
            r = results[0]
            result = {
                "org_id": r.get("orgId"),
                "name": r.get("name"),
                "short_name": r.get("shortName"),
                "country": r.get("country"),
                "country_name": r.get("countryName"),
                "entity_type": r.get("entityType"),
                "entity_type_name": r.get("entityTypeName"),
                "total_projects": r.get("totalProjects", 0),
                "coordinations": r.get("coordinations", 0),
                "total_funding": r.get("totalFunding", 0) or 0,
                "recent_projects": r.get("recentProjects", []),
                "source": "neo4j_graph"
            }
            
            # Get top partners if requested
            if include_partners:
                partners = self.find_organization_partners(org_name, limit=5)
                result["top_partners"] = partners
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting organization track record: {e}")
            return None
    
    # ========================================================================
    # Compliance Checker: Consortium Validation
    # ========================================================================
    
    def check_consortium_compliance(
        self,
        partners: List[Dict[str, str]],
        action_type: str = "RIA",
        call_specific_rules: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Check if a proposed consortium meets eligibility requirements.
        
        Args:
            partners: List of partners with {country, entity_type, is_coordinator}
            action_type: RIA, IA, CSA, ERC, MSCA, etc.
            call_specific_rules: Override default rules
            
        Returns:
            Compliance check results with issues and recommendations
        """
        # Default rules by action type
        default_rules = {
            "RIA": {
                "min_partners": 3,
                "min_countries": 3,
                "countries_must_be_different": True,
                "requires_eu_coordinator": True
            },
            "IA": {
                "min_partners": 3,
                "min_countries": 3,
                "countries_must_be_different": True,
                "requires_eu_coordinator": True
            },
            "CSA": {
                "min_partners": 1,
                "min_countries": 1,
                "countries_must_be_different": False,
                "requires_eu_coordinator": True
            },
            "ERC": {
                "min_partners": 1,
                "min_countries": 1,
                "countries_must_be_different": False,
                "requires_eu_coordinator": True
            },
            "MSCA": {
                "min_partners": 1,
                "min_countries": 1,
                "countries_must_be_different": False,
                "requires_eu_coordinator": True
            }
        }
        
        rules = call_specific_rules or default_rules.get(action_type.upper(), default_rules["RIA"])
        
        issues = []
        warnings = []
        
        # Check partner count
        if len(partners) < rules.get("min_partners", 1):
            issues.append({
                "type": "partner_count",
                "severity": "error",
                "message": f"Minimum {rules['min_partners']} partners required, found {len(partners)}"
            })
        
        # Check country diversity
        countries = set(p.get("country", "").upper() for p in partners if p.get("country"))
        if len(countries) < rules.get("min_countries", 1):
            issues.append({
                "type": "country_count",
                "severity": "error",
                "message": f"Minimum {rules['min_countries']} different countries required, found {len(countries)}"
            })
        
        # Check if countries must be different
        if rules.get("countries_must_be_different") and len(partners) > 1:
            if len(countries) < min(len(partners), rules.get("min_countries", 3)):
                warnings.append({
                    "type": "country_diversity",
                    "severity": "warning",
                    "message": "Consider partners from more diverse countries for stronger proposal"
                })
        
        # Check EU coordinator requirement
        coordinator = next((p for p in partners if p.get("is_coordinator")), None)
        if coordinator:
            coord_country = coordinator.get("country", "").upper()
            if rules.get("requires_eu_coordinator"):
                if coord_country and coord_country not in self.EU_MEMBER_STATES and coord_country not in self.ASSOCIATED_COUNTRIES:
                    issues.append({
                        "type": "coordinator_eligibility",
                        "severity": "error",
                        "message": f"Coordinator country {coord_country} may not be eligible to coordinate"
                    })
        elif len(partners) > 0:
            warnings.append({
                "type": "no_coordinator",
                "severity": "warning",
                "message": "No coordinator specified - ensure one partner is designated as coordinator"
            })
        
        # Check entity diversity (recommendation)
        entity_types = set(p.get("entity_type", "").upper() for p in partners if p.get("entity_type"))
        if len(entity_types) == 1 and len(partners) >= 3:
            warnings.append({
                "type": "entity_diversity",
                "severity": "recommendation",
                "message": "Consider including diverse entity types (research, industry, SME) for stronger impact"
            })
        
        # Check for SME participation (often valued)
        has_sme = any("SME" in p.get("entity_type", "").upper() or "PRC" in p.get("entity_type", "").upper() 
                      for p in partners)
        if not has_sme and action_type.upper() in ["RIA", "IA"]:
            warnings.append({
                "type": "sme_participation",
                "severity": "recommendation",
                "message": "Consider including SME/private sector partners for innovation and exploitation"
            })
        
        is_compliant = len(issues) == 0
        
        return {
            "is_compliant": is_compliant,
            "action_type": action_type.upper(),
            "rules_applied": rules,
            "partner_count": len(partners),
            "country_count": len(countries),
            "countries": sorted(list(countries)),
            "entity_types": sorted(list(entity_types)),
            "issues": issues,
            "warnings": warnings,
            "recommendation": "Consortium meets basic eligibility criteria ✓" if is_compliant 
                            else f"Address {len(issues)} issue(s) before submission",
            "source": "compliance_checker"
        }
    
    # ========================================================================
    # Consortium Builder: Partner Suggestions
    # ========================================================================
    
    def suggest_consortium_partners(
        self,
        cluster_code: str,
        topic_code: Optional[str] = None,
        coordinator_country: Optional[str] = None,
        target_partner_count: int = 5,
        required_entity_types: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Suggest potential consortium partners for a project.
        
        Args:
            cluster_code: Target cluster (e.g., "CLUSTER-4")
            topic_code: Specific topic (optional)
            coordinator_country: Coordinator's country to exclude
            target_partner_count: Number of partners to suggest
            required_entity_types: Required entity types ["HES", "REC", "PRC"]
            
        Returns:
            Dictionary with suggested partners grouped by role/type
        """
        params = {
            "cluster_code": cluster_code.upper(),
            "limit": target_partner_count * 3  # Get more to filter
        }
        
        where_clauses = []
        
        if coordinator_country:
            where_clauses.append("co.isoCode <> $coord_country")
            params["coord_country"] = coordinator_country.upper()
        
        where_clause = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""
        
        # Find organizations active in this cluster with good track record
        query = f"""
        MATCH (o:Organization)-[r:PARTICIPATES_IN]->(p:Project)-[:TARGETS]->(c:Cluster {{code: $cluster_code}})
        OPTIONAL MATCH (o)-[:LOCATED_IN]->(co:Country)
        OPTIONAL MATCH (o)-[:IS_TYPE]->(et:EntityType)
        {where_clause}
        
        WITH o, co, et,
             COUNT(DISTINCT p) as projectCount,
             COUNT(CASE WHEN r.role = 'coordinator' THEN 1 END) as coordinations,
             SUM(r.ecContribution) as totalFunding
        
        WHERE projectCount >= 2
        
        RETURN o.id as orgId,
               o.name as name,
               o.shortName as shortName,
               co.isoCode as country,
               co.name as countryName,
               et.code as entityType,
               et.name as entityTypeName,
               projectCount,
               coordinations,
               totalFunding
        ORDER BY projectCount DESC, coordinations DESC
        LIMIT $limit
        """
        
        try:
            candidates = self.db.execute_query(query, params)
            
            # Group by entity type
            by_type: Dict[str, List[Dict]] = {"HES": [], "REC": [], "PRC": [], "PUB": [], "OTH": []}
            countries_seen: set = set()
            
            suggestions = []
            
            for candidate in candidates:
                entity_type = candidate.get("entityType") or "OTH"
                country = candidate.get("country")
                
                # Format candidate
                formatted = {
                    "org_id": candidate.get("orgId"),
                    "name": candidate.get("name"),
                    "short_name": candidate.get("shortName"),
                    "country": country,
                    "country_name": candidate.get("countryName"),
                    "entity_type": entity_type,
                    "entity_type_name": candidate.get("entityTypeName"),
                    "project_count": candidate.get("projectCount", 0),
                    "coordinations": candidate.get("coordinations", 0),
                    "total_funding": candidate.get("totalFunding", 0) or 0
                }
                
                # Prioritize geographic diversity
                if country not in countries_seen or len(by_type.get(entity_type, [])) < 2:
                    by_type.setdefault(entity_type, []).append(formatted)
                    if country:
                        countries_seen.add(country)
                    suggestions.append(formatted)
                    
                    if len(suggestions) >= target_partner_count:
                        break
            
            return {
                "cluster": cluster_code,
                "topic": topic_code,
                "suggestions": suggestions[:target_partner_count],
                "by_entity_type": {k: v[:2] for k, v in by_type.items() if v},
                "countries_covered": list(countries_seen)[:10],
                "total_candidates": len(candidates),
                "source": "neo4j_graph"
            }
            
        except Exception as e:
            logger.error(f"Error suggesting consortium partners: {e}")
            return {"suggestions": [], "error": str(e)}
    
    # ========================================================================
    # QUERY TYPE H: Trend Analysis
    # ========================================================================
    
    def get_funding_trends(
        self,
        cluster_code: Optional[str] = None,
        group_by: str = "year"
    ) -> List[Dict[str, Any]]:
        """
        Get funding trends over time.
        
        Args:
            cluster_code: Optional cluster filter
            group_by: Time grouping ("year" or "quarter")
            
        Returns:
            List of time periods with funding statistics
        """
        where_clauses = ["p.startDate IS NOT NULL"]
        params = {}
        
        if cluster_code:
            where_clauses.append("c.code = $cluster_code")
            params["cluster_code"] = cluster_code.upper()
        
        where_clause = "WHERE " + " AND ".join(where_clauses)
        
        if group_by == "quarter":
            date_extract = "substring(p.startDate, 0, 7)"  # YYYY-MM
        else:
            date_extract = "substring(p.startDate, 0, 4)"  # YYYY
        
        query = f"""
        MATCH (p:Project)
        OPTIONAL MATCH (p)-[:TARGETS]->(c:Cluster)
        {where_clause}
        
        WITH {date_extract} as period, p, c
        
        WITH period,
             COUNT(p) as projectCount,
             SUM(p.ecMaxContribution) as totalFunding,
             AVG(p.ecMaxContribution) as avgBudget,
             COLLECT(DISTINCT c.code) as clusters
        
        RETURN period,
               projectCount,
               totalFunding,
               avgBudget,
               clusters
        ORDER BY period
        """
        
        try:
            results = self.db.execute_query(query, params)
            return [
                {
                    "period": r.get("period"),
                    "project_count": r.get("projectCount", 0),
                    "total_funding": r.get("totalFunding", 0) or 0,
                    "avg_budget": r.get("avgBudget", 0) or 0,
                    "clusters": [c for c in r.get("clusters", []) if c],
                    "source": "neo4j_graph"
                }
                for r in results
            ]
        except Exception as e:
            logger.error(f"Error getting funding trends: {e}")
            return []


# ========================================================================
    # PROJECT DISCOVERY: Find Similar and Related Projects
    # ========================================================================
    
    def find_similar_projects(
        self,
        project_id: str,
        similarity_type: str = "topic",
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Find projects similar to a given project.
        
        Neo4j Schema:
        - Project: id, title, acronym, objective, status, startDate, endDate, 
                   totalCost, ecMaxContribution, fundingScheme, legalBasis
        - Relationships: FUNDED_UNDER->Topic, TARGETS->Cluster, PARTICIPATES_IN<-Organization
        
        Args:
            project_id: ID of the reference project
            similarity_type: Type of similarity:
                - "topic": Same topic/call
                - "consortium": Shared organizations
                - "cluster": Same cluster area
            limit: Maximum results
            
        Returns:
            List of similar projects with similarity info
        """
        params = {'project_id': project_id, 'limit': limit}
        
        if similarity_type == "topic":
            query = """
            MATCH (p1:Project {id: $project_id})-[:FUNDED_UNDER]->(t:Topic)<-[:FUNDED_UNDER]-(p2:Project)
            WHERE p1 <> p2
            WITH p2, t, p1
            RETURN p2.id as id, p2.title as title, p2.acronym as acronym,
                   t.code as shared_topic, p2.ecMaxContribution as budget,
                   p2.status as status, p2.fundingScheme as fundingScheme
            ORDER BY p2.startDate DESC
            LIMIT $limit
            """
        elif similarity_type == "consortium":
            query = """
            MATCH (p1:Project {id: $project_id})<-[:PARTICIPATES_IN]-(o:Organization)-[:PARTICIPATES_IN]->(p2:Project)
            WHERE p1 <> p2
            WITH p2, COUNT(DISTINCT o) as shared_orgs, COLLECT(DISTINCT o.name)[0..3] as shared_org_names
            RETURN p2.id as id, p2.title as title, p2.acronym as acronym,
                   shared_orgs, shared_org_names, p2.ecMaxContribution as budget,
                   p2.status as status, p2.fundingScheme as fundingScheme
            ORDER BY shared_orgs DESC
            LIMIT $limit
            """
        elif similarity_type == "cluster":
            query = """
            MATCH (p1:Project {id: $project_id})-[:TARGETS]->(c:Cluster)<-[:TARGETS]-(p2:Project)
            WHERE p1 <> p2
            WITH p2, c
            RETURN p2.id as id, p2.title as title, p2.acronym as acronym,
                   c.code as shared_cluster, c.name as cluster_name,
                   p2.ecMaxContribution as budget, p2.status as status,
                   p2.fundingScheme as fundingScheme
            ORDER BY p2.startDate DESC
            LIMIT $limit
            """
        else:
            logger.warning(f"Unknown similarity type: {similarity_type}, using 'topic'")
            return self.find_similar_projects(project_id, "topic", limit)
        
        try:
            results = self.db.execute_query(query, params)
            return [
                {
                    "id": r.get("id"),
                    "title": r.get("title"),
                    "acronym": r.get("acronym"),
                    "budget": r.get("budget", 0) or 0,
                    "status": r.get("status"),
                    "funding_scheme": r.get("fundingScheme"),
                    "similarity_type": similarity_type,
                    "shared_topic": r.get("shared_topic"),
                    "shared_cluster": r.get("shared_cluster"),
                    "cluster_name": r.get("cluster_name"),
                    "shared_orgs": r.get("shared_orgs"),
                    "shared_org_names": r.get("shared_org_names", []),
                    "cordis_url": f"https://cordis.europa.eu/project/id/{r.get('id')}"
                }
                for r in results
            ]
        except Exception as e:
            logger.error(f"Error finding similar projects: {e}")
            return []
    
    def find_projects_by_organization(
        self,
        organization_name: str,
        role: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Find all projects an organization participated in.
        
        Note: Neo4j only has PARTICIPATES_IN relationship - role detection uses 
        convention where coordinator org IDs end with '_coordinator'.
        
        Args:
            organization_name: Name (or partial name) of organization
            role: Filter by role ("coordinator", "participant", or None for both)
            limit: Maximum results
            
        Returns:
            List of projects with organization role info
        """
        params = {'org_name': organization_name.lower(), 'limit': limit}
        
        # Build the query - detect coordinator by naming convention or first participant
        query = """
        MATCH (o:Organization)-[:PARTICIPATES_IN]->(p:Project)
        WHERE toLower(o.name) CONTAINS $org_name
           OR toLower(o.shortName) CONTAINS $org_name
        
        // Try to determine role - coordinator if ID ends with _coordinator or first alphabetically
        WITH o, p, 
             CASE 
               WHEN o.id ENDS WITH '_coordinator' THEN 'coordinator'
               ELSE 'participant'
             END as detected_role
        
        RETURN p.id as id, p.title as title, p.acronym as acronym,
               p.ecMaxContribution as budget, p.status as status,
               o.name as organization, detected_role as role,
               o.country as org_country, p.fundingScheme as fundingScheme,
               p.startDate as start_date
        ORDER BY p.startDate DESC
        LIMIT $limit
        """
        
        try:
            results = self.db.execute_query(query, params)
            formatted_results = [
                {
                    "id": r.get("id"),
                    "title": r.get("title"),
                    "acronym": r.get("acronym"),
                    "budget": r.get("budget", 0) or 0,
                    "status": r.get("status"),
                    "funding_scheme": r.get("fundingScheme"),
                    "organization": r.get("organization"),
                    "org_country": r.get("org_country"),
                    "role": r.get("role"),
                    "start_date": r.get("start_date"),
                    "cordis_url": f"https://cordis.europa.eu/project/id/{r.get('id')}"
                }
                for r in results
            ]
            
            # Filter by role if specified
            if role:
                formatted_results = [r for r in formatted_results if r['role'] == role]
            
            return formatted_results
        except Exception as e:
            logger.error(f"Error finding projects by organization: {e}")
            return []
    
    def search_projects_by_keywords(
        self,
        keywords: List[str],
        status: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Search for projects by keywords in title and objective.
        
        Note: Neo4j Project nodes don't have 'topics' or 'frameworkProgramme' properties.
        
        Args:
            keywords: List of search keywords
            status: Optional status filter (SIGNED, CLOSED)
            limit: Maximum results
            
        Returns:
            List of matching projects
        """
        # Build search pattern - case-insensitive regex with word boundaries for short keywords
        pattern_parts = []
        for kw in keywords:
            kw_lower = kw.lower().strip()
            if len(kw_lower) <= 3:
                # Short keywords (like "AI") need word boundary matching to avoid false positives
                pattern_parts.append(f"\\\\b{kw_lower}\\\\b")
            else:
                # Longer keywords can use partial match
                pattern_parts.append(kw_lower)
        search_pattern = '|'.join(pattern_parts)

        where_clauses = [
            f"(toLower(p.title) =~ '.*({search_pattern}).*' OR toLower(p.objective) =~ '.*({search_pattern}).*')"
        ]
        params = {'limit': limit}
        
        if status:
            where_clauses.append("p.status = $status")
            params['status'] = status
        
        where_clause = " AND ".join(where_clauses)
        
        query = f"""
        MATCH (p:Project)
        WHERE {where_clause}
        OPTIONAL MATCH (p)-[:TARGETS]->(c:Cluster)
        OPTIONAL MATCH (p)-[:FUNDED_UNDER]->(t:Topic)
        RETURN p.id as id, p.title as title, p.acronym as acronym,
               p.objective as objective, p.ecMaxContribution as budget,
               p.status as status, p.fundingScheme as fundingScheme,
               p.startDate as start_date, p.endDate as end_date,
               COLLECT(DISTINCT c.code) as clusters,
               COLLECT(DISTINCT t.code) as topics
        ORDER BY p.startDate DESC
        LIMIT $limit
        """
        
        try:
            results = self.db.execute_query(query, params)
            return [
                {
                    "id": r.get("id"),
                    "title": r.get("title"),
                    "acronym": r.get("acronym"),
                    "objective": (r.get("objective") or "")[:300],
                    "budget": r.get("budget", 0) or 0,
                    "status": r.get("status"),
                    "funding_scheme": r.get("fundingScheme"),
                    "start_date": r.get("start_date"),
                    "end_date": r.get("end_date"),
                    "clusters": [c for c in r.get("clusters", []) if c],
                    "topics": [t for t in r.get("topics", []) if t],
                    "cordis_url": f"https://cordis.europa.eu/project/id/{r.get('id')}"
                }
                for r in results
            ]
        except Exception as e:
            logger.error(f"Error searching projects by keywords: {e}")
            return []
    
    def get_organization_collaboration_network(
        self,
        organization_name: str,
        depth: int = 1,
        limit: int = 50
    ) -> Dict[str, Any]:
        """
        Get the collaboration network of an organization.
        
        Args:
            organization_name: Name of the organization
            depth: How many hops of collaboration to explore (1 = direct partners)
            limit: Maximum number of collaborating organizations to return
            
        Returns:
            Dict with organization network data
        """
        params = {'org_name': organization_name.lower(), 'depth': depth, 'limit': limit}
        
        query = """
        MATCH (o1:Organization)-[:PARTICIPATES_IN]->(p:Project)<-[:PARTICIPATES_IN]-(o2:Organization)
        WHERE (toLower(o1.name) CONTAINS $org_name OR toLower(o1.shortName) CONTAINS $org_name)
          AND o1 <> o2
        WITH o1, o2, COUNT(DISTINCT p) as collaboration_count
        ORDER BY collaboration_count DESC
        LIMIT $limit
        RETURN o1.name as source_org, o1.country as source_country,
               o2.name as partner_org, o2.country as partner_country,
               o2.activityType as partner_type, o2.sme as partner_is_sme,
               collaboration_count
        """
        
        try:
            results = self.db.execute_query(query, params)
            
            partners = []
            source_org = None
            source_country = None
            
            for r in results:
                if not source_org:
                    source_org = r.get('source_org')
                    source_country = r.get('source_country')
                
                partners.append({
                    'name': r.get('partner_org'),
                    'country': r.get('partner_country'),
                    'type': r.get('partner_type'),
                    'is_sme': r.get('partner_is_sme'),
                    'collaborations': r.get('collaboration_count')
                })
            
            return {
                'success': True,
                'organization': source_org,
                'country': source_country,
                'partners': partners,
                'total_partners': len(partners)
            }
        except Exception as e:
            logger.error(f"Error getting collaboration network: {e}")
            return {'success': False, 'error': str(e), 'partners': []}
    
    def get_cluster_statistics(
        self,
        cluster_code: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get statistics for clusters - project counts, funding, etc.
        
        Args:
            cluster_code: Optional specific cluster code. If None, returns all clusters.
            
        Returns:
            List of cluster statistics
        """
        params = {}
        where_clause = ""
        
        if cluster_code:
            where_clause = "WHERE c.code = $cluster_code"
            params['cluster_code'] = cluster_code
        
        query = f"""
        MATCH (c:Cluster)<-[:TARGETS]-(p:Project)
        {where_clause}
        WITH c, 
             COUNT(DISTINCT p) as project_count,
             SUM(p.ecMaxContribution) as total_funding,
             AVG(p.ecMaxContribution) as avg_budget,
             COLLECT(DISTINCT p.fundingScheme) as funding_schemes
        RETURN c.code as code, c.name as name, c.pillar as pillar,
               project_count, total_funding, avg_budget, funding_schemes
        ORDER BY project_count DESC
        """
        
        try:
            results = self.db.execute_query(query, params)
            return [
                {
                    "code": r.get("code"),
                    "name": r.get("name"),
                    "pillar": r.get("pillar"),
                    "project_count": r.get("project_count", 0),
                    "total_funding": r.get("total_funding", 0) or 0,
                    "avg_budget": r.get("avg_budget", 0) or 0,
                    "funding_schemes": [s for s in r.get("funding_schemes", []) if s]
                }
                for r in results
            ]
        except Exception as e:
            logger.error(f"Error getting cluster statistics: {e}")
            return []

    # ========================================================================
    # ERASMUS+ PROGRAMME QUERIES
    # ========================================================================

    def get_erasmus_actions(
        self,
        key_action: Optional[str] = None,
        sector: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get Erasmus+ actions with their metadata.

        Args:
            key_action: Filter by key action (KA1, KA2, KA3, JMO, SPORT)
            sector: Filter by sector (HED, VET, SCH, ADU, YOU, SPORT)

        Returns:
            List of Erasmus+ actions with full metadata
        """
        where_clauses = []
        params = {}

        if key_action:
            where_clauses.append("a.key_action = $key_action")
            params["key_action"] = key_action.upper()

        if sector:
            where_clauses.append("a.sector = $sector")
            params["sector"] = sector.upper()

        where_clause = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""

        query = f"""
        MATCH (a:ErasmusAction)
        {where_clause}
        OPTIONAL MATCH (a)-[:AVAILABLE_IN]->(s:ErasmusSector)
        OPTIONAL MATCH (a)-[:REQUIRES_COORDINATOR_FROM]->(cr:PartnerRegion)
        OPTIONAL MATCH (a)-[:ALLOWS_PARTNERS_FROM]->(pr:PartnerRegion)

        RETURN a.code as code,
               a.name as name,
               a.key_action as key_action,
               a.description as description,
               a.min_partners as min_partners,
               a.min_countries as min_countries,
               a.requires_eche as requires_eche,
               a.duration_months_min as duration_min,
               a.duration_months_max as duration_max,
               a.typical_budget_min as budget_min,
               a.typical_budget_max as budget_max,
               a.funding_model as funding_model,
               s.code as sector_code,
               s.name as sector_name,
               cr.code as coordinator_region,
               pr.code as partner_region
        ORDER BY a.key_action, a.code
        """

        try:
            results = self.db.execute_query(query, params)
            return [
                {
                    "code": r.get("code"),
                    "name": r.get("name"),
                    "key_action": r.get("key_action"),
                    "description": r.get("description"),
                    "min_partners": r.get("min_partners", 1),
                    "min_countries": r.get("min_countries", 1),
                    "requires_eche": r.get("requires_eche", False),
                    "duration_months": {
                        "min": r.get("duration_min"),
                        "max": r.get("duration_max")
                    },
                    "typical_budget": {
                        "min": r.get("budget_min"),
                        "max": r.get("budget_max")
                    },
                    "funding_model": r.get("funding_model"),
                    "sector": {
                        "code": r.get("sector_code"),
                        "name": r.get("sector_name")
                    },
                    "coordinator_region": r.get("coordinator_region"),
                    "partner_region": r.get("partner_region"),
                    "source": "neo4j_graph"
                }
                for r in results
            ]
        except Exception as e:
            logger.error(f"Error getting Erasmus+ actions: {e}")
            return []

    def get_erasmus_sectors(self) -> List[Dict[str, Any]]:
        """
        Get all Erasmus+ sectors with their available actions.

        Returns:
            List of sectors with action counts
        """
        query = """
        MATCH (s:ErasmusSector)
        OPTIONAL MATCH (a:ErasmusAction)-[:AVAILABLE_IN]->(s)

        WITH s, COLLECT(DISTINCT a.code) as actions, COUNT(DISTINCT a) as action_count

        RETURN s.code as code,
               s.name as name,
               s.description as description,
               s.org_types as org_types,
               actions,
               action_count
        ORDER BY s.code
        """

        try:
            results = self.db.execute_query(query)
            return [
                {
                    "code": r.get("code"),
                    "name": r.get("name"),
                    "description": r.get("description"),
                    "org_types": r.get("org_types", []),
                    "actions": r.get("actions", []),
                    "action_count": r.get("action_count", 0),
                    "source": "neo4j_graph"
                }
                for r in results
            ]
        except Exception as e:
            logger.error(f"Error getting Erasmus+ sectors: {e}")
            return []

    def check_erasmus_country_eligibility(
        self,
        country_code: str,
        action_code: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Check if a country is eligible for Erasmus+ actions.

        Args:
            country_code: ISO country code (e.g., "DE", "FR")
            action_code: Optional specific action code (e.g., "KA2-COOP-HED")

        Returns:
            Eligibility status with eligible actions
        """
        country_code = country_code.upper().strip()

        # First check which regions the country belongs to
        region_query = """
        MATCH (r:PartnerRegion)
        WHERE $country_code IN r.countries
        RETURN r.code as region_code, r.name as region_name
        """

        try:
            regions = self.db.execute_query(region_query, {"country_code": country_code})

            is_programme_country = any(r.get("region_code") == "PROGRAMME" for r in regions)
            region_codes = [r.get("region_code") for r in regions]

            # Find eligible actions
            action_params = {"regions": region_codes}
            action_where = ""

            if action_code:
                action_where = "AND a.code = $action_code"
                action_params["action_code"] = action_code.upper()

            action_query = f"""
            MATCH (a:ErasmusAction)
            OPTIONAL MATCH (a)-[:REQUIRES_COORDINATOR_FROM]->(cr:PartnerRegion)
            OPTIONAL MATCH (a)-[:ALLOWS_PARTNERS_FROM]->(pr:PartnerRegion)
            WHERE (cr.code IN $regions OR pr.code IN $regions OR cr.code = 'WORLDWIDE' OR pr.code = 'WORLDWIDE')
            {action_where}

            RETURN a.code as code,
                   a.name as name,
                   a.key_action as key_action,
                   a.requires_eche as requires_eche,
                   cr.code as coordinator_region,
                   pr.code as partner_region,
                   CASE WHEN cr.code IN $regions OR cr.code = 'WORLDWIDE' THEN true ELSE false END as can_coordinate,
                   CASE WHEN pr.code IN $regions OR pr.code = 'WORLDWIDE' THEN true ELSE false END as can_participate
            ORDER BY a.key_action, a.code
            """

            eligible_actions = self.db.execute_query(action_query, action_params)

            coordinator_actions = [a for a in eligible_actions if a.get("can_coordinate")]
            participant_actions = [a for a in eligible_actions if a.get("can_participate")]

            return {
                "country_code": country_code,
                "is_programme_country": is_programme_country,
                "regions": region_codes,
                "can_coordinate_actions": [
                    {
                        "code": a.get("code"),
                        "name": a.get("name"),
                        "key_action": a.get("key_action"),
                        "requires_eche": a.get("requires_eche", False)
                    }
                    for a in coordinator_actions
                ],
                "can_participate_actions": [
                    {
                        "code": a.get("code"),
                        "name": a.get("name"),
                        "key_action": a.get("key_action")
                    }
                    for a in participant_actions
                ],
                "eligible_as_coordinator": len(coordinator_actions) > 0,
                "eligible_as_partner": len(participant_actions) > 0,
                "notes": [
                    "Programme Countries can coordinate most actions" if is_programme_country
                    else "Partner Countries have limited coordination options",
                    "ECHE required for HEIs in Programme Countries for mobility actions"
                ],
                "source": "neo4j_graph"
            }

        except Exception as e:
            logger.error(f"Error checking Erasmus+ country eligibility: {e}")
            return {
                "country_code": country_code,
                "error": str(e),
                "eligible_as_coordinator": False,
                "eligible_as_partner": False,
                "source": "fallback"
            }

    def get_erasmus_action_details(self, action_code: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific Erasmus+ action.

        Args:
            action_code: Action code (e.g., "KA2-COOP-HED", "JMO-MODULE")

        Returns:
            Detailed action information including requirements
        """
        query = """
        MATCH (a:ErasmusAction {code: $action_code})
        OPTIONAL MATCH (a)-[:AVAILABLE_IN]->(s:ErasmusSector)
        OPTIONAL MATCH (a)-[:REQUIRES_COORDINATOR_FROM]->(cr:PartnerRegion)
        OPTIONAL MATCH (a)-[:ALLOWS_PARTNERS_FROM]->(pr:PartnerRegion)

        RETURN a.code as code,
               a.name as name,
               a.key_action as key_action,
               a.description as description,
               a.min_partners as min_partners,
               a.min_countries as min_countries,
               a.requires_eche as requires_eche,
               a.coordinator_countries as coordinator_countries,
               a.partner_countries as partner_countries,
               a.duration_months_min as duration_min,
               a.duration_months_max as duration_max,
               a.typical_budget_min as budget_min,
               a.typical_budget_max as budget_max,
               a.funding_model as funding_model,
               s.code as sector_code,
               s.name as sector_name,
               s.org_types as sector_org_types,
               cr.code as coordinator_region,
               cr.countries as coordinator_countries_list,
               pr.code as partner_region,
               pr.countries as partner_countries_list
        """

        try:
            results = self.db.execute_query(query, {"action_code": action_code.upper()})

            if not results:
                return None

            r = results[0]
            return {
                "code": r.get("code"),
                "name": r.get("name"),
                "key_action": r.get("key_action"),
                "description": r.get("description"),
                "requirements": {
                    "min_partners": r.get("min_partners", 1),
                    "min_countries": r.get("min_countries", 1),
                    "requires_eche": r.get("requires_eche", False),
                },
                "duration": {
                    "min_months": r.get("duration_min"),
                    "max_months": r.get("duration_max")
                },
                "budget": {
                    "typical_min": r.get("budget_min"),
                    "typical_max": r.get("budget_max"),
                    "funding_model": r.get("funding_model")
                },
                "sector": {
                    "code": r.get("sector_code"),
                    "name": r.get("sector_name"),
                    "eligible_org_types": r.get("sector_org_types", [])
                },
                "country_eligibility": {
                    "coordinator_region": r.get("coordinator_region"),
                    "partner_region": r.get("partner_region")
                },
                "source": "neo4j_graph"
            }

        except Exception as e:
            logger.error(f"Error getting Erasmus+ action details: {e}")
            return None

    def find_eligible_erasmus_actions(
        self,
        country_code: str,
        sector: Optional[str] = None,
        role: str = "participant"
    ) -> List[Dict[str, Any]]:
        """
        Find Erasmus+ actions that an organization from a country can participate in.

        Args:
            country_code: ISO country code
            sector: Optional sector filter (HED, VET, SCH, ADU, YOU, SPORT)
            role: "coordinator" or "participant"

        Returns:
            List of eligible actions with requirements
        """
        country_code = country_code.upper()

        # First determine which regions the country belongs to
        region_query = """
        MATCH (r:PartnerRegion)
        WHERE $country_code IN r.countries
        RETURN COLLECT(r.code) as regions
        """

        try:
            region_result = self.db.execute_query(region_query, {"country_code": country_code})
            regions = region_result[0].get("regions", []) if region_result else []

            # Build action query
            params = {"regions": regions}
            sector_filter = ""

            if sector:
                sector_filter = "AND a.sector = $sector"
                params["sector"] = sector.upper()

            if role == "coordinator":
                region_match = """
                MATCH (a)-[:REQUIRES_COORDINATOR_FROM]->(r:PartnerRegion)
                WHERE r.code IN $regions OR r.code = 'WORLDWIDE'
                """
            else:
                region_match = """
                MATCH (a)-[:ALLOWS_PARTNERS_FROM]->(r:PartnerRegion)
                WHERE r.code IN $regions OR r.code = 'WORLDWIDE'
                """

            query = f"""
            MATCH (a:ErasmusAction)
            {region_match}
            {sector_filter}
            OPTIONAL MATCH (a)-[:AVAILABLE_IN]->(s:ErasmusSector)

            RETURN a.code as code,
                   a.name as name,
                   a.key_action as key_action,
                   a.description as description,
                   a.min_partners as min_partners,
                   a.min_countries as min_countries,
                   a.requires_eche as requires_eche,
                   a.typical_budget_min as budget_min,
                   a.typical_budget_max as budget_max,
                   s.code as sector_code,
                   s.name as sector_name
            ORDER BY a.key_action, a.code
            """

            results = self.db.execute_query(query, params)
            return [
                {
                    "code": r.get("code"),
                    "name": r.get("name"),
                    "key_action": r.get("key_action"),
                    "description": r.get("description"),
                    "requirements": {
                        "min_partners": r.get("min_partners", 1),
                        "min_countries": r.get("min_countries", 1),
                        "requires_eche": r.get("requires_eche", False)
                    },
                    "typical_budget": {
                        "min": r.get("budget_min"),
                        "max": r.get("budget_max")
                    },
                    "sector": {
                        "code": r.get("sector_code"),
                        "name": r.get("sector_name")
                    },
                    "eligible_role": role,
                    "source": "neo4j_graph"
                }
                for r in results
            ]

        except Exception as e:
            logger.error(f"Error finding eligible Erasmus+ actions: {e}")
            return []

    def get_partner_regions(self) -> List[Dict[str, Any]]:
        """
        Get all Erasmus+ partner regions with their countries.

        Returns:
            List of partner regions
        """
        query = """
        MATCH (r:PartnerRegion)
        RETURN r.code as code,
               r.name as name,
               r.description as description,
               r.countries as countries,
               SIZE(r.countries) as country_count
        ORDER BY r.code
        """

        try:
            results = self.db.execute_query(query)
            return [
                {
                    "code": r.get("code"),
                    "name": r.get("name"),
                    "description": r.get("description"),
                    "countries": r.get("countries", []),
                    "country_count": r.get("country_count", 0),
                    "source": "neo4j_graph"
                }
                for r in results
            ]
        except Exception as e:
            logger.error(f"Error getting partner regions: {e}")
            return []


# Module-level instance for convenience
graph_search = GraphSearchService()


if __name__ == "__main__":
    # Test the service
    service = GraphSearchService()
    
    logger.info("\n" + "=" * 60)
    logger.info("GRAPH SEARCH SERVICE TEST")
    logger.info("=" * 60)
    
    # Test cluster overview
    logger.info("\n🎯 Cluster Overview:")
    for cluster in service.get_cluster_overview():
        logger.info(f"   {cluster['code']}: {cluster['project_count']} projects, €{cluster['total_funding']:,.0f}")
    
    # Test eligibility check
    logger.info("\n🌍 Eligibility Check (Germany):")
    result = service.check_country_eligibility("DE")
    logger.info(f"   Status: {result['eligibility_status']}")
    logger.info(f"   Projects: {result['participation_history'].get('project_count', 0)}")
    
    logger.info("\n🌍 Eligibility Check (Switzerland):")
    result = service.check_country_eligibility("CH")
    logger.info(f"   Status: {result['eligibility_status']}")
    logger.info(f"   Notes: {result['notes']}")
    
    # Test budget statistics
    logger.info("\n💰 Budget Statistics by Cluster:")
    for stat in service.get_budget_statistics():
        logger.info(f"   {stat['cluster_code']}: avg €{stat['avg_budget']:,.0f}, max €{stat['max_budget']:,.0f}")
    
    # Test consortium patterns
    logger.info("\n👥 Consortium Patterns:")
    for pattern in service.get_consortium_patterns():
        logger.info(f"   {pattern['cluster_code']}: {pattern['avg_partners']:.1f} partners, {pattern['avg_countries']:.1f} countries")
    
    # Test topic search
    logger.info("\n🔍 Topic Search (DATA):")
    topics = service.search_topics("DATA", limit=5)
    for t in topics:
        logger.info(f"   {t['code']}: {t['projectCount']} projects")
    
    logger.info("\n✅ Graph Search Service test complete!")


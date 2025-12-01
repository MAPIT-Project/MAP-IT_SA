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
            eligibility_status = "Associated Country - Check specific call conditions"
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
                notes.append("Switzerland: Check current association status - may have restrictions")
            if country_code == "UK":
                notes.append("UK: Post-Brexit association - verify current participation rules")
            if not is_eligible:
                notes.append("Third countries may participate under specific conditions - check call text")
            
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
        where_clauses = []
        params = {"limit": limit}
        
        if cluster_code:
            where_clauses.append("c.code = $cluster_code")
            params["cluster_code"] = cluster_code.upper()
        
        if country_code:
            where_clauses.append("co.isoCode = $country_code")
            params["country_code"] = country_code.upper()
        
        where_clause = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""
        
        query = f"""
        MATCH (o:Organization)-[r:PARTICIPATES_IN]->(p:Project)
        OPTIONAL MATCH (p)-[:TARGETS]->(c:Cluster)
        OPTIONAL MATCH (o)-[:LOCATED_IN]->(co:Country)
        {where_clause}
        
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


# Module-level instance for convenience
graph_search = GraphSearchService()


if __name__ == "__main__":
    # Test the service
    service = GraphSearchService()
    
    print("\n" + "=" * 60)
    print("GRAPH SEARCH SERVICE TEST")
    print("=" * 60)
    
    # Test cluster overview
    print("\n🎯 Cluster Overview:")
    for cluster in service.get_cluster_overview():
        print(f"   {cluster['code']}: {cluster['project_count']} projects, €{cluster['total_funding']:,.0f}")
    
    # Test eligibility check
    print("\n🌍 Eligibility Check (Germany):")
    result = service.check_country_eligibility("DE")
    print(f"   Status: {result['eligibility_status']}")
    print(f"   Projects: {result['participation_history'].get('project_count', 0)}")
    
    print("\n🌍 Eligibility Check (Switzerland):")
    result = service.check_country_eligibility("CH")
    print(f"   Status: {result['eligibility_status']}")
    print(f"   Notes: {result['notes']}")
    
    # Test budget statistics
    print("\n💰 Budget Statistics by Cluster:")
    for stat in service.get_budget_statistics():
        print(f"   {stat['cluster_code']}: avg €{stat['avg_budget']:,.0f}, max €{stat['max_budget']:,.0f}")
    
    # Test consortium patterns
    print("\n👥 Consortium Patterns:")
    for pattern in service.get_consortium_patterns():
        print(f"   {pattern['cluster_code']}: {pattern['avg_partners']:.1f} partners, {pattern['avg_countries']:.1f} countries")
    
    # Test topic search
    print("\n🔍 Topic Search (DATA):")
    topics = service.search_topics("DATA", limit=5)
    for t in topics:
        print(f"   {t['code']}: {t['projectCount']} projects")
    
    print("\n✅ Graph Search Service test complete!")


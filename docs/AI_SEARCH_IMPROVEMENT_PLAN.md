# AI Search Improvement Plan for CORDIS Database

## Executive Summary
This document outlines a comprehensive plan to improve AI search capabilities by better leveraging the structured data in the `projects` and `organizations` tables. The goal is to eliminate "Unknown programme framework" responses and provide rich, contextual answers about European research projects.

## Current Problem Analysis

### Issue: "Unknown Programme Framework" in AI Responses
The AI currently states that most projects fall under an "Unknown" programme framework because:

1. **Incomplete Data Retrieval**: The system only fetches basic project information, missing the `frameworkProgramme` field
2. **Limited Join Operations**: Not leveraging the full relationship between projects and organizations
3. **Missing Aggregations**: No consortium statistics or geographic distribution data
4. **Poor Context**: Embeddings don't include organizational or programme metadata

## Solution Architecture

### 1. Enhanced Data Model

#### A. Composite Project Embeddings
Create embeddings that combine multiple data sources:

```python
def create_composite_embedding(project):
    """
    Create a rich embedding combining project and organization data
    """
    text_components = [
        f"Title: {project['title']}",
        f"Objective: {project['objective']}",
        f"Topics: {project['topics']}",
        f"Keywords: {project['keywords']}",
        f"Programme: {project['frameworkProgramme']} - {project['fundingScheme']}",
        f"Coordinator: {project['coordinator_name']} ({project['coordinator_country']})",
        f"Partners: {', '.join(project['participant_countries'])}",
        f"Consortium: {project['participant_count']} organizations from {project['country_count']} countries",
        f"Budget: EUR {project['totalCost']:,.0f}",
        f"Period: {project['startDate']} to {project['endDate']}"
    ]
    
    composite_text = " | ".join(text_components)
    return generate_embedding(composite_text)
```

#### B. Metadata-Enhanced Search
Augment vector search with structured filters:

```sql
-- Enhanced search query with full context
WITH project_context AS (
    SELECT 
        p.*,
        -- Consortium composition
        COUNT(DISTINCT o.organisationID) as consortium_size,
        COUNT(DISTINCT o.country) as country_count,
        COUNT(CASE WHEN o.SME = true THEN 1 END) as sme_count,
        
        -- Geographic distribution
        ARRAY_AGG(DISTINCT o.country ORDER BY o.country) as countries,
        ARRAY_AGG(DISTINCT o.city ORDER BY o.city) FILTER (WHERE o.city IS NOT NULL) as cities,
        
        -- Organization types
        ARRAY_AGG(DISTINCT o.activityType ORDER BY o.activityType) as activity_types,
        
        -- Key participants
        MAX(CASE WHEN o.role = 'coordinator' THEN o.name END) as coordinator_name,
        MAX(CASE WHEN o.role = 'coordinator' THEN o.country END) as coordinator_country,
        
        -- Financial aggregations
        SUM(o.ecContribution) as total_ec_contribution,
        AVG(o.ecContribution) as avg_org_contribution,
        
        -- Participation details
        STRING_AGG(
            DISTINCT o.name || ' (' || o.country || ')',
            ', ' ORDER BY o.role DESC, o.name
        ) as participant_summary
        
    FROM projects p
    LEFT JOIN organizations o ON p.id = o.projectID
    WHERE 
        -- Vector similarity condition
        p.embedding <=> query_embedding < 0.3
        -- Additional structured filters
        AND p.frameworkProgramme IN ('HORIZON', 'H2020')
        AND p.totalCost > 1000000
    GROUP BY p.id
)
SELECT * FROM project_context
ORDER BY similarity_score DESC
LIMIT 10;
```

### 2. Data Transformation Pipeline

#### Phase 1: Data Enrichment (Immediate)
```python
def enrich_project_data(project_id):
    """
    Enrich project data with full organizational context
    """
    # Get base project data
    project = fetch_project(project_id)
    
    # Add organizational context
    orgs = fetch_organizations(project_id)
    
    # Compute aggregations
    project['consortium_size'] = len(orgs)
    project['countries'] = list(set(org['country'] for org in orgs))
    project['country_count'] = len(project['countries'])
    project['sme_participation'] = sum(1 for org in orgs if org['SME'])
    project['coordinator'] = next((org for org in orgs if org['role'] == 'coordinator'), None)
    
    # Add programme details
    project['programme_full'] = f"{project['frameworkProgramme']} - {project['fundingScheme']}"
    project['programme_period'] = get_programme_period(project['frameworkProgramme'])
    
    # Geographic scope
    if project['country_count'] > 10:
        project['geographic_scope'] = 'Large International Consortium'
    elif project['country_count'] > 5:
        project['geographic_scope'] = 'International Consortium'
    elif project['country_count'] > 1:
        project['geographic_scope'] = 'European Collaboration'
    else:
        project['geographic_scope'] = 'National Project'
    
    return project
```

#### Phase 2: Embedding Generation (Short-term)
```python
def generate_enhanced_embeddings():
    """
    Generate embeddings for all projects with full context
    """
    projects = fetch_all_projects()
    
    for project in projects:
        # Enrich with organizational data
        enriched = enrich_project_data(project['id'])
        
        # Create composite text for embedding
        embedding_text = create_embedding_text(enriched)
        
        # Generate embedding
        embedding = embedding_service.generate(embedding_text)
        
        # Store in vector database
        store_project_embedding(project['id'], embedding, enriched)
```

### 3. Search Enhancement Strategy

#### A. Hybrid Search Implementation
Combine vector similarity with structured queries:

```python
def enhanced_search(query, filters=None):
    """
    Perform hybrid search combining vector and structured search
    """
    # Step 1: Vector search for semantic similarity
    vector_results = vector_search(query, top_k=50)
    
    # Step 2: Apply structured filters
    if filters:
        filtered_results = apply_filters(vector_results, filters)
    else:
        filtered_results = vector_results
    
    # Step 3: Boost by metadata relevance
    boosted_results = apply_metadata_boost(filtered_results, query)
    
    # Step 4: Enrich with full context
    enriched_results = [enrich_project_data(r['id']) for r in boosted_results[:10]]
    
    # Step 5: Generate comprehensive answer
    answer = generate_contextual_answer(query, enriched_results)
    
    return {
        'answer': answer,
        'projects': enriched_results,
        'metadata': extract_portfolio_insights(enriched_results)
    }
```

#### B. Metadata Boosting Algorithm
```python
def apply_metadata_boost(results, query):
    """
    Boost results based on metadata relevance
    """
    query_lower = query.lower()
    
    for result in results:
        boost_score = 0
        
        # Programme relevance
        if 'horizon' in query_lower and 'HORIZON' in result['frameworkProgramme']:
            boost_score += 0.2
        
        # Recency boost
        years_old = (datetime.now().year - int(result['startDate'][:4]))
        if years_old < 2:
            boost_score += 0.15
        elif years_old < 5:
            boost_score += 0.1
        
        # Consortium size relevance
        if 'collaboration' in query_lower or 'consortium' in query_lower:
            if result['country_count'] > 10:
                boost_score += 0.15
        
        # Budget relevance
        if 'large' in query_lower or 'major' in query_lower:
            if result['totalCost'] > 10000000:
                boost_score += 0.1
        
        # Apply boost
        result['final_score'] = result['similarity_score'] + boost_score
    
    return sorted(results, key=lambda x: x['final_score'], reverse=True)
```

### 4. Answer Generation Enhancement

#### A. Contextual Answer Template
```python
def generate_contextual_answer(query, projects):
    """
    Generate rich, contextual answer with full project details
    """
    # Analyze portfolio
    insights = analyze_project_portfolio(projects)
    
    # Create structured answer
    answer_parts = []
    
    # Overview
    answer_parts.append(f"Based on the CORDIS database, I found {len(projects)} relevant projects:")
    
    # Programme distribution
    programmes = {}
    for p in projects:
        prog = p['frameworkProgramme']
        programmes[prog] = programmes.get(prog, 0) + 1
    
    answer_parts.append("\n**Programme Distribution:**")
    for prog, count in programmes.items():
        answer_parts.append(f"- {prog}: {count} projects")
    
    # Project details
    answer_parts.append("\n**Key Projects:**")
    for i, project in enumerate(projects[:5], 1):
        answer_parts.append(f"""
{i}. **{project['title']}** ({project['acronym']})
   - Programme: {project['frameworkProgramme']} - {project['fundingScheme']}
   - Coordinator: {project['coordinator_name']} ({project['coordinator_country']})
   - Consortium: {project['consortium_size']} partners from {project['country_count']} countries
   - Budget: €{project['totalCost']:,.0f} (EU: €{project['ecMaxContribution']:,.0f})
   - Period: {project['startDate']} to {project['endDate']}
   - Status: {project['status']}
   - CORDIS: https://cordis.europa.eu/project/id/{project['id']}
        """)
    
    # Portfolio insights
    answer_parts.append(f"\n**Portfolio Insights:**")
    answer_parts.append(insights)
    
    return "\n".join(answer_parts)
```

### 5. Implementation Roadmap

#### Week 1: Foundation
- [x] Document database schema
- [ ] Create data enrichment functions
- [ ] Test enhanced query patterns

#### Week 2: Embeddings
- [ ] Implement composite embedding generation
- [ ] Create embedding pipeline for existing projects
- [ ] Store enhanced embeddings in Supabase

#### Week 3: Search Enhancement
- [ ] Implement hybrid search
- [ ] Add metadata boosting
- [ ] Create faceted search capabilities

#### Week 4: Integration
- [ ] Update RAG service to use enhanced search
- [ ] Modify answer generation templates
- [ ] Add portfolio analysis features

### 6. Testing Strategy

#### Test Cases
1. **Programme Identification**: "What Horizon Europe projects focus on AI?"
   - Expected: Clear programme identification, no "Unknown"
   
2. **Consortium Analysis**: "Show me large international collaborations in renewable energy"
   - Expected: Projects with 10+ countries, consortium details
   
3. **Geographic Search**: "German-coordinated projects in healthcare"
   - Expected: Projects with German coordinators, health topics
   
4. **Budget Queries**: "Major projects over 10M EUR in quantum computing"
   - Expected: High-budget projects with financial details
   
5. **Temporal Queries**: "Recent projects started in 2024"
   - Expected: Current projects with accurate dates

### 7. Success Metrics

1. **Accuracy**: 95% of projects correctly identify programme framework
2. **Completeness**: All answers include consortium and budget information
3. **Relevance**: Top 5 results have >0.8 relevance score
4. **Performance**: Search completes in <2 seconds
5. **User Satisfaction**: Eliminate need for "check CORDIS directly" disclaimers

## Conclusion

By implementing this comprehensive plan, we will transform the AI search from a simple text-matching system to a sophisticated, context-aware search engine that fully leverages the rich structured data available in the CORDIS database. The key improvements are:

1. **Complete Data Utilization**: Use all fields from both tables
2. **Relationship Awareness**: Leverage project-organization connections
3. **Rich Embeddings**: Include metadata in vector representations
4. **Hybrid Search**: Combine vector and structured queries
5. **Contextual Answers**: Provide comprehensive, accurate responses

This will eliminate the "Unknown programme framework" issue and provide users with detailed, actionable insights about European research projects.
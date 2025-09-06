# CORDIS Database Schema Documentation

## Overview
This document provides comprehensive documentation of the `projects` and `organizations` tables in the PostgreSQL database that contains ALL projects from the CORDIS website and ALL organizations that have participated in these projects.

## Database Connection
- **Connection String**: `postgresql://postgres:postgres@localhost:54322/postgres`
- **Database Type**: PostgreSQL with full-text search capabilities
- **Indexes**: Full-text search indexes on title, objective, and topics fields

## Projects Table Structure

Based on the code analysis from [`app/services/rag_service.py`](../app/services/rag_service.py), the `projects` table contains the following attributes:

### Core Identification Fields
- **`id`** (Primary Key): Unique identifier for the project
- **`rcn`**: Research Call Number - CORDIS-specific identifier
- **`acronym`**: Short project acronym (e.g., "AI4HEALTH")
- **`title`**: Full project title
- **`status`**: Current project status (e.g., "SIGNED", "CLOSED", "TERMINATED")
- **`grantDoi`**: Digital Object Identifier for the grant

### Temporal Fields
- **`startDate`**: Project start date (DATE)
- **`endDate`**: Project end date (DATE)
- **`periodFrom`**: Funding period start
- **`periodTo`**: Funding period end

### Financial Fields
- **`totalCost`** (DECIMAL): Total project cost in EUR
- **`ecMaxContribution`** (DECIMAL): Maximum EU contribution in EUR

### Content/Description Fields
- **`objective`** (TEXT): Detailed project objectives and description
- **`topics`** (TEXT): Research topics and keywords
- **`keywords`** (TEXT): Additional keywords for search

### Programme Information
- **`frameworkProgramme`**: Framework programme (e.g., "HORIZON", "FP7", "H2020")
- **`fundingScheme`**: Type of funding scheme (e.g., "RIA", "CSA", "IA", "MSCA-IF")
- **`legalBasis`**: Legal basis for the funding
- **`programme`**: Specific programme details

### Call Information
- **`callIdentifier`**: Identifier of the call for proposals
- **`callTitle`**: Title of the call
- **`callDeadline`**: Submission deadline for the call

## Organizations Table Structure

The `organizations` table contains ALL organizations that have participated in projects:

### Core Identification Fields
- **`organisationID`** (Primary Key): Unique identifier for the organization
- **`projectID`** (Foreign Key): Links to projects.id
- **`name`**: Full organization name
- **`legalName`**: Legal registered name
- **`shortName`**: Abbreviated name

### Geographic Information
- **`country`**: Country code (ISO)
- **`city`**: City location
- **`postCode`**: Postal code
- **`street`**: Street address
- **`nutsCode`**: NUTS (Nomenclature of Territorial Units for Statistics) code

### Organization Details
- **`activityType`**: Type of activity (e.g., "REC", "HES", "PRC", "SME")
  - REC: Research organizations
  - HES: Higher education establishments
  - PRC: Private companies
  - SME: Small and Medium Enterprises
  - PUB: Public bodies
  - OTH: Other
- **`SME`** (BOOLEAN): Whether the organization is an SME
- **`role`**: Role in the project ("coordinator" or "participant")

### Financial Information
- **`ecContribution`** (DECIMAL): EU contribution to this organization
- **`netEcContribution`** (DECIMAL): Net EU contribution
- **`totalCost`** (DECIMAL): Total cost for this organization

## Key Relationships

1. **One-to-Many**: One project can have multiple organizations
2. **Coordinator**: Each project has exactly one coordinator (role='coordinator')
3. **Participants**: Projects can have multiple participants (role='participant')

## Data Quality Insights

### Coverage
- **Temporal Coverage**: Projects from FP7 (2007-2013), H2020 (2014-2020), and Horizon Europe (2021-2027)
- **Geographic Coverage**: Organizations from all EU member states and associated countries
- **Completeness**: Most fields are populated, but some older projects may have missing data

### Common Query Patterns
Based on [`_search_local_database`](../app/services/rag_service.py:1730-1817):
1. Full-text search on title, objective, and topics
2. Date range filtering (startDate, endDate)
3. Budget filtering (totalCost ranges)
4. Country-based filtering through organizations
5. Framework programme filtering

## Improving AI Search Capabilities

### Current Limitations
The current system has these limitations that cause the "Unknown programme framework" issue:

1. **Limited Context**: The AI only searches project titles and objectives, missing rich organizational data
2. **No Relationship Awareness**: Doesn't leverage the connection between projects and organizations
3. **Missing Aggregations**: Doesn't provide consortium composition, geographic distribution, or funding patterns
4. **Incomplete Embeddings**: Current embeddings don't capture the full context of projects

### Proposed Improvements

#### 1. Enhanced Data Embeddings
Create composite embeddings that combine:
- Project objective (primary)
- Topics and keywords (secondary)
- Organization names and countries (contextual)
- Framework programme and funding scheme (categorical)

#### 2. Structured Data Integration
Enhance the vector search with structured metadata:
```sql
-- Example enhanced query
SELECT 
    p.*,
    COUNT(DISTINCT o.country) as country_diversity,
    COUNT(o.organisationID) as consortium_size,
    SUM(CASE WHEN o.SME = true THEN 1 ELSE 0 END) as sme_count,
    ARRAY_AGG(DISTINCT o.activityType) as activity_types,
    ARRAY_AGG(DISTINCT o.country) as countries_involved
FROM projects p
LEFT JOIN organizations o ON p.id = o.projectID
WHERE [search conditions]
GROUP BY p.id
```

#### 3. Pre-computed Aggregations
Create materialized views for common patterns:
- Project consortiums by country
- Funding distribution by programme
- Technology clusters by keywords
- Collaboration networks

#### 4. Contextual Enrichment
Add computed fields to improve search:
- `consortium_description`: Text summary of participating organizations
- `geographic_scope`: EU, International, National, Regional
- `technology_domain`: AI, Energy, Health, etc. (derived from keywords)
- `collaboration_score`: Measure of international collaboration

## Implementation Strategy

### Phase 1: Data Analysis and Documentation
1. Document all table attributes with examples ✓
2. Identify data quality issues
3. Map common query patterns

### Phase 2: Embedding Enhancement
1. Create composite embeddings for projects
2. Include organizational context in embeddings
3. Add programme and funding metadata

### Phase 3: Search Improvement
1. Implement hybrid search (vector + structured)
2. Add faceted search capabilities
3. Improve result ranking with metadata boost

### Phase 4: Context Enrichment
1. Pre-compute aggregations
2. Add relationship-aware search
3. Implement portfolio analysis features

## SQL Examples for Common Queries

### Find Projects by Technology and Country
```sql
SELECT DISTINCT p.*, 
       COUNT(DISTINCT o.country) as countries,
       ARRAY_AGG(DISTINCT o.name) as organizations
FROM projects p
JOIN organizations o ON p.id = o.projectID
WHERE p.objective ILIKE '%nuclear energy%'
  AND o.country IN ('DE', 'FR', 'IT')
GROUP BY p.id
ORDER BY p.startDate DESC;
```

### Get Project Portfolio Statistics
```sql
SELECT 
    p.frameworkProgramme,
    COUNT(DISTINCT p.id) as project_count,
    SUM(p.totalCost) as total_funding,
    AVG(p.totalCost) as avg_funding,
    COUNT(DISTINCT o.country) as countries_involved
FROM projects p
JOIN organizations o ON p.id = o.projectID
WHERE p.topics ILIKE '%artificial intelligence%'
GROUP BY p.frameworkProgramme
ORDER BY project_count DESC;
```

### Find Collaborative Projects
```sql
SELECT p.*, 
       COUNT(DISTINCT o.country) as country_count,
       COUNT(o.organisationID) as partner_count
FROM projects p
JOIN organizations o ON p.id = o.projectID
GROUP BY p.id
HAVING COUNT(DISTINCT o.country) > 5
ORDER BY country_count DESC;
```

## Recommendations for AI Context

When the AI searches for projects, it should:

1. **Always include organizational context**: Don't just search projects, include participating organizations
2. **Provide aggregated statistics**: Show consortium size, geographic distribution, SME participation
3. **Use programme metadata**: Always specify the framework programme and funding scheme
4. **Include temporal context**: Mention project duration and current status
5. **Show funding information**: Include both total cost and EU contribution
6. **Highlight collaboration**: Emphasize international partnerships and diverse consortiums

## Next Steps

1. **Immediate**: Update the [`_format_db_project_data`](../app/services/rag_service.py:1473-1575) function to include all organizational data
2. **Short-term**: Create composite embeddings that include organizational context
3. **Medium-term**: Implement pre-computed aggregations for common queries
4. **Long-term**: Build a knowledge graph of project-organization relationships

## Conclusion

The database contains rich, structured data about all CORDIS projects and participating organizations. By properly leveraging this data through enhanced embeddings, structured queries, and contextual enrichment, we can significantly improve the AI's ability to answer questions about European research projects. The key is to move beyond simple text search to a hybrid approach that combines vector similarity with structured metadata and relationship awareness.
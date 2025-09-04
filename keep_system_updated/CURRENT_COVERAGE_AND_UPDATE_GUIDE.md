# Current Coverage and System Update Guide

## Current System Coverage Analysis

### ✅ Currently Supported Clusters

**Horizon Europe Clusters:**
- **Cluster 4**: Digital, Industry and Space (Fully supported)
- **Cluster 1**: Health (Basic support via domain detection)
- **Cluster 2**: Culture, Creativity and Inclusive Society (Basic support)
- **Cluster 3**: Civil Security for Society (Basic support)
- **Cluster 5**: Climate, Energy and Mobility (Basic support)
- **Cluster 6**: Food, Bioeconomy, Natural Resources, Agriculture and Environment (Basic support)

### ✅ Currently Supported Technologies

**Core Technologies:**
- **AI & Machine Learning**: Full support with semantic detection
- **Cybersecurity**: Full support with semantic detection
- **Edge Computing**: Full support with semantic detection
- **Quantum Computing**: Full support with semantic detection
- **Data Spaces**: Full support with semantic detection
- **Digital Twins**: Full support with semantic detection
- **Clean Energy**: Basic support via keyword matching
- **Renewable Energy**: Basic support via keyword matching

### ✅ Currently Supported Programmes

**EU Programmes:**
- **Horizon Europe**: Full support (all clusters)
- **Digital Europe Programme**: Full support
- **EIC (European Innovation Council)**: Full support
- **ERC (European Research Council)**: Basic support
- **MSCA (Marie Skłodowska-Curie Actions)**: Basic support
- **Euratom**: Basic support
- **Joint Undertakings**: Basic support

### ✅ Currently Supported Filters

**Status Filters:**
- Open calls (31094502)
- Closed calls (31094503)
- Forthcoming calls (31094501)
- Available calls (Open + Forthcoming)

**Temporal Filters:**
- Next 30 days
- Next 60 days
- Next 90 days
- Recent (last 6 months)
- Very recent (last 3 months)
- Current year

**Domain-Specific Filters:**
- TRL levels (1-2, 3-4, 5-7, 8-9)
- Living labs and GovTech
- Standardization activities
- Digital twins
- EIC Accelerator cut-offs
- Mission calls
- Lump-sum vs actual cost funding
- SSH integration

## 🔄 Areas Needing Expansion

### Missing Cluster-Specific Support
- **Detailed cluster-specific filtering**: Currently only Cluster 4 has detailed support
- **Cluster-specific keywords**: Need comprehensive keyword mappings for all clusters
- **Cluster-specific action types**: Different clusters have different typical action types

### Missing Technology Coverage
- **Advanced manufacturing**: Limited support
- **Biotechnology**: Limited support
- **Nanotechnology**: Limited support
- **Advanced materials**: Limited support
- **Robotics**: Limited support
- **Internet of Things (IoT)**: Limited support
- **5G/6G technologies**: Limited support
- **Blockchain**: Limited support

### Missing Programme Coverage
- **Specific Joint Undertakings**: 
  - Clean Hydrogen JU
  - Batteries Europe
  - Chips JU
  - Smart Networks and Services JU
- **European Partnerships**: Limited coverage
- **National co-funding programmes**: Not covered
- **EIT Knowledge and Innovation Communities**: Not covered

## 📋 Update Procedures

### 1. Adding New Cluster Support

**File to modify**: [`app/services/intelligent_query_parser.py`](app/services/intelligent_query_parser.py:216)

**Example for adding Cluster 1 (Health):**
```python
# Add to domain_patterns
'cluster_1': [r'cluster\s*1', r'health.*research', r'medical.*research', r'healthcare'],

# Add to fallback_patterns in AI parser
'cluster_1': [r'cluster\s*1', r'health.*research'],

# Add cluster-specific filtering in enhanced_call_search.py
if specific_filters.get('cluster_1'):
    domain_filters.append({"term": {"programmeDivision": "Health"}})
```

### 2. Adding New Technology Support

**File to modify**: [`app/services/intelligent_query_parser.py`](app/services/intelligent_query_parser.py:237)

**Example for adding Robotics:**
```python
# Add to tech_patterns
'robotics': [r'robotics', r'robots', r'autonomous.*systems', r'automation'],

# Add to fallback_patterns in AI parser
'robotics': [r'robotics', r'robots'],

# Add semantic boost terms in enhanced_call_search.py
# (These would be automatically handled by the semantic tag API)
```

### 3. Adding New Programme Support

**File to modify**: [`app/services/enhanced_call_search.py`](app/services/enhanced_call_search.py:842)

**Example for adding Clean Hydrogen JU:**
```python
# Add to programme_mappings
'CLEAN HYDROGEN': 'Clean Hydrogen Joint Undertaking',
'HYDROGEN JU': 'Clean Hydrogen Joint Undertaking',

# Add identifier pattern recognition
if 'HYDROGEN' in identifier and 'JU' in identifier:
    return 'clean hydrogen technologies'
```

### 4. Adding New Filter Types

**File to modify**: [`app/services/intelligent_query_parser.py`](app/services/intelligent_query_parser.py:216)

**Example for adding Budget Filter:**
```python
# Add to domain_patterns
'budget_large': [r'budget.*over.*10.*million', r'large.*budget', r'10m\+'],
'budget_small': [r'small.*budget', r'under.*2.*million', r'sme.*funding'],

# Add specific filtering in enhanced_call_search.py
if specific_filters.get('budget_large'):
    # Add budget range filter to query
    pass
```

## 🔧 Configuration Files Overview

### Primary Configuration Files:

1. **Intelligent Query Parser** ([`app/services/intelligent_query_parser.py`](app/services/intelligent_query_parser.py))
   - Domain patterns (lines 216-226)
   - Technology patterns (lines 237-243)
   - Status keywords (lines 36-57)
   - Temporal keywords (lines 60-82)

2. **AI Query Parser** ([`app/services/ai_query_parser.py`](app/services/ai_query_parser.py))
   - Fallback patterns (lines 61-107)
   - Comprehensive prompt template (lines 109-188)

3. **Enhanced Call Search** ([`app/services/enhanced_call_search.py`](app/services/enhanced_call_search.py))
   - Domain filtering (lines 294-328)
   - Programme mappings (lines 842-861)
   - Action type mappings (lines 735-773)
   - Cluster mappings (lines 784-798)

### Supporting Files:

4. **RAG Service** ([`app/services/rag_service.py`](app/services/rag_service.py))
   - Main search orchestration
   - Cache management
   - API integration

5. **Call-Specific RAG** ([`app/services/call_specific_rag.py`](app/services/call_specific_rag.py))
   - Detailed call/topic analysis
   - Document-specific processing

## 🚀 Recommended Expansion Priorities

### Phase 1: Immediate (High Impact)
1. **Complete Cluster Support**: Add detailed support for Clusters 1, 2, 3, 5, 6
2. **Expand Technology Coverage**: Add robotics, IoT, advanced manufacturing
3. **Enhance Programme Support**: Add specific Joint Undertakings

### Phase 2: Short-term (Medium Impact)
1. **Budget Filtering**: Add budget range detection and filtering
2. **Consortium Requirements**: Detect consortium size requirements
3. **Geographic Filters**: Add country/region specific filtering

### Phase 3: Long-term (Advanced)
1. **Machine Learning Enhancement**: Train custom models for better intent detection
2. **Real-time API Integration**: Direct integration with EU portal APIs
3. **Predictive Analytics**: Predict call openings based on historical patterns

## 📊 Monitoring and Maintenance

### Regular Updates Needed:
1. **EU API Changes**: Monitor for changes in EU Funding & Tenders Portal API
2. **Programme Updates**: Track new Horizon Europe work programmes
3. **Technology Trends**: Update technology keywords as new trends emerge
4. **Cluster Changes**: Monitor cluster structure changes in Horizon Europe

### Quality Assurance:
1. **Monthly Testing**: Run comprehensive test suite with new questions
2. **Accuracy Monitoring**: Track parsing accuracy and adjust patterns
3. **Performance Monitoring**: Ensure response times remain optimal
4. **User Feedback**: Incorporate user queries to improve coverage

## 🛠️ Update Checklist

When adding new capabilities:

- [ ] Update intelligent query parser patterns
- [ ] Update AI parser fallback patterns  
- [ ] Add enhanced search filtering logic
- [ ] Update programme/action type mappings
- [ ] Add comprehensive test cases
- [ ] Update documentation
- [ ] Verify API integration works
- [ ] Test with real EU portal data

## 📈 Performance Considerations

When expanding coverage:

1. **Pattern Complexity**: Keep regex patterns efficient
2. **Cache Strategy**: Ensure new patterns don't break caching
3. **API Limits**: Respect EU API rate limits
4. **Response Times**: Monitor impact on search performance
5. **Memory Usage**: Watch for memory increases with new patterns

This system is designed to be extensible, and new capabilities can be added by following the patterns established for existing features. The modular architecture allows for targeted updates without affecting overall system stability.
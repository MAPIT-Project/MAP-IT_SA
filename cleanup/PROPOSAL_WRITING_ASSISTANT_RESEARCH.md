# 📝 Proposal Writing Assistant - Research & Architecture

## Executive Summary

This document outlines how to extend your current MAP-IT SA system from a **research & discovery tool** to a comprehensive **proposal writing assistant** for Horizon Europe grants. Your system already excels at helping users find and understand calls - now we'll enable them to write winning proposals.

---

## 🎯 Current System Capabilities (What You Have)

### ✅ Strong Foundation
Your system already has:

1. **Intelligent Document Retrieval**
   - Automatic fetching of call documents from EU Portal API
   - 14 shared documents with 4,470+ chunks
   - Call-specific document mapping (Cluster 3, 4, 6 Work Programmes)
   - Full-text semantic search

2. **Conversational AI System**
   - Context-aware conversation management
   - Memory system (short-term Redis + long-term PostgreSQL)
   - AI intent detection and tool orchestration
   - Multi-turn conversations with context retention

3. **RAG Infrastructure**
   - Hybrid search (vector + keyword)
   - Grounded response generation with citations
   - Document chunking and embedding
   - Response formatting with source attribution

4. **Knowledge Base**
   - Horizon Europe eligibility rules
   - Budget requirements
   - Evaluation criteria
   - Application procedures
   - General Annexes, Programme Guide, Work Programmes

### 🎯 What You Need to Add
**Proposal Writing Capabilities:**
- Draft generation for proposal sections
- Compliance checking against call requirements
- Evaluation criteria matching
- Budget table creation
- Consortium composition assistance
- Quality assurance and improvement suggestions

---

## 🏗️ Proposed Architecture: Proposal Writing Assistant

### System Overview

```
┌─────────────────────────────────────────────────────────────┐
│              PROPOSAL WRITING ASSISTANT                      │
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │  Phase 1: DISCOVERY (Current System) ✅            │    │
│  │  - Find relevant calls                              │    │
│  │  - Understand requirements                          │    │
│  │  - Answer eligibility questions                     │    │
│  └────────────────────────────────────────────────────┘    │
│                           │                                  │
│                           ▼                                  │
│  ┌────────────────────────────────────────────────────┐    │
│  │  Phase 2: PLANNING (NEW!) 🆕                       │    │
│  │  - Extract call requirements                        │    │
│  │  - Generate proposal outline                        │    │
│  │  - Identify evaluation criteria                     │    │
│  │  - Suggest consortium structure                     │    │
│  └────────────────────────────────────────────────────┘    │
│                           │                                  │
│                           ▼                                  │
│  ┌────────────────────────────────────────────────────┐    │
│  │  Phase 3: WRITING (NEW!) 🆕                        │    │
│  │  - Generate section drafts                          │    │
│  │  - Match to evaluation criteria                     │    │
│  │  - Create budget tables                             │    │
│  │  - Draft work packages                              │    │
│  └────────────────────────────────────────────────────┘    │
│                           │                                  │
│                           ▼                                  │
│  ┌────────────────────────────────────────────────────┐    │
│  │  Phase 4: REFINEMENT (NEW!) 🆕                     │    │
│  │  - Compliance checking                              │    │
│  │  - Quality assessment                               │    │
│  │  - Improvement suggestions                          │    │
│  │  - Citation verification                            │    │
│  └────────────────────────────────────────────────────┘    │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔑 Core Components to Build

### 1. **Proposal Template Service** 🆕

**Purpose**: Generate structured templates based on call requirements

**Features**:
- Extract required sections from call documents
- Generate Part B templates (Excellence, Impact, Implementation)
- Create section-specific guidance
- Pre-populate evaluation criteria

**Data Model**:
```sql
CREATE TABLE proposal_templates (
    id SERIAL PRIMARY KEY,
    call_identifier VARCHAR(255) NOT NULL,
    template_type VARCHAR(50), -- 'RIA', 'IA', 'CSA', 'ERC', etc.
    template_structure JSONB, -- Section hierarchy
    evaluation_criteria JSONB, -- Criteria mapping
    page_limits JSONB, -- Page limits per section
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE proposal_sections (
    id SERIAL PRIMARY KEY,
    template_id INTEGER REFERENCES proposal_templates(id),
    section_name VARCHAR(255),
    section_order INTEGER,
    parent_section_id INTEGER,
    guidance_text TEXT,
    evaluation_criteria TEXT[],
    page_limit INTEGER,
    required_subsections JSONB
);
```

**Example API**:
```python
@router.post("/api/proposal/template/generate")
async def generate_proposal_template(call_id: str):
    """
    Generate a proposal template for a specific call
    
    Returns:
    - Section structure
    - Evaluation criteria mapping
    - Page limits
    - Required elements
    """
    # Extract call requirements from documents
    call_docs = await call_doc_service.get_call_documents(call_id)
    
    # Identify proposal type (RIA, IA, CSA)
    proposal_type = extract_proposal_type(call_docs)
    
    # Generate template
    template = {
        "sections": [
            {
                "name": "Excellence",
                "subsections": [
                    "Objectives and ambition",
                    "Methodology",
                    "Beyond state of the art"
                ],
                "evaluation_criteria": ["Scientific excellence", "Innovation"],
                "page_limit": 30
            },
            # ... more sections
        ]
    }
    
    return template
```

---

### 2. **Proposal Draft Generator** 🆕

**Purpose**: Generate initial drafts for proposal sections using AI

**Architecture**:
```python
class ProposalDraftGenerator:
    """
    Generate proposal section drafts based on:
    - Call requirements
    - User inputs
    - Past successful proposals (optional)
    """
    
    def __init__(self, ai_service, call_doc_service):
        self.ai_service = ai_service
        self.call_doc_service = call_doc_service
        
    async def generate_section_draft(
        self,
        call_id: str,
        section_name: str,
        user_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate a draft for a specific proposal section
        
        Args:
            call_id: The call identifier
            section_name: e.g., "Excellence.Objectives"
            user_context: {
                "project_idea": "...",
                "research_area": "...",
                "partners": [...],
                "budget": 2000000
            }
        
        Returns:
            {
                "draft_text": "...",
                "word_count": 500,
                "evaluation_criteria_addressed": [...],
                "suggestions": [...]
            }
        """
        
        # 1. Retrieve call-specific requirements
        requirements = await self._get_section_requirements(call_id, section_name)
        
        # 2. Retrieve relevant guidance from documents
        guidance_chunks = await self.call_doc_service.search_call_chunks(
            call_id,
            f"guidance for {section_name} section",
            limit=10
        )
        
        # 3. Build AI prompt
        prompt = f"""
        You are an expert Horizon Europe proposal writer.
        
        TASK: Write the "{section_name}" section for a proposal to call {call_id}.
        
        CALL REQUIREMENTS:
        {requirements}
        
        GUIDANCE FROM OFFICIAL DOCUMENTS:
        {guidance_chunks}
        
        USER'S PROJECT CONTEXT:
        {json.dumps(user_context, indent=2)}
        
        INSTRUCTIONS:
        1. Address all evaluation criteria for this section
        2. Use clear, compelling language
        3. Include specific, measurable objectives
        4. Stay within page limits
        5. Use EU terminology and style
        
        Generate a professional draft for this section.
        """
        
        # 4. Generate draft
        draft = await self.ai_service.generate_completion(prompt)
        
        # 5. Analyze draft quality
        analysis = await self._analyze_draft(draft, requirements)
        
        return {
            "draft_text": draft,
            "word_count": len(draft.split()),
            "evaluation_criteria_addressed": analysis["criteria_addressed"],
            "suggestions": analysis["improvement_suggestions"],
            "compliance_score": analysis["compliance_score"]
        }
```

**Key Features**:
- **Context-Aware Generation**: Uses call requirements + user inputs
- **Evaluation Criteria Matching**: Ensures all criteria are addressed
- **Style Consistency**: EU/Horizon Europe writing style
- **Quality Scoring**: Automatic assessment of draft quality

---

### 3. **Evaluation Criteria Matcher** 🆕

**Purpose**: Ensure proposal content matches evaluation criteria

**Implementation**:
```python
class EvaluationCriteriaMatcher:
    """
    Match proposal content to evaluation criteria
    """
    
    async def analyze_section(
        self,
        section_text: str,
        evaluation_criteria: List[str],
        call_id: str
    ) -> Dict[str, Any]:
        """
        Analyze how well a section addresses evaluation criteria
        
        Returns:
            {
                "overall_score": 0.85,
                "criteria_coverage": {
                    "Scientific excellence": {
                        "addressed": True,
                        "strength": 0.9,
                        "evidence": ["paragraph 2", "paragraph 5"],
                        "gaps": []
                    },
                    "Innovation": {
                        "addressed": True,
                        "strength": 0.7,
                        "evidence": ["paragraph 3"],
                        "gaps": ["Lacks comparison with state of the art"]
                    }
                },
                "recommendations": [...]
            }
        """
        
        # Retrieve evaluation criteria descriptions
        criteria_details = await self._get_criteria_details(call_id, evaluation_criteria)
        
        # AI-powered analysis
        prompt = f"""
        Analyze this proposal section against the evaluation criteria.
        
        SECTION TEXT:
        {section_text}
        
        EVALUATION CRITERIA:
        {json.dumps(criteria_details, indent=2)}
        
        For each criterion:
        1. Identify if it's addressed (yes/no)
        2. Rate strength (0-1)
        3. Cite evidence (which paragraphs)
        4. Identify gaps
        5. Suggest improvements
        
        Return JSON format.
        """
        
        analysis = await self.ai_service.generate_structured_output(
            prompt,
            output_schema=EvaluationAnalysisSchema
        )
        
        return analysis
```

**Benefits**:
- **Comprehensive Coverage**: Ensures nothing is missed
- **Evidence-Based**: Shows where criteria are addressed
- **Gap Identification**: Highlights weaknesses
- **Actionable Feedback**: Specific improvement suggestions

---

### 4. **Budget Assistant** 🆕

**Purpose**: Help create budget tables and justifications

**Features**:
```python
class BudgetAssistant:
    """
    Assist with budget planning and table generation
    """
    
    async def generate_budget_table(
        self,
        call_id: str,
        project_params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate budget breakdown table
        
        Args:
            project_params: {
                "duration_months": 36,
                "partners": [
                    {"name": "Uni X", "country": "DE", "type": "HES"},
                    {"name": "SME Y", "country": "FR", "type": "PRC"}
                ],
                "total_budget": 2000000
            }
        
        Returns:
            Budget table + justification guidance
        """
        
        # Get funding rules from call documents
        funding_rules = await self._get_funding_rules(call_id)
        
        # Calculate eligible costs per partner type
        budget_breakdown = self._calculate_budget(
            project_params,
            funding_rules
        )
        
        # Generate justification guidance
        justification = await self._generate_budget_justification(
            budget_breakdown,
            call_id
        )
        
        return {
            "budget_table": budget_breakdown,
            "total_eligible_costs": sum(...),
            "total_funding": sum(...),
            "justification_guidance": justification,
            "compliance_check": self._check_budget_compliance(...)
        }
    
    def _calculate_budget(self, params, rules):
        """
        Calculate budget based on funding rates
        
        For example:
        - HES (Universities): 100% funding
        - PRC (Companies): 70% funding for IA, 100% for RIA
        - Non-profit: 100% funding
        """
        budget = {
            "personnel": [],
            "subcontracting": [],
            "equipment": [],
            "other_direct_costs": [],
            "indirect_costs": []  # 25% flat rate
        }
        
        # Calculate per partner based on rules
        for partner in params["partners"]:
            funding_rate = rules.get_funding_rate(partner["type"])
            # ... calculations
        
        return budget
```

**Budget Categories Handled**:
- Personnel costs (person-months × rates)
- Subcontracting
- Equipment and consumables
- Other direct costs
- Indirect costs (25% flat rate)
- Travel and dissemination

---

### 5. **Compliance Checker** 🆕

**Purpose**: Verify proposal meets all mandatory requirements

**Implementation**:
```python
class ComplianceChecker:
    """
    Check proposal compliance with call requirements
    """
    
    async def run_compliance_check(
        self,
        call_id: str,
        proposal_content: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Run comprehensive compliance checks
        
        Returns:
            {
                "compliant": False,
                "critical_issues": [...],
                "warnings": [...],
                "recommendations": [...]
            }
        """
        
        checks = []
        
        # 1. Mandatory sections check
        checks.append(await self._check_mandatory_sections(call_id, proposal_content))
        
        # 2. Page limits check
        checks.append(await self._check_page_limits(call_id, proposal_content))
        
        # 3. Eligibility criteria check
        checks.append(await self._check_eligibility(call_id, proposal_content))
        
        # 4. Consortium composition check
        checks.append(await self._check_consortium(call_id, proposal_content))
        
        # 5. Budget compliance check
        checks.append(await self._check_budget_compliance(call_id, proposal_content))
        
        # 6. Evaluation criteria coverage check
        checks.append(await self._check_criteria_coverage(call_id, proposal_content))
        
        # Aggregate results
        return self._aggregate_compliance_results(checks)
```

**Compliance Checks**:
- ✅ Mandatory sections present
- ✅ Page limits respected
- ✅ Eligibility requirements met
- ✅ Consortium composition valid
- ✅ Budget rules followed
- ✅ Evaluation criteria addressed
- ✅ Required attachments listed
- ✅ Formatting requirements

---

### 6. **Quality Improvement Advisor** 🆕

**Purpose**: Provide AI-powered suggestions to improve proposal quality

**Features**:
```python
class QualityImprover:
    """
    Analyze and suggest improvements to proposal content
    """
    
    async def analyze_quality(
        self,
        section_text: str,
        section_type: str,
        call_id: str
    ) -> Dict[str, Any]:
        """
        Comprehensive quality analysis
        
        Returns:
            {
                "readability_score": 0.75,
                "clarity_issues": [...],
                "terminology_suggestions": [...],
                "structure_recommendations": [...],
                "impact_enhancement": [...]
            }
        """
        
        analyses = []
        
        # 1. Readability analysis
        analyses.append(self._analyze_readability(section_text))
        
        # 2. Terminology check (EU-specific terms)
        analyses.append(await self._check_terminology(section_text, call_id))
        
        # 3. Structure analysis
        analyses.append(self._analyze_structure(section_text, section_type))
        
        # 4. Impact and ambition analysis
        analyses.append(await self._analyze_impact(section_text))
        
        # 5. Innovation analysis
        analyses.append(await self._analyze_innovation(section_text))
        
        # 6. AI-powered improvement suggestions
        improvements = await self._generate_improvements(
            section_text,
            analyses,
            call_id
        )
        
        return {
            "overall_quality_score": self._calculate_overall_score(analyses),
            "detailed_analysis": analyses,
            "improvement_suggestions": improvements,
            "rewritten_suggestions": improvements.get("rewrites", [])
        }
    
    async def _generate_improvements(self, text, analyses, call_id):
        """
        Use AI to generate specific improvement suggestions
        """
        
        prompt = f"""
        You are a Horizon Europe proposal expert reviewer.
        
        SECTION TO IMPROVE:
        {text}
        
        ANALYSIS RESULTS:
        {json.dumps(analyses, indent=2)}
        
        Provide specific, actionable improvements:
        1. Identify weak or unclear statements
        2. Suggest stronger, more compelling alternatives
        3. Recommend additions to strengthen impact
        4. Propose restructuring if needed
        5. Ensure EU terminology is used correctly
        
        For each suggestion, explain WHY it would improve the proposal.
        """
        
        suggestions = await self.ai_service.generate_structured_output(
            prompt,
            output_schema=ImprovementSuggestionsSchema
        )
        
        return suggestions
```

**Quality Dimensions**:
- Clarity and readability
- Scientific rigor
- Innovation level
- Impact and ambition
- EU terminology usage
- Structure and flow
- Evidence and citations
- Measurability of objectives

---

## 📊 Database Schema Extensions

### New Tables for Proposal Management

```sql
-- Proposals table
CREATE TABLE proposals (
    id SERIAL PRIMARY KEY,
    call_identifier VARCHAR(255) NOT NULL,
    conversation_id INTEGER REFERENCES conversations(id),
    proposal_title VARCHAR(500),
    proposal_acronym VARCHAR(50),
    proposal_type VARCHAR(50), -- 'RIA', 'IA', 'CSA', etc.
    status VARCHAR(50) DEFAULT 'draft', -- 'draft', 'in_review', 'submitted'
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    user_id INTEGER,
    metadata JSONB
);

-- Proposal sections with versioning
CREATE TABLE proposal_sections (
    id SERIAL PRIMARY KEY,
    proposal_id INTEGER REFERENCES proposals(id),
    section_name VARCHAR(255),
    section_content TEXT,
    version INTEGER DEFAULT 1,
    word_count INTEGER,
    compliance_score DECIMAL(3,2),
    quality_score DECIMAL(3,2),
    created_at TIMESTAMP DEFAULT NOW(),
    created_by VARCHAR(100),
    parent_version_id INTEGER REFERENCES proposal_sections(id)
);

-- Evaluation criteria tracking
CREATE TABLE section_criteria_mapping (
    id SERIAL PRIMARY KEY,
    section_id INTEGER REFERENCES proposal_sections(id),
    criterion_name VARCHAR(255),
    addressed BOOLEAN DEFAULT FALSE,
    strength_score DECIMAL(3,2),
    evidence TEXT[], -- References to paragraphs
    gaps TEXT[],
    last_checked TIMESTAMP DEFAULT NOW()
);

-- Budget tables
CREATE TABLE proposal_budgets (
    id SERIAL PRIMARY KEY,
    proposal_id INTEGER REFERENCES proposals(id),
    partner_name VARCHAR(255),
    partner_country VARCHAR(3),
    partner_type VARCHAR(50), -- 'HES', 'REC', 'PRC', 'OTH'
    personnel_costs DECIMAL(12,2),
    subcontracting_costs DECIMAL(12,2),
    equipment_costs DECIMAL(12,2),
    other_costs DECIMAL(12,2),
    indirect_costs DECIMAL(12,2),
    total_eligible_costs DECIMAL(12,2),
    funding_rate DECIMAL(3,2),
    requested_funding DECIMAL(12,2)
);

-- Compliance tracking
CREATE TABLE compliance_checks (
    id SERIAL PRIMARY KEY,
    proposal_id INTEGER REFERENCES proposals(id),
    check_type VARCHAR(100),
    check_result VARCHAR(20), -- 'pass', 'fail', 'warning'
    details JSONB,
    checked_at TIMESTAMP DEFAULT NOW()
);

-- Quality improvement suggestions
CREATE TABLE improvement_suggestions (
    id SERIAL PRIMARY KEY,
    section_id INTEGER REFERENCES proposal_sections(id),
    suggestion_type VARCHAR(100),
    suggestion_text TEXT,
    priority VARCHAR(20), -- 'critical', 'high', 'medium', 'low'
    status VARCHAR(20) DEFAULT 'pending', -- 'pending', 'applied', 'dismissed'
    created_at TIMESTAMP DEFAULT NOW()
);

-- Successful proposal examples (optional - for learning)
CREATE TABLE proposal_examples (
    id SERIAL PRIMARY KEY,
    call_identifier VARCHAR(255),
    section_name VARCHAR(255),
    example_text TEXT,
    evaluation_score DECIMAL(3,1), -- e.g., 14.5 out of 15
    success_factors TEXT[],
    is_public BOOLEAN DEFAULT FALSE,
    added_at TIMESTAMP DEFAULT NOW()
);
```

---

## 🔄 Integration with Current System

### Conversation Flow Enhancement

```python
# Updated ConversationManager with proposal writing mode

class ConversationManager:
    
    def __init__(self):
        # ... existing initialization ...
        
        # NEW: Proposal writing services
        self.proposal_template_service = ProposalTemplateService(self.db_pool)
        self.draft_generator = ProposalDraftGenerator(
            ai_service=self.ai_intent_service,
            call_doc_service=self.call_doc_service
        )
        self.criteria_matcher = EvaluationCriteriaMatcher(self.ai_intent_service)
        self.budget_assistant = BudgetAssistant(self.db_pool)
        self.compliance_checker = ComplianceChecker(
            self.call_doc_service,
            self.db_pool
        )
        self.quality_improver = QualityImprover(self.ai_intent_service)
    
    async def process_message(self, conversation_id: int, user_message: str):
        """
        Enhanced to handle proposal writing requests
        """
        
        # Detect mode: discovery vs. writing
        mode = await self._detect_conversation_mode(conversation_id, user_message)
        
        if mode == "proposal_writing":
            return await self._handle_proposal_writing(conversation_id, user_message)
        else:
            # Existing discovery flow
            return await self._handle_discovery(conversation_id, user_message)
    
    async def _detect_conversation_mode(self, conversation_id: int, message: str):
        """
        Detect if user wants help with proposal writing
        """
        
        writing_indicators = [
            "write proposal",
            "draft section",
            "help me write",
            "generate proposal",
            "create budget",
            "check compliance",
            "improve my draft"
        ]
        
        if any(indicator in message.lower() for indicator in writing_indicators):
            return "proposal_writing"
        
        # Check conversation context
        context = await self.memory_service.get_conversation_context(conversation_id)
        if context.get("mode") == "proposal_writing":
            return "proposal_writing"
        
        return "discovery"
    
    async def _handle_proposal_writing(
        self,
        conversation_id: int,
        user_message: str
    ):
        """
        Handle proposal writing requests
        """
        
        # Analyze intent
        intent = await self._analyze_writing_intent(user_message)
        
        if intent["action"] == "generate_template":
            call_id = intent["call_id"]
            template = await self.proposal_template_service.generate_template(call_id)
            return self._format_template_response(template)
        
        elif intent["action"] == "draft_section":
            draft = await self.draft_generator.generate_section_draft(
                call_id=intent["call_id"],
                section_name=intent["section_name"],
                user_context=intent["user_context"]
            )
            return self._format_draft_response(draft)
        
        elif intent["action"] == "check_compliance":
            compliance = await self.compliance_checker.run_compliance_check(
                call_id=intent["call_id"],
                proposal_content=intent["proposal_content"]
            )
            return self._format_compliance_response(compliance)
        
        elif intent["action"] == "improve_quality":
            improvements = await self.quality_improver.analyze_quality(
                section_text=intent["section_text"],
                section_type=intent["section_type"],
                call_id=intent["call_id"]
            )
            return self._format_improvement_response(improvements)
        
        elif intent["action"] == "create_budget":
            budget = await self.budget_assistant.generate_budget_table(
                call_id=intent["call_id"],
                project_params=intent["project_params"]
            )
            return self._format_budget_response(budget)
        
        # Default: conversational assistance
        return await self._provide_writing_assistance(user_message, conversation_id)
```

---

## 🚀 Implementation Roadmap

### Phase 1: Foundation (Weeks 1-2) 🔧

**Goal**: Set up basic proposal writing infrastructure

**Tasks**:
1. ✅ Create database schema extensions
   ```bash
   psql $DATABASE_URL < migration/005_proposal_writing_schema.sql
   ```

2. ✅ Build ProposalTemplateService
   - Extract section requirements from call documents
   - Generate basic templates
   - Map evaluation criteria to sections

3. ✅ Create simple draft generator
   - Start with one section type (e.g., "Objectives")
   - Use existing AI services
   - Test with one call

**Deliverables**:
- Database tables created
- Template generation working for 1 call
- Basic draft generation for 1 section type

**Success Criteria**:
- Can generate proposal outline for any Cluster 3/4/6 call
- Can generate basic draft for "Objectives" section
- Draft addresses at least 70% of evaluation criteria

---

### Phase 2: Core Writing Features (Weeks 3-5) ✍️

**Goal**: Build comprehensive draft generation

**Tasks**:
1. ✅ Expand DraftGenerator to all section types
   - Excellence sections
   - Impact sections
   - Implementation sections

2. ✅ Build EvaluationCriteriaMatcher
   - Analyze section coverage
   - Identify gaps
   - Suggest improvements

3. ✅ Create BudgetAssistant
   - Generate budget tables
   - Calculate funding rates
   - Create justifications

4. ✅ Integrate with conversation flow
   - Update ConversationManager
   - Add writing mode detection
   - Create new API endpoints

**API Endpoints**:
```python
# New routes
POST /api/proposal/template/{call_id}
POST /api/proposal/draft/section
POST /api/proposal/budget/generate
GET  /api/proposal/{proposal_id}/sections
PUT  /api/proposal/{proposal_id}/section/{section_id}
```

**Success Criteria**:
- Can generate drafts for all major sections
- Budget tables calculate correctly
- Evaluation criteria matching >80% accurate
- Users can iterate on drafts

---

### Phase 3: Quality & Compliance (Weeks 6-7) ✅

**Goal**: Ensure proposal quality and compliance

**Tasks**:
1. ✅ Build ComplianceChecker
   - Mandatory sections check
   - Page limits validation
   - Eligibility verification
   - Consortium composition check

2. ✅ Create QualityImprover
   - Readability analysis
   - Terminology checking
   - Structure recommendations
   - AI-powered improvements

3. ✅ Add versioning system
   - Track section versions
   - Allow rollback
   - Compare versions

**Success Criteria**:
- Compliance checker identifies 100% of mandatory issues
- Quality suggestions improve draft scores by >20%
- Users can track changes across versions

---

### Phase 4: Advanced Features (Weeks 8-10) 🚀

**Goal**: Add advanced capabilities

**Tasks**:
1. ✅ **Consortium Builder**
   - Suggest partner roles
   - Check eligibility per partner
   - Calculate budget distribution
   
2. ✅ **Work Package Planner**
   - Generate WP structure
   - Create Gantt charts
   - Calculate person-months

3. ✅ **Past Proposal Learning** (Optional)
   - Store successful examples
   - Learn from patterns
   - Suggest proven approaches

4. ✅ **Export & Integration**
   - Export to Word/PDF
   - Generate submission-ready format
   - Integration with Funding & Tenders Portal

**Success Criteria**:
- Can suggest consortium composition
- Work package planning is automated
- Export produces submission-ready documents

---

### Phase 5: Testing & Refinement (Weeks 11-12) 🧪

**Goal**: Polish and optimize

**Tasks**:
1. User testing with real proposals
2. Performance optimization
3. UI/UX improvements
4. Documentation

**Success Criteria**:
- User satisfaction >4.5/5
- Draft quality matches professional consultants
- End-to-end proposal creation <5 hours (vs. weeks)

---

## 💻 Example User Flows

### Flow 1: Complete Proposal Generation

```
User: "I want to write a proposal for HORIZON-CL3-2025-02-CS-ECCC-01"

System: "Great! I'll help you write your proposal. First, let me understand 
         your project. What's your main research idea?"

User: "We want to develop an AI-powered early warning system for 
       cybersecurity threats in critical infrastructure."

System: "Excellent! I've analyzed the call requirements. This is a 
         Research & Innovation Action (RIA) with these key requirements:
         
         📋 Evaluation Criteria:
         - Excellence: Scientific innovation, methodology
         - Impact: Expected outcomes, dissemination
         - Implementation: Work plan, consortium, resources
         
         🎯 Specific Requirements:
         - Consortium: Min 3 entities from 3 different EU countries
         - Budget: €2-4M
         - Duration: 24-36 months
         - Page limit: 45 pages (Part B)
         
         Would you like me to:
         1. Generate a proposal template
         2. Help with consortium composition
         3. Start drafting sections
         4. Create a budget outline"

User: "Generate the template first"

System: [Generates structured template with all sections]

User: "Now draft the Objectives section"

System: "I'll draft the Objectives section. To make it specific to your 
         project, I need a few details:
         - What are your 3-5 main objectives?
         - What's the main problem you're solving?
         - Who are the end users?"

User: [Provides details]

System: [Generates draft]
        
        "Here's your draft for the Objectives section:
        
        1.1 Objectives and Ambition
        
        The CYBER-SHIELD project aims to develop an AI-powered early 
        warning system for cybersecurity threats in critical 
        infrastructure...
        
        [Full draft - 800 words]
        
        ✅ Quality Analysis:
        - Evaluation criteria coverage: 90%
        - Clarity score: 8.5/10
        - Innovation level: High
        
        💡 Suggestions:
        1. Add specific, measurable KPIs
        2. Strengthen the beyond-state-of-the-art aspect
        3. Include more EU-specific context
        
        Would you like to:
        - Refine this draft
        - Move to the next section
        - Check compliance"
```

### Flow 2: Budget Creation

```
User: "Help me create the budget table"

System: "I'll create your budget table. First, tell me about your consortium:
         - How many partners?
         - Partner types (university, company, etc.)?
         - Country for each partner?"

User: "3 partners: University (Germany), SME (France), Research org (Spain)"

System: [Generates budget table]
        
        "Here's your budget breakdown:
        
        Partner 1: Technical University Munich (Germany)
        - Type: Higher Education (HES)
        - Funding rate: 100%
        - Personnel: €500,000
        - Equipment: €200,000
        - Other: €50,000
        - Indirect (25%): €187,500
        - Total eligible: €937,500
        - EU contribution: €937,500
        
        [Similar for other partners]
        
        TOTAL PROJECT:
        - Total eligible costs: €2,500,000
        - EU contribution: €2,300,000 (92%)
        
        ✅ Compliance Check:
        - Budget within call limits: ✓
        - Funding rates correct: ✓
        - Indirect costs at 25%: ✓
        
        💡 Recommendations:
        1. Consider adding dissemination budget
        2. Equipment costs are high - justify in proposal
        3. Balance person-months across partners"
```

### Flow 3: Compliance & Quality Check

```
User: "Check if my proposal is compliant"

System: [Runs compliance checks]
        
        "Compliance Analysis Results:
        
        ✅ PASSED:
        - All mandatory sections present
        - Consortium composition valid (3 countries)
        - Budget within limits
        - Evaluation criteria addressed
        
        ⚠️ WARNINGS:
        - Excellence section: 31 pages (limit: 30)
        - Work package 3: No clear deliverables
        - Budget justification: Missing for equipment costs
        
        ❌ CRITICAL ISSUES:
        - Ethical issues section: Not completed
        - Gender dimension: Not addressed
        
        🔧 Required Actions:
        1. MUST: Complete ethical issues assessment
        2. MUST: Add gender dimension analysis
        3. SHOULD: Reduce Excellence section by 1 page
        4. SHOULD: Define WP3 deliverables
        
        Priority: Fix critical issues before submission!"
```

---

## 🛠️ Technical Implementation Details

### AI Prompt Engineering for Proposal Writing

**Key Principles**:
1. **Structured Prompts**: Always include context, requirements, examples
2. **Iterative Generation**: Generate → Analyze → Improve
3. **Evaluation-Focused**: Every draft must address criteria
4. **EU-Specific**: Use Horizon Europe terminology and style

**Example Prompt Template**:
```python
PROPOSAL_SECTION_PROMPT = """
You are an expert Horizon Europe proposal writer with 15+ years of experience 
writing successful RIA, IA, and CSA proposals.

CONTEXT:
- Call: {call_id}
- Section: {section_name}
- Evaluation Criteria: {criteria}
- Page Limit: {page_limit}

OFFICIAL GUIDANCE FROM CALL DOCUMENTS:
{call_guidance}

USER'S PROJECT:
{user_context}

TASK:
Write a compelling {section_name} section that:

1. DIRECTLY ADDRESSES these evaluation criteria:
{criteria_list}

2. FOLLOWS this structure:
{required_structure}

3. USES these EU-specific elements:
- TRL levels where relevant
- References to EU policies/strategies
- Alignment with EU priorities
- Clear methodology
- Measurable objectives

4. WRITING STYLE:
- Clear and concise
- Persuasive but factual
- Technical but accessible
- Active voice preferred
- Future-focused language

5. MUST INCLUDE:
- Specific, measurable objectives
- Beyond state-of-the-art analysis
- Clear innovation aspects
- EU added value

Generate the section now. After generation, self-critique and ensure all 
evaluation criteria are explicitly addressed.

OUTPUT FORMAT:
[Section text]

---
Self-Assessment:
- Criteria addressed: [list]
- Strengths: [list]
- Potential improvements: [list]
"""
```

### Caching Strategy for Performance

```python
class ProposalWritingCache:
    """
    Smart caching for proposal writing operations
    """
    
    def __init__(self, redis_client):
        self.redis = redis_client
        self.ttl = {
            "call_requirements": 3600 * 24,  # 24 hours
            "templates": 3600 * 12,           # 12 hours
            "drafts": 3600 * 2,               # 2 hours
            "compliance_checks": 1800          # 30 minutes
        }
    
    async def get_or_generate_template(self, call_id: str):
        """Cache templates per call"""
        cache_key = f"template:{call_id}"
        
        cached = await self.redis.get(cache_key)
        if cached:
            return json.loads(cached)
        
        # Generate fresh
        template = await self.template_service.generate(call_id)
        
        # Cache
        await self.redis.setex(
            cache_key,
            self.ttl["templates"],
            json.dumps(template)
        )
        
        return template
```

---

## 📈 Success Metrics

### Quantitative Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Draft Quality Score** | >8.0/10 | AI evaluation + user rating |
| **Evaluation Criteria Coverage** | >90% | Automated analysis |
| **Compliance Pass Rate** | 100% | Automated checks |
| **Time to First Draft** | <10 min | System logs |
| **Time Savings vs. Manual** | >70% | User surveys (weeks → hours) |
| **User Satisfaction** | >4.5/5 | Post-use surveys |
| **Proposal Success Rate** | Track | Follow-up on submissions |

### Qualitative Metrics

| Aspect | Success Indicator |
|--------|------------------|
| **Usability** | Non-experts can create quality proposals |
| **Quality** | Drafts comparable to professional consultants |
| **Compliance** | Zero mandatory requirement violations |
| **Learning** | System improves with usage |
| **Trust** | Users confident in AI-generated content |

---

## ⚠️ Risks & Mitigation

### Risk 1: AI Hallucination in Critical Content
**Risk**: AI generates incorrect information about requirements
**Mitigation**:
- Always cite source documents
- Implement fact-checking against call documents
- Flag uncertain information
- Allow user verification before final use

### Risk 2: Over-Reliance on AI
**Risk**: Users submit AI drafts without proper review
**Mitigation**:
- Always include "This is a draft - review required" disclaimer
- Require manual confirmation for critical sections
- Provide quality scores to indicate confidence
- Encourage iterative improvement

### Risk 3: Template Rigidity
**Risk**: Templates too rigid for diverse research areas
**Mitigation**:
- Make templates highly customizable
- Provide examples from different domains
- Allow users to modify structure
- Support free-form writing with guidance

### Risk 4: Compliance Rule Changes
**Risk**: EU requirements change, system becomes outdated
**Mitigation**:
- Monitor EU portal for updates
- Version templates by year
- Regular document refresh pipeline
- Clear version indicators

### Risk 5: Data Privacy
**Risk**: Sensitive project information in AI prompts
**Mitigation**:
- Use local LLMs for sensitive content (optional)
- Clear data retention policies
- Anonymize examples in training data
- User controls over data sharing

---

## 🔧 Quick Start Implementation

### Step 1: Add Database Schema (30 mins)

```bash
# Create migration file
cat > migration/005_proposal_writing_schema.sql << 'EOF'
-- [Insert schema from earlier section]
EOF

# Apply migration
psql $DATABASE_URL < migration/005_proposal_writing_schema.sql
```

### Step 2: Create Core Services (1 day)

```bash
# Create directory structure
mkdir -p app/services/proposal_writing

# Create core files
touch app/services/proposal_writing/__init__.py
touch app/services/proposal_writing/template_service.py
touch app/services/proposal_writing/draft_generator.py
touch app/services/proposal_writing/criteria_matcher.py
```

### Step 3: Build Simple Prototype (2 days)

Focus on ONE flow:
1. User provides call ID + project idea
2. System generates template
3. System drafts "Objectives" section
4. System checks evaluation criteria coverage

### Step 4: Test with Real Call (1 day)

Use your existing test call: `HORIZON-CL3-2025-02-CS-ECCC-01`

```python
# test_proposal_writing.py
async def test_proposal_generation():
    call_id = "HORIZON-CL3-2025-02-CS-ECCC-01"
    project_idea = "AI-powered early warning system for cybersecurity"
    
    # Generate template
    template = await template_service.generate_template(call_id)
    print(f"✅ Template generated with {len(template['sections'])} sections")
    
    # Generate objectives draft
    draft = await draft_generator.generate_section_draft(
        call_id=call_id,
        section_name="Excellence.Objectives",
        user_context={"project_idea": project_idea}
    )
    print(f"✅ Draft generated: {draft['word_count']} words")
    print(f"✅ Criteria coverage: {len(draft['evaluation_criteria_addressed'])}")
    
    # Check compliance
    compliance = await criteria_matcher.analyze_section(
        section_text=draft['draft_text'],
        evaluation_criteria=["Scientific excellence", "Innovation"],
        call_id=call_id
    )
    print(f"✅ Compliance score: {compliance['overall_score']}")
```

---

## 🎓 Learning from Successful Proposals (Optional Enhancement)

### Concept: Learn from Past Successes

**Idea**: Build a library of successful proposal excerpts to learn patterns

**Implementation**:
```python
class ProposalLearningSystem:
    """
    Analyze successful proposals to learn patterns
    """
    
    async def learn_from_example(
        self,
        call_id: str,
        section_name: str,
        example_text: str,
        evaluation_score: float
    ):
        """
        Store successful example for learning
        """
        
        # Extract patterns
        patterns = await self._extract_success_patterns(example_text, evaluation_score)
        
        # Store in database
        await self.db.execute("""
            INSERT INTO proposal_examples 
            (call_identifier, section_name, example_text, evaluation_score, success_factors)
            VALUES ($1, $2, $3, $4, $5)
        """, call_id, section_name, example_text, evaluation_score, patterns)
    
    async def get_relevant_examples(
        self,
        call_id: str,
        section_name: str,
        user_context: Dict
    ) -> List[Dict]:
        """
        Retrieve relevant examples to guide draft generation
        """
        
        # Find similar calls and sections
        examples = await self.db.fetch("""
            SELECT example_text, evaluation_score, success_factors
            FROM proposal_examples
            WHERE call_identifier LIKE $1 
            AND section_name = $2
            AND evaluation_score > 13.0
            ORDER BY evaluation_score DESC
            LIMIT 3
        """, f"{call_id[:12]}%", section_name)
        
        return examples
    
    async def enhance_draft_with_patterns(
        self,
        draft: str,
        examples: List[Dict]
    ) -> str:
        """
        Use successful patterns to improve draft
        """
        
        prompt = f"""
        You have a proposal draft and examples of successful sections.
        
        CURRENT DRAFT:
        {draft}
        
        SUCCESSFUL EXAMPLES (high-scoring):
        {self._format_examples(examples)}
        
        Improve the draft by:
        1. Adopting successful patterns from examples
        2. Maintaining the draft's unique content
        3. Enhancing structure and clarity
        4. Incorporating proven phrases and approaches
        
        Generate improved version.
        """
        
        improved = await self.ai_service.generate(prompt)
        return improved
```

**Benefits**:
- Learn what evaluators value
- Identify winning patterns
- Improve over time
- Domain-specific optimization

**Privacy Considerations**:
- Only use publicly available proposals
- Anonymize sensitive information
- Get permission for non-public examples
- Focus on structure/patterns, not copying content

---

## 🔌 API Specification

### Complete API Endpoints

```python
# Proposal Template APIs
POST   /api/proposal/template/{call_id}
GET    /api/proposal/template/{call_id}

# Proposal Management
POST   /api/proposal/create
GET    /api/proposal/{proposal_id}
PUT    /api/proposal/{proposal_id}
DELETE /api/proposal/{proposal_id}
GET    /api/proposal/list

# Section Management
POST   /api/proposal/{proposal_id}/section
GET    /api/proposal/{proposal_id}/section/{section_id}
PUT    /api/proposal/{proposal_id}/section/{section_id}
DELETE /api/proposal/{proposal_id}/section/{section_id}

# Draft Generation
POST   /api/proposal/draft/generate
POST   /api/proposal/draft/improve

# Evaluation & Compliance
POST   /api/proposal/evaluate/criteria
POST   /api/proposal/check/compliance
POST   /api/proposal/quality/analyze

# Budget
POST   /api/proposal/budget/generate
GET    /api/proposal/{proposal_id}/budget
PUT    /api/proposal/{proposal_id}/budget

# Export
GET    /api/proposal/{proposal_id}/export/docx
GET    /api/proposal/{proposal_id}/export/pdf
GET    /api/proposal/{proposal_id}/export/submission

# Conversational Interface (uses existing endpoint)
POST   /api/v2/conversation/{conversation_id}/message
# Add proposal_mode flag or detect automatically
```

### Example Request/Response

**Request**: Generate Section Draft
```json
POST /api/proposal/draft/generate

{
  "call_id": "HORIZON-CL3-2025-02-CS-ECCC-01",
  "section_name": "Excellence.Objectives",
  "user_context": {
    "project_idea": "AI-powered early warning system for cybersecurity",
    "research_area": "Cybersecurity, AI, Critical Infrastructure",
    "main_objectives": [
      "Develop AI models for threat detection",
      "Create early warning dashboard",
      "Validate in real infrastructure"
    ],
    "partners": [
      {"name": "TU Munich", "expertise": "AI"},
      {"name": "Thales", "expertise": "Cybersecurity"},
      {"name": "CERN", "expertise": "Infrastructure"}
    ],
    "budget": 3000000,
    "duration_months": 36
  }
}
```

**Response**:
```json
{
  "draft": {
    "section_id": "12345",
    "section_name": "Excellence.Objectives",
    "content": "1.1 Objectives and Ambition\n\nThe CYBER-SHIELD project addresses the critical challenge of cybersecurity threats...\n\n[Full draft text - ~1000 words]",
    "word_count": 1043,
    "estimated_pages": 3.2,
    "version": 1,
    "created_at": "2025-10-10T14:30:00Z"
  },
  "evaluation": {
    "overall_score": 8.5,
    "criteria_addressed": [
      {
        "criterion": "Scientific excellence",
        "addressed": true,
        "strength": 0.9,
        "evidence": ["Paragraph 2 describes novel AI approach", "Paragraph 4 shows beyond state-of-the-art"],
        "gaps": []
      },
      {
        "criterion": "Clarity of objectives",
        "addressed": true,
        "strength": 0.85,
        "evidence": ["Three SMART objectives listed", "Success criteria defined"],
        "gaps": ["Could add more measurable KPIs"]
      }
    ]
  },
  "suggestions": [
    {
      "type": "improvement",
      "priority": "medium",
      "text": "Consider adding specific TRL levels for each objective",
      "section_ref": "Paragraph 3"
    },
    {
      "type": "compliance",
      "priority": "low",
      "text": "Ensure alignment with EU Cybersecurity Strategy is explicit",
      "section_ref": "Introduction"
    }
  ],
  "next_steps": [
    "Review and refine the draft",
    "Add stakeholder analysis",
    "Proceed to Methodology section"
  ]
}
```

---

## 🎯 Conclusion & Next Steps

### What You'll Achieve

By implementing this proposal writing assistant, your system will:

1. **Transform from Discovery to Creation**
   - From "find calls" → "write proposals"
   - From "understand requirements" → "meet requirements automatically"
   - From "hours of research" → "minutes to first draft"

2. **Deliver Massive Time Savings**
   - Current: 2-4 weeks to write a proposal
   - With AI: 2-3 days with AI assistance
   - **80-90% time reduction**

3. **Improve Proposal Quality**
   - 100% compliance with mandatory requirements
   - >90% evaluation criteria coverage
   - Professional-grade drafts from day 1

4. **Scale Impact**
   - Help hundreds of researchers
   - Increase proposal success rates
   - Democratize access to EU funding

### Recommended Next Steps

1. **Week 1**: 
   - Review this research document
   - Decide on Phase 1 scope
   - Set up database schema

2. **Week 2-3**:
   - Build ProposalTemplateService
   - Create basic DraftGenerator
   - Test with one call

3. **Week 4-5**:
   - Expand to all sections
   - Add compliance checking
   - Integrate with existing system

4. **Week 6+**:
   - User testing
   - Refinement
   - Advanced features

### Key Success Factors

✅ **Start Small**: Begin with ONE section type, perfect it, then expand
✅ **Use Existing Infrastructure**: Leverage your RAG, memory, and AI services
✅ **Focus on Quality**: Better to do one thing excellently than many things poorly
✅ **Iterate with Users**: Get feedback early and often
✅ **Maintain Compliance**: Never compromise on EU requirements

---

## 📚 Additional Resources

### Technical Resources
- [Horizon Europe Online Manual](https://ec.europa.eu/info/funding-tenders/opportunities/docs/2021-2027/common/guidance/om_en.pdf)
- [Proposal Template (Part B)](https://ec.europa.eu/info/funding-tenders/opportunities/docs/2021-2027/common/guidance/document-templates_he_en.zip)
- [Evaluation Criteria Guidelines](https://ec.europa.eu/info/funding-tenders/opportunities/docs/2021-2027/horizon/guidance/evaluation-criteria_he_en.pdf)

### AI/LLM Resources
- OpenAI GPT-4 for high-quality generation
- Claude for longer context (100K tokens)
- Gemini Pro for cost-effective processing
- Local LLMs (Llama 3) for privacy-sensitive content

### Similar Systems (Inspiration)
- Arphie (RFP response automation)
- Qvidian (Proposal management)
- Grant.ai (Grant writing assistance)
- Your system can be specialized for Horizon Europe!

---

## 💝 Final Thoughts

Your current system is already impressive - you've built a comprehensive Horizon Europe discovery and research tool. Adding proposal writing capabilities is a natural and powerful extension that will:

- **10x the value** you provide to users
- **Transform weeks of work** into hours
- **Make EU funding accessible** to more researchers
- **Increase success rates** with better proposals

The architecture outlined here leverages everything you've already built:
- Your document retrieval system
- Your RAG infrastructure
- Your conversational AI
- Your compliance knowledge

You're in a perfect position to build the **world's best Horizon Europe proposal writing assistant**. 

Start small, iterate fast, and watch your users succeed! 🚀

---

**Document Version**: 1.0  
**Date**: October 10, 2025  
**Author**: AI Research Assistant  
**Status**: Research Complete - Ready for Implementation


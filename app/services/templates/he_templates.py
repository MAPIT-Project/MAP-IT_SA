"""
Production-ready Horizon Europe proposal templates.

Extracted from official EU Funding & Tenders Portal application forms:
- af_he-ria-ia_en.pdf (RIA/IA full proposal)
- af_he-csa_en.pdf (CSA full proposal)
- af_he-erc-stg_en.pdf (ERC Starting Grant proposal)
- af_he-msca-pf_en.pdf (MSCA Postdoctoral Fellowships)
- af_he-msca-dn_en.pdf (MSCA Doctoral Networks)
- af_he-eic-pathfinder-open_en.pdf (EIC Pathfinder Open)
- af_he-eic-transition_en.pdf (EIC Transition)
- af_he-eic-accelerator_en.pdf (EIC Accelerator)

Each section includes:
- name: Official section title with numbering
- instructions: What the EU template asks you to write
- evaluation_criteria: What evaluators score this section on
- page_guidance: Approximate page allocation
- tips: Expert writing advice for high scores
- keywords: Keywords used by the AI agent to detect when this section is active
"""

# =============================================================================
# Official Horizon Europe RIA/IA Template (Part B - Full Proposal)
# =============================================================================
RIA_IA_TEMPLATE: dict[str, dict] = {
    "excellence.objectives": {
        "name": "1.1 Objectives and ambition",
        "instructions": (
            "Describe the overall and specific objectives for the project, which should be clear, "
            "measurable, realistic and achievable within the duration of the project. "
            "Objectives should be consistent with the expected exploitation and impact of the project. "
            "\n\n"
            "Show the extent to which the proposed work is ambitious, novel and goes beyond the "
            "state of the art (e.g. ground-breaking objectives, novel concepts and approaches, "
            "new products, services or business and organisational models). "
            "\n\n"
            "Describe the innovation potential (e.g. ground-breaking objectives, novel concepts "
            "and approaches, new products, services or business and organisational models) which "
            "the project represents. Where relevant, refer to products and services already available "
            "on the market. Please refer to the results of any patent search carried out."
        ),
        "evaluation_criteria": (
            "Evaluated under 'Excellence' criterion. Evaluators assess: "
            "clarity and pertinence of objectives; extent of ambition and novelty; "
            "soundness of the concept; credibility of the proposed approach."
        ),
        "page_guidance": "~5-7 pages (including state-of-the-art)",
        "tips": [
            "Start with 1-2 clear overall objectives, then list 3-6 specific measurable objectives (SO1, SO2, etc.)",
            "Each specific objective should be SMART: Specific, Measurable, Achievable, Relevant, Time-bound",
            "Include a clear 'Beyond State of the Art' subsection showing what's novel",
            "Reference TRL levels to position your innovation maturity",
            "Use a table or diagram to show how objectives map to work packages",
        ],
        "keywords": [
            "objectives",
            "ambition",
            "1.1",
            "state of the art",
            "beyond",
            "novelty",
            "innovation potential",
            "patent search",
        ],
    },
    "excellence.methodology": {
        "name": "1.2 Methodology",
        "instructions": (
            "Describe and explain the overall methodology, including the concepts, models and "
            "assumptions that underpin your work. Explain how this will enable you to deliver "
            "your project's objectives. Refer to any important challenges you may have identified "
            "in the chosen methodology and how you intend to overcome them. "
            "\n\n"
            "Where relevant, describe how the gender dimension (i.e. sex and/or gender analysis) "
            "is taken into account in the project's content. If you do not consider such a "
            "dimension to be relevant, please provide a justification. "
            "\n\n"
            "Describe how appropriate open science practices are implemented as an integral part "
            "of the proposed methodology. Show how the choice of practices and their implementation "
            "are adapted to the nature of your work, in a way that will increase the chances of "
            "the project delivering on its objectives. If you believe that none of these practices "
            "are appropriate for your project, please provide a justification here. "
            "\n\n"
            "Open science practices include: early and open sharing of research (for example through "
            "preregistration, registered reports, pre-prints, or crowd-sourcing); research output "
            "management; measures to ensure reproducibility of research outputs; providing open "
            "access to research outputs (such as publications, data, software, models, algorithms, "
            "and workflows); participating in open peer-review."
        ),
        "evaluation_criteria": (
            "Evaluated under 'Excellence' criterion. Evaluators assess: "
            "quality and credibility of the methodology; appropriateness of open science practices; "
            "integration of gender dimension where relevant."
        ),
        "page_guidance": "~5-8 pages",
        "tips": [
            "Include a methodology diagram or flowchart showing the research approach",
            "Explicitly address open science: data management, open access publications, FAIR data",
            "Address gender dimension even if brief — explain why it is or isn't relevant",
            "Show interdisciplinary integration if applicable",
            "Mention key standards, protocols, or frameworks you will follow",
        ],
        "keywords": [
            "methodology",
            "1.2",
            "open science",
            "gender dimension",
            "concepts",
            "models",
            "assumptions",
            "sex and/or gender analysis",
            "reproducibility",
            "peer-review",
        ],
    },
    "impact.pathways": {
        "name": "2.1 Project's pathways towards impact",
        "instructions": (
            "Provide a narrative explaining how the project's results are expected to make a "
            "difference in terms of impact, beyond the immediate scope and duration of the project. "
            "The narrative should include the components below, tailored to your project. "
            "\n\n"
            "(a) Describe the unique contribution your project results would make towards the "
            "outcomes specified in this topic, in the respective destination in the work programme, "
            "and towards the wider impacts, in the longer term, as specified in the respective "
            "expected impact description in the work programme. "
            "\n\n"
            "(b) Give an indication of the scale and significance of the project's contribution "
            "to the expected outcomes and impacts, including, where appropriate, through the use "
            "of quantified indicators and targets. "
            "\n\n"
            "(c) Describe the credibility of the pathways to achieve the expected outcomes and "
            "impacts specified in the work programme, and any relevant external factors that may "
            "determine whether the impacts will be achieved. "
            "\n\n"
            "(d) Describe any requirements and potential barriers — Loss of connectivity, "
            "dependency on other projects or external factors — that could hamper the progress "
            "towards the expected outcomes and impacts."
        ),
        "evaluation_criteria": (
            "Evaluated under 'Impact' criterion. Evaluators assess: "
            "credibility of pathways to outcomes and impacts; scale and significance of contribution; "
            "alignment with work programme expected outcomes."
        ),
        "page_guidance": "~4-5 pages",
        "tips": [
            "Map directly to the Expected Outcomes listed in the call topic text",
            "Use an impact pathway diagram: Outputs → Outcomes → Impacts",
            "Quantify impacts where possible (e.g., 'reduce CO2 by X tonnes', 'create Y jobs')",
            "Address both scientific/technological and societal/economic impacts",
            "Be honest about barriers and show concrete mitigation strategies",
        ],
        "keywords": [
            "pathways",
            "impact",
            "2.1",
            "outcomes",
            "scale and significance",
            "barriers",
            "expected outcomes",
            "contribution",
        ],
    },
    "impact.dissemination": {
        "name": "2.2 Measures to maximise impact – Dissemination, exploitation and communication",
        "instructions": (
            "Describe the planned measures to maximise the impact of your project by providing "
            "a first version of your 'plan for the dissemination and exploitation including "
            "communication activities'. "
            "\n\n"
            "For dissemination, exploitation and communication: "
            "\n\n"
            "(a) Describe the dissemination, exploitation, and communication measures that are "
            "planned, and the target group(s) addressed (e.g. scientific community, end users, "
            "financial actors, public at large). Describe measures for creating awareness of the "
            "project and for dissemination of the project results. "
            "\n\n"
            "(b) Outline your strategy for knowledge management and protection. Include measures "
            "for the management of research data where relevant, in line with the FAIR principles "
            "(Findable, Accessible, Interoperable, Re-usable). "
            "\n\n"
            "(c) Outline your strategy for the management of intellectual property, foreseen "
            "protection measures, such as patents, design rights, copyright, trade secrets, etc., "
            "and how these would be used to support exploitation. "
            "\n\n"
            "If your project is contributing to the introduction of a new/improved product, process "
            "or service, please describe the steps needed to bring the results to the market."
        ),
        "evaluation_criteria": (
            "Evaluated under 'Impact' criterion. Evaluators assess: "
            "quality of dissemination and exploitation plan; IP management strategy; "
            "suitability of measures to engage target groups."
        ),
        "page_guidance": "~3-5 pages",
        "tips": [
            "Include a dissemination table: Target Group | Message | Channel | Timing | KPI",
            "Distinguish clearly between dissemination (scientific), exploitation (commercial), and communication (public)",
            "Describe your Data Management Plan approach (FAIR principles)",
            "Be specific about IP: who owns what, licensing strategy, freedom-to-operate",
            "Include a preliminary exploitation plan per partner",
        ],
        "keywords": [
            "dissemination",
            "exploitation",
            "communication",
            "2.2",
            "ip",
            "intellectual property",
            "knowledge management",
            "fair principles",
            "patents",
            "market",
        ],
    },
    "impact.summary": {
        "name": "2.3 Summary",
        "instructions": (
            "Provide a summary of this section by presenting in the canvas below the key elements "
            "of your project's impact pathway and of the measures to maximise its impact. "
            "\n\n"
            "The canvas should include: "
            "- Specific Needs: What needs does the project address? "
            "- D&E&C Measures: Dissemination, Exploitation and Communication measures "
            "- Expected Results: Key project outputs (publications, prototypes, pilots, etc.) "
            "- Target Groups: Who will use/benefit from the results? "
            "- Expected Outcomes: What change will the results bring in the short/medium term? "
            "- Expected Impacts: What wider societal/economic/environmental impacts in the longer term?"
        ),
        "evaluation_criteria": (
            "Part of the 'Impact' evaluation. Provides evaluators a quick overview of the impact logic."
        ),
        "page_guidance": "~1 page (canvas/table format)",
        "tips": [
            "Use the official EU impact canvas table format",
            "Keep it concise — this is a summary, not a repeat",
            "Ensure consistency with sections 2.1 and 2.2",
            "Use clear, evaluator-friendly language",
        ],
        "keywords": [
            "summary",
            "2.3",
            "canvas",
            "impact canvas",
            "specific needs",
            "expected results",
        ],
    },
    "implementation.work_plan": {
        "name": "3.1 Work plan and resources",
        "instructions": (
            "Please provide the following: "
            "\n\n"
            "• A brief presentation of the overall structure of the work plan "
            "\n"
            "• Timing of the different work packages and their components "
            "(Gantt chart or similar) "
            "\n"
            "• Graphical presentation of the components showing how they inter-relate "
            "(Pert chart or similar) "
            "\n"
            "• Detailed work package descriptions (Tables 3.1a to 3.1f) "
            "\n\n"
            "Give full details. Base your account on the logical structure of the project "
            "and target groups: what will be done, how, where, when, why, by whom. "
            "The number of work packages should be proportionate to the scale and complexity "
            "of the project and the overall duration."
        ),
        "evaluation_criteria": (
            "Evaluated under 'Quality and efficiency of the implementation' criterion. "
            "Evaluators assess: quality of work plan structure; coherence between work packages; "
            "appropriateness of allocation of tasks and resources."
        ),
        "page_guidance": "~2-3 pages for narrative + tables take additional space",
        "tips": [
            "Include a clear Gantt chart showing WP timelines, milestones, and deliverables",
            "5-7 work packages is typical for a 36-month RIA",
            "Include a dedicated WP for project management and a WP for dissemination/exploitation",
            "Ensure WP dependencies are logical and avoid bottlenecks",
        ],
        "keywords": ["work plan", "3.1", "gantt", "pert", "timing", "resources", "work packages"],
    },
    "implementation.work_packages": {
        "name": "Table 3.1a: List of work packages",
        "instructions": (
            "Provide a table with columns: "
            "Work Package Number | Work Package Title | Lead Participant No | "
            "Lead Participant Short Name | Person-Months | Start Month | End Month"
        ),
        "evaluation_criteria": "Part of implementation evaluation — completeness and coherence.",
        "page_guidance": "~0.5-1 page",
        "tips": [
            "Number WPs sequentially (WP1, WP2, etc.)",
            "WP1 is typically 'Project Management and Coordination'",
            "Last WP is often 'Dissemination, Exploitation, and Communication'",
            "Person-months should be realistic and consistent with budget",
        ],
        "keywords": ["list of work packages", "table 3.1a", "work package list"],
    },
    "implementation.wp_descriptions": {
        "name": "Table 3.1b: Work package descriptions",
        "instructions": (
            "For each work package provide: "
            "\n"
            "- Work package number and title "
            "- Participant short names and effort (person-months) per participant "
            "- Start and end months "
            "- Work package objectives "
            "- Description of work (broken down into tasks with task leaders) "
            "- Role of each non-lead participant"
        ),
        "evaluation_criteria": (
            "Evaluators check: clarity of objectives; logical task breakdown; "
            "appropriate role distribution; feasibility of timelines."
        ),
        "page_guidance": "~1-2 pages per work package",
        "tips": [
            "Each WP should have 2-5 tasks",
            "Clearly identify task leaders with 'Task X.Y (Lead: PARTNER)'",
            "Make WP objectives specific and measurable",
            "Show inter-WP dependencies explicitly",
        ],
        "keywords": [
            "work package description",
            "table 3.1b",
            "wp description",
            "wp objectives",
            "tasks",
        ],
    },
    "implementation.deliverables": {
        "name": "Table 3.1c: List of Deliverables",
        "instructions": (
            "List all deliverables with: "
            "Deliverable Number (D1.1, D2.1, etc.) | Deliverable Name | "
            "Short Description | Work Package Number | Lead Participant Short Name | "
            "Type (R=Report, DEM=Demonstrator, DEC=Websites/patent/etc., DATA, DMP, ETHICS, OTHER) | "
            "Dissemination Level (PU=Public, SEN=Sensitive, CI=Classified) | "
            "Delivery Date (in months)"
        ),
        "evaluation_criteria": "Evaluators check completeness, relevance, and timing of deliverables.",
        "page_guidance": "~1-2 pages",
        "tips": [
            "Aim for 3-5 deliverables per WP",
            "Include milestones reports (periodic reports are mandatory)",
            "Spread deliverables across the project timeline — avoid clustering at the end",
            "Make at least key scientific deliverables Public (PU)",
        ],
        "keywords": ["deliverables", "table 3.1c", "list of deliverables"],
    },
    "implementation.milestones": {
        "name": "Table 3.1d: List of milestones",
        "instructions": (
            "List critical milestones with: "
            "Milestone Number | Milestone Name | Related Work Package(s) | "
            "Due Date (in months) | Means of Verification"
        ),
        "evaluation_criteria": "Evaluators check: are milestones critical decision points? Are means of verification clear?",
        "page_guidance": "~0.5-1 page",
        "tips": [
            "5-10 milestones for a typical 36-month project",
            "Include go/no-go decision points",
            "Milestones should be verifiable events, not just deliverable submissions",
            "Space them reasonably across the project duration",
        ],
        "keywords": ["milestones", "table 3.1d", "list of milestones", "means of verification"],
    },
    "implementation.risks": {
        "name": "Table 3.1e: Critical risks for implementation",
        "instructions": (
            "List critical risks with: "
            "Description of Risk (indicate level of likelihood: Low/Medium/High) | "
            "Work Package(s) Involved | "
            "Proposed Risk-Mitigation Measures"
        ),
        "evaluation_criteria": "Evaluators assess: realistic risk identification; quality of mitigation strategies.",
        "page_guidance": "~1 page",
        "tips": [
            "Include 5-8 risks covering technical, management, and external factors",
            "Be honest — evaluators respect realistic risk assessment",
            "Each risk MUST have a concrete mitigation measure, not generic statements",
            "Include risks related to ethics, data protection, and dependencies on third parties",
        ],
        "keywords": ["risks", "table 3.1e", "critical risks", "mitigation measures"],
    },
    "implementation.staff_effort": {
        "name": "Table 3.1f: Summary of staff effort",
        "instructions": (
            "Provide a table showing person-months per participant per work package. "
            "Rows: Participant numbers/names. Columns: Work package numbers. "
            "Include totals per participant and per work package."
        ),
        "evaluation_criteria": "Evaluators check consistency with budget and WP descriptions.",
        "page_guidance": "~0.5-1 page",
        "tips": [
            "Ensure total PMs match the budget tables in Part A",
            "The coordinator typically has significant effort in WP1 (management)",
            "Distribute effort realistically — no partner should have trivially low effort",
        ],
        "keywords": ["staff effort", "table 3.1f", "person-months", "summary of staff effort"],
    },
    "implementation.consortium": {
        "name": "3.2 Capacity of participants and consortium as a whole",
        "instructions": (
            "Describe the consortium. How does it match the project's objectives, and bring "
            "together the necessary disciplinary and inter-disciplinary knowledge? "
            "\n\n"
            "Show how the partners will have access to critical mass of expertise and to "
            "the infrastructure needed to carry out the project activities. "
            "\n\n"
            "Describe how the members of the consortium complement one another (and cover the "
            "value chain, where appropriate). In what way does each of them contribute to the "
            "project? Show the synergy between participants. "
            "\n\n"
            "If applicable, describe how the consortium is balanced in terms of participation "
            "of different types of participants (academia, industry, SMEs, public bodies, etc.) "
            "and in terms of geographical spread."
        ),
        "evaluation_criteria": (
            "Evaluated under 'Quality and efficiency of implementation'. Evaluators assess: "
            "complementarity and balance of consortium; quality of individual participants; "
            "adequacy of resources."
        ),
        "page_guidance": "~3-4 pages",
        "tips": [
            "Include a consortium table: Partner | Country | Type | Key Expertise | Role in Project",
            "Don't repeat CVs — focus on why THIS combination of partners is uniquely suited",
            "Show value chain coverage if applicable",
            "Highlight previous successful collaborations between partners",
            "Address geographical balance and widening country participation if relevant",
        ],
        "keywords": [
            "consortium",
            "3.2",
            "capacity",
            "participants",
            "complementarity",
            "synergy",
            "geographical spread",
        ],
    },
}


# =============================================================================
# Official Horizon Europe CSA Template (Part B - Full Proposal)
# =============================================================================
CSA_TEMPLATE: dict[str, dict] = {
    "excellence.objectives": {
        "name": "1.1 Objectives",
        "instructions": (
            "Describe the overall and specific objectives for the project. "
            "Objectives should be clear, measurable, realistic and achievable "
            "within the duration of the project."
        ),
        "evaluation_criteria": "Evaluated under 'Excellence'. Clarity and pertinence of objectives.",
        "page_guidance": "~3-4 pages",
        "tips": [
            "CSA objectives focus on coordination and support activities, not research",
            "Emphasize policy support, networking, standardisation, or capacity building",
        ],
        "keywords": ["objectives", "1.1", "clarity", "measurable"],
    },
    "excellence.methodology": {
        "name": "1.2 Coordination and/or support measures and methodology",
        "instructions": (
            "Describe and explain the coordination and/or support measures and the overall "
            "methodology, including the concepts, models and assumptions that underpin your work. "
            "Explain how this will enable you to deliver your project's objectives. "
            "Describe how appropriate open science practices are implemented."
        ),
        "evaluation_criteria": "Evaluated under 'Excellence'. Quality of coordination methodology.",
        "page_guidance": "~4-6 pages",
        "tips": [
            "Focus on coordination mechanisms, stakeholder engagement, and support activities",
            "CSAs don't do primary research — show how you coordinate and support others",
        ],
        "keywords": ["coordination", "support measures", "methodology", "1.2", "open science"],
    },
    "impact.pathways": {
        "name": "2.1 Project's pathways towards impact",
        "instructions": (
            "Provide a narrative explaining how the project's results are expected to make a "
            "difference in terms of impact, beyond the immediate scope and duration of the project. "
            "Describe the unique contribution your project results would make towards the outcomes "
            "specified in this topic."
        ),
        "evaluation_criteria": "Evaluated under 'Impact'. Credibility of pathways to impact.",
        "page_guidance": "~3-4 pages",
        "tips": [
            "CSA impact is often about policy influence, network effects, and capacity building",
            "Show how coordination activities lead to concrete, lasting changes",
        ],
        "keywords": ["pathways", "impact", "2.1", "outcomes", "narrative"],
    },
    "impact.dissemination": {
        "name": "2.2 Measures to maximise impact",
        "instructions": (
            "Describe the planned measures to maximise the impact of your project by providing "
            "a first version of your 'plan for the dissemination and exploitation including "
            "communication activities'. Include IP management strategy where relevant."
        ),
        "evaluation_criteria": "Evaluated under 'Impact'. Quality of D&E&C plan.",
        "page_guidance": "~3-4 pages",
        "tips": [
            "CSAs often focus more on communication and stakeholder engagement than exploitation",
            "Describe how project outputs (guidelines, reports, platforms) will be sustained post-project",
        ],
        "keywords": ["dissemination", "exploitation", "communication", "2.2", "measures"],
    },
    "impact.summary": {
        "name": "2.3 Summary",
        "instructions": (
            "Provide a summary of this section by presenting in the canvas the key elements "
            "of your project's impact pathway and measures to maximise impact."
        ),
        "evaluation_criteria": "Part of Impact evaluation. Quick overview for evaluators.",
        "page_guidance": "~1 page",
        "tips": ["Use the official EU impact canvas format."],
        "keywords": ["summary", "2.3", "canvas", "impact canvas"],
    },
    "implementation.work_plan": {
        "name": "3.1 Work plan and resources",
        "instructions": (
            "Provide a brief presentation of the overall structure of the work plan; "
            "timing of the different work packages and their components (Gantt chart or similar). "
            "Include detailed work package descriptions."
        ),
        "evaluation_criteria": "Evaluated under 'Implementation'. Quality and coherence of work plan.",
        "page_guidance": "~2-3 pages + tables",
        "tips": ["CSA work plans are typically simpler than RIA, with fewer WPs (3-5)."],
        "keywords": ["work plan", "3.1", "gantt", "work packages"],
    },
    "implementation.work_packages": {
        "name": "Table 3.1a: List of work packages",
        "instructions": "Provide a table listing all work packages with lead participant, person-months, and timing.",
        "evaluation_criteria": "Completeness and coherence.",
        "page_guidance": "~0.5 page",
        "tips": ["Keep WP structure lean for CSAs."],
        "keywords": ["list of work packages", "table 3.1a"],
    },
    "implementation.wp_descriptions": {
        "name": "Table 3.1b: Work package descriptions",
        "instructions": "For each work package provide objectives, task breakdown, and participant roles.",
        "evaluation_criteria": "Clarity of tasks and role distribution.",
        "page_guidance": "~1 page per WP",
        "tips": ["Focus on coordination and support tasks, not research tasks."],
        "keywords": ["work package description", "table 3.1b"],
    },
    "implementation.deliverables": {
        "name": "Table 3.1c: List of Deliverables",
        "instructions": "List all deliverables with type, dissemination level, and delivery date.",
        "evaluation_criteria": "Relevance and completeness.",
        "page_guidance": "~1 page",
        "tips": [
            "CSA deliverables are often reports, guidelines, policy briefs, and event proceedings."
        ],
        "keywords": ["deliverables", "table 3.1c"],
    },
    "implementation.milestones": {
        "name": "Table 3.1d: List of milestones",
        "instructions": "List milestones with related WPs, due dates, and means of verification.",
        "evaluation_criteria": "Are milestones meaningful decision points?",
        "page_guidance": "~0.5 page",
        "tips": ["Include stakeholder engagement milestones."],
        "keywords": ["milestones", "table 3.1d"],
    },
    "implementation.risks": {
        "name": "Table 3.1e: Critical risks for implementation",
        "instructions": "List critical risks with likelihood, severity, and mitigation measures.",
        "evaluation_criteria": "Realistic risk identification and quality of mitigation.",
        "page_guidance": "~0.5-1 page",
        "tips": ["CSA risks often relate to stakeholder engagement and political context."],
        "keywords": ["risks", "table 3.1e"],
    },
    "implementation.staff_effort": {
        "name": "Table 3.1f: Summary of staff effort",
        "instructions": "Provide person-months per participant per work package.",
        "evaluation_criteria": "Consistency with budget.",
        "page_guidance": "~0.5 page",
        "tips": ["Ensure effort is proportionate to the CSA scope."],
        "keywords": ["staff effort", "table 3.1f", "person-months"],
    },
    "implementation.consortium": {
        "name": "3.2 Capacity of participants and consortium",
        "instructions": (
            "Describe the consortium composition and how it matches the project's objectives. "
            "Show complementarity and access to relevant stakeholder networks."
        ),
        "evaluation_criteria": "Quality and complementarity of consortium.",
        "page_guidance": "~2-3 pages",
        "tips": [
            "CSA consortia should demonstrate strong policy and stakeholder networks",
            "Show access to relevant communities and decision-makers",
        ],
        "keywords": ["consortium", "3.2", "capacity", "networks"],
    },
}


# =============================================================================
# Official Horizon Europe ERC Template (Part B1 and B2 - Starting/Consolidator/Advanced)
# =============================================================================
ERC_TEMPLATE: dict[str, dict] = {
    "excellence.synopsis": {
        "name": "Part B1 - Section a: Extended Synopsis",
        "instructions": (
            "Describe the envisaged research project. Lay out the current state of knowledge. "
            "Explain the scientific question and objectives. Present the overall approach or "
            "research strategy to reach the goals of the project. "
            "\n\n"
            "This section should convince the evaluation panel that the proposal presents an original "
            "and creative idea addressing an important question in the respective research field(s). "
            "It should substantiate how the project will advance the frontier of knowledge and "
            "what contribution it will make to the research field (what may be changed, opened, "
            "challenged, or altered)."
        ),
        "evaluation_criteria": (
            "Evaluated under 'Excellence' (Step 1). Evaluators assess: "
            "Ground-breaking nature, ambition and feasibility of the research project. "
            "Specifically, to what extent the proposed research addresses important challenges, "
            "is high-risk/high-gain, and goes beyond the state-of-the-art."
        ),
        "page_guidance": "Max 5 pages (references do not count towards the limit)",
        "tips": [
            "Write a highly compelling, standalone narrative. Step 1 remote evaluators will ONLY read Part B1",
            "Clearly state the central research question or hypothesis in bold early on",
            "Clearly define the 'High-Risk / High-Gain' profile: explain why it is risky but why the payoff is revolutionary",
            "Highlight why you (the PI) are uniquely qualified to pull this off",
        ],
        "keywords": [
            "synopsis",
            "b1",
            "extended synopsis",
            "part i",
            "hypothesis",
            "high-risk",
            "high-gain",
            "frontier of knowledge",
            "scientific question",
        ],
    },
    "excellence.cv_track": {
        "name": "Part B1 - Section b & c: CV and Track Record",
        "instructions": (
            "Provide your CV details including Personal Details, Education, Current and Previous "
            "Positions. Under Research Achievements and Peer Recognition, list up to ten research "
            "outputs that demonstrate how you have advanced knowledge in your field, with emphasis "
            "on recent achievements (e.g. publications, preprint servers, books, patents, software, etc.). "
            "\n\n"
            "Under Additional Information, you may mention career breaks, diverse career paths, "
            "major life events, and other contributions to the research community (peer review, "
            "responsibilities, leadership roles)."
        ),
        "evaluation_criteria": (
            "Evaluated under 'Excellence' (Principal Investigator). Evaluators assess: "
            "Intellectual capacity, creativity, and commitment of the PI. Specifically, "
            "whether the PI has demonstrated the ability to propose and conduct ground-breaking research, "
            "creative thinking, and has a strong track record relative to their career stage."
        ),
        "page_guidance": "Max 4 pages",
        "tips": [
            "Use the official template structure (Education, Positions, Research Achievements)",
            "For each of the 10 selected achievements/publications, add a 2-3 sentence qualitative description of its impact",
            "Explain any career gaps or non-traditional paths factually — panels are trained to take this into account fairly",
        ],
        "keywords": [
            "cv",
            "curriculum vitae",
            "track record",
            "achievements",
            "personal details",
            "education",
            "career break",
            "peer recognition",
            "positions",
            "funding id",
        ],
    },
    "excellence.scientific_proposal": {
        "name": "Part B2 - Scientific Proposal",
        "instructions": (
            "Provide a detailed explanation of the project implementation, including research "
            "methodology, work plan, risk assessment, mitigating measures and any further necessary "
            "background not included in Part I. "
            "\n\n"
            "This section should describe: "
            "(a) State-of-the-art and objectives: detail the objectives, state of art, and conceptual framework. "
            "(b) Methodology: detail the research path, key intermediate stages, work packages, "
            "and risks. Explain how you will handle potential bottlenecks."
        ),
        "evaluation_criteria": (
            "Evaluated under 'Excellence' (Step 2). Evaluators assess: "
            "feasibility of the scientific approach; appropriateness of the research methodology; "
            "quality of the work plan; appropriateness of risk mitigation."
        ),
        "page_guidance": "Max 7 pages (references do not count towards the limit)",
        "tips": [
            "This is evaluated in Step 2 by panel members and specialist external reviewers",
            "Be much more technically detailed here than in the Extended Synopsis",
            "Include a Gantt chart showing the research phases, work packages, and key milestones",
            "Include a clear risk-bottleneck analysis table with concrete alternative pathways",
            "Do NOT include the budget table or resources description here (as of 2026, it is in Part A)",
        ],
        "keywords": [
            "b2",
            "scientific proposal",
            "part ii",
            "state-of-the-art",
            "methodology",
            "conceptual framework",
            "work plan",
            "risk assessment",
            "mitigating measures",
            "bottlenecks",
        ],
    },
    "implementation.funding_id": {
        "name": "Part B2 - Appendix: Funding ID",
        "instructions": (
            "Provide details of all current research grants and on-going / submitted grant applications. "
            "For each, list the project title, funding source, amount, period, your role, and the relation "
            "to the current ERC proposal. Clearly describe any scientific overlap."
        ),
        "evaluation_criteria": "Evaluated for scientific overlap and PI commitment. Evaluators check that there is no double funding.",
        "page_guidance": "Mandatory appendix (does not count towards page limits)",
        "tips": [
            "State 'No funding' or 'None' if you do not have current grants or pending applications",
            "For relation to ERC proposal, write a clear description showing that while it may build on previous work, there is ZERO duplication or overlap",
        ],
        "keywords": [
            "funding id",
            "grants",
            "on-going",
            "applications",
            "overlap",
            "double funding",
            "current research grants",
        ],
    },
    "implementation.resources": {
        "name": "Part A - Section C: Resources",
        "instructions": (
            "State the resources needed for the project. Explain and justify the staff effort (person-months) "
            "for the PI and team members, purchase costs (travel, equipment, other goods and services), "
            "subcontracting, and any request for additional funding (e.g. major equipment, access to large "
            "infrastructures, major experimental work). "
            "\n\n"
            "This description should match the detailed budget table submitted online in Part A."
        ),
        "evaluation_criteria": (
            "Evaluated in Step 2. Evaluators assess: "
            "whether the requested resources are fully justified and necessary for the implementation of the project."
        ),
        "page_guidance": "Max 8000 characters (entered directly in the online system)",
        "tips": [
            "Break down the team member roles clearly: Postdocs, PhDs, Technicians",
            "Provide explicit justification for any expensive equipment requests",
            "Ensure the total requested budget aligns perfectly with the online tables",
        ],
        "keywords": [
            "resources",
            "budget justification",
            "other costs",
            "subcontracting",
            "person-months",
            "staff effort",
            "travel",
            "equipment",
            "purchase costs",
        ],
    },
}


# =============================================================================
# Official Horizon Europe MSCA PF Template (Postdoctoral Fellowships)
# =============================================================================
MSCA_PF_TEMPLATE: dict[str, dict] = {
    "excellence.objectives": {
        "name": "1.1 Research and innovation objectives",
        "instructions": (
            "Describe the quality and pertinence of the project’s research and innovation objectives, "
            "and the extent to which they are ambitious, and go beyond the state of the art. "
            "Explain the scientific question and objectives, laying out the state of knowledge."
        ),
        "evaluation_criteria": "Evaluated under 'Excellence' (50% overall weight). Quality, pertinence, ambition, and novelty of objectives.",
        "page_guidance": "~1.5-2 pages",
        "tips": [
            "Frame the research objectives in a way that matches the supervisor's expertise and the host's focus",
            "Make sure the state-of-the-art overview is concise and highlights a clear knowledge gap",
        ],
        "keywords": [
            "objectives",
            "ambition",
            "state of the art",
            "scientific question",
            "knowledge gap",
        ],
    },
    "excellence.methodology": {
        "name": "1.2 Soundness of the proposed methodology",
        "instructions": (
            "Describe the overall methodology, including concepts, models, and assumptions. "
            "Highlight interdisciplinary approaches, consideration of the gender dimension and other "
            "diversity aspects (if relevant), and the quality of open science practices."
        ),
        "evaluation_criteria": "Evaluated under 'Excellence'. Soundness of scientific approach, gender integration, and open science practices.",
        "page_guidance": "~2 pages",
        "tips": [
            "Explain specifically how open science (e.g. repository uploads, open access) will be implemented",
            "If gender/diversity is not relevant, write a highly convincing, logical justification",
        ],
        "keywords": [
            "methodology",
            "interdisciplinary",
            "gender dimension",
            "open science",
            "diversity",
        ],
    },
    "excellence.supervision": {
        "name": "1.3 Supervision, training and transfer of knowledge",
        "instructions": (
            "Describe the quality of the supervision, training and of the two-way transfer of knowledge "
            "between the researcher and the host. Explain how the researcher will gain new skills and "
            "how the host institution will benefit from the researcher's expertise."
        ),
        "evaluation_criteria": "Evaluated under 'Excellence'. Quality of supervision, credibility of training plan, and two-way knowledge transfer.",
        "page_guidance": "~1.5-2 pages",
        "tips": [
            "Detail a concrete Personal Career Development Plan (PCDP)",
            "Specify both advanced scientific skills and transferable skills (e.g. grant writing, project management) to be acquired",
            "Include a table showing the transfer of knowledge activities between you and the host team",
        ],
        "keywords": [
            "supervision",
            "training",
            "transfer of knowledge",
            "two-way",
            "skills",
            "pcdp",
            "mentor",
            "career development",
            "development plan",
            "training objectives",
            "career development plan",
        ],
    },
    "excellence.experience": {
        "name": "1.4 Researcher's professional experience and skills",
        "instructions": (
            "Discuss the quality and appropriateness of the researcher’s professional experience, "
            "competences and skills. Show how your qualifications are suited to deliver the project."
        ),
        "evaluation_criteria": "Evaluated under 'Excellence'. Match between researcher's profile and the project.",
        "page_guidance": "~0.5-1 page",
        "tips": [
            "Do not just copy your CV — describe how your past achievements prove you can complete the proposed tasks",
            "Highlight your publication track record, leadership roles, or international mobility",
        ],
        "keywords": [
            "experience",
            "competences",
            "skills",
            "qualifications",
            "track record",
            "researcher profile",
        ],
    },
    "impact.career": {
        "name": "2.1 Career perspectives and employability",
        "instructions": (
            "Describe the credibility of the measures to enhance the career perspectives and employability "
            "of the researcher and contribution to his/her skills development. Address specific measures "
            "inside and/or outside academia, and expected contribution of skills development."
        ),
        "evaluation_criteria": "Evaluated under 'Impact' (30% overall weight). Enhancement of career prospects and employability.",
        "page_guidance": "~1-1.5 pages",
        "tips": [
            "Be specific about your career goal (e.g., Professor, Industry R&D Lead) and how this fellowship is the critical stepping stone",
            "Outline specific networks you will join and key industry/academic contacts you will make",
        ],
        "keywords": [
            "career",
            "employability",
            "perspectives",
            "skills development",
            "academia",
            "industry",
        ],
    },
    "impact.dissemination": {
        "name": "2.2 Measures to maximise outcomes and impacts",
        "instructions": (
            "Describe the suitability and quality of the measures to maximise expected outcomes and impacts, "
            "as set out in the dissemination and exploitation plan, including communication activities. "
            "Address target groups, intellectual property strategy, and knowledge management."
        ),
        "evaluation_criteria": "Evaluated under 'Impact'. Quality of dissemination/exploitation plan and public engagement.",
        "page_guidance": "~1-1.5 pages",
        "tips": [
            "Distinguish between Dissemination (to peers), Exploitation (commercial/clinical use), and Communication (to general public)",
            "Include concrete KPIs for public engagement (e.g. school visits, blog posts, science festivals)",
        ],
        "keywords": [
            "dissemination",
            "exploitation",
            "communication",
            "measures",
            "ip",
            "public engagement",
            "outcomes",
        ],
    },
    "impact.contribution": {
        "name": "2.3 Scientific, societal and economic impacts",
        "instructions": (
            "Describe the magnitude and importance of the project’s contribution to the expected scientific, "
            "societal and economic impacts. Provide a credible narrative outlining the longer term effects "
            "beyond the project duration, indicating magnitude (widespreadness) and importance (value)."
        ),
        "evaluation_criteria": "Evaluated under 'Impact'. Credibility and significance of long-term impacts.",
        "page_guidance": "~1 page",
        "tips": [
            "Quantify impacts where possible (e.g., 'addressing a disease affecting X million Europeans')",
            "Ensure the scientific impact is described, and justify if economic or societal impacts are minor",
        ],
        "keywords": [
            "scientific impact",
            "societal",
            "economic",
            "magnitude",
            "importance",
            "pathways",
        ],
    },
    "implementation.work_plan": {
        "name": "3.1 Work plan and risk assessment",
        "instructions": (
            "Describe the quality and effectiveness of the work plan, assessment of risks and appropriateness "
            "of the effort assigned to work packages. Provide details on task allocation, WPs, deliverables, "
            "milestones, and a Gantt chart. Detail critical risks and mitigation."
        ),
        "evaluation_criteria": (
            "Evaluated under 'Implementation' (20% overall weight). Coherence of work plan, "
            "adequacy of person-months, and credibility of risk mitigation."
        ),
        "page_guidance": "~1.5-2 pages (including Gantt chart)",
        "tips": [
            "Use 3-4 work packages (e.g., WP1: Research, WP2: Training, WP3: Dissemination/Management)",
            "The Gantt chart MUST fit on one page and show training events, conferences, secondments, and milestones clearly",
        ],
        "keywords": [
            "work plan",
            "risks",
            "gantt",
            "work packages",
            "deliverables",
            "milestones",
            "effort",
            "mitigation",
        ],
    },
    "implementation.capacity": {
        "name": "3.2 Capacity of host and participating organisations",
        "instructions": (
            "Describe the quality and capacity of the host institutions and participating organisations, "
            "including hosting arrangements. Show how the hosting environment supports the researcher, "
            "integration, and access to necessary infrastructures."
        ),
        "evaluation_criteria": "Evaluated under 'Implementation'. Institutional infrastructure, hosting capacity, and supervisor integration.",
        "page_guidance": "~0.5-1 page",
        "tips": [
            "Highlight the host institution's experience in managing EU projects and welcoming mobile researchers (e.g., Euraxess member)",
            "Detail the physical infrastructure (labs, equipment, office space) that is already available for your project",
        ],
        "keywords": [
            "capacity",
            "host",
            "hosting arrangements",
            "participating organisations",
            "infrastructure",
            "integration",
        ],
    },
}


# =============================================================================
# Official Horizon Europe MSCA DN Template (Doctoral Networks)
# =============================================================================
MSCA_DN_TEMPLATE: dict[str, dict] = {
    "excellence.objectives": {
        "name": "1.1 Research and innovation objectives",
        "instructions": (
            "Provide the introduction, objectives and overview of the overall research programme. "
            "Describe the individual Doctoral Candidate (DC) research projects, objectives, and "
            "pertinence/innovative aspects of the research programme in light of the state of the art."
        ),
        "evaluation_criteria": "Evaluated under 'Excellence' (50% weight). Research quality, pertinence, and innovative aspects of doctoral network.",
        "page_guidance": "~4-5 pages",
        "tips": [
            "Include a summary table of all DC projects (e.g., DC1 title, Host, Supervisor, Target Degree)",
            "Define a clear, unifying research theme that ties all individual DC projects together",
        ],
        "keywords": [
            "objectives",
            "doctoral candidate",
            "dc",
            "research programme",
            "state of the art",
            "innovative aspects",
            "scientific objective",
        ],
    },
    "excellence.methodology": {
        "name": "1.2 Soundness of the proposed methodology",
        "instructions": (
            "Describe the overall methodology, conceptual framework, and assumptions. Explain "
            "the integration of methods and disciplines, gender dimension/diversity, and open science practices."
        ),
        "evaluation_criteria": "Evaluated under 'Excellence'. Coherence and quality of research methodology, gender dimension, and open science.",
        "page_guidance": "~3-4 pages",
        "tips": [
            "Describe how the interdisciplinary and inter-sectoral nature is integrated into the research methodology",
            "Outline how open science will be managed collectively across all network beneficiaries",
        ],
        "keywords": ["methodology", "disciplines", "gender dimension", "open science", "diversity"],
    },
    "excellence.training": {
        "name": "1.3 Training programme quality and credibility",
        "instructions": (
            "Provide an overview and content structure of the doctoral training programme. Describe "
            "scientific and transferable skills training, inter-sectoral and international exposure. "
            "Include Table 1 showing main network-wide training events, conferences, and contributions."
        ),
        "evaluation_criteria": "Evaluated under 'Excellence'. Quality and structure of training programme, transferable skills, and sectoral exposure.",
        "page_guidance": "~3 pages (including Table 1)",
        "tips": [
            "Structure training in three tiers: local training, network-wide training, and secondments",
            "Fill out Table 1 completely with specific months and locations (tentative) for winter/summer schools",
        ],
        "keywords": [
            "training programme",
            "transferable skills",
            "events",
            "conferences",
            "table 1",
            "secondments",
            "doctoral training",
        ],
    },
    "excellence.supervision": {
        "name": "1.4 Supervision quality",
        "instructions": (
            "Describe the qualifications and supervision experience of supervisors. Detail the quality "
            "of supervision for DN, and the mandatory joint supervision arrangements for Industrial "
            "and Joint Doctorate modes (if applicable)."
        ),
        "evaluation_criteria": "Evaluated under 'Excellence'. Supervisor track records and joint supervision credibility.",
        "page_guidance": "~1-1.5 pages",
        "tips": [
            "Show that supervisors have a strong record of successfully mentoring PhD students to graduation",
            "Explain the supervision governance: how supervisors coordinate and handle student progress reviews",
        ],
        "keywords": [
            "supervision",
            "supervisors",
            "experience",
            "joint supervision",
            "supervision arrangements",
        ],
    },
    "impact.training_structuring": {
        "name": "2.1 Structuring doctoral training and strengthening innovation capacity",
        "instructions": (
            "Describe the potential for: (a) Meaningful contribution of the non-academic sector to the "
            "doctoral training, as appropriate to the mode/field. (b) Developing sustainable (=lasting) "
            "elements of doctoral programmes after the end of the DN funding."
        ),
        "evaluation_criteria": "Evaluated under 'Impact' (30% weight). Contribution to European doctoral training structures and innovation capacity.",
        "page_guidance": "~1.5-2 pages",
        "tips": [
            "Show how non-academic partners participate in teaching, supervision, and hosting secondments",
            "Propose concrete mechanisms to sustain the network (e.g., joint degree agreements, future grant bids)",
        ],
        "keywords": [
            "structuring",
            "doctoral training",
            "non-academic sector",
            "sustainable elements",
            "innovation capacity",
        ],
    },
    "impact.career": {
        "name": "2.2 Career perspectives and employability",
        "instructions": (
            "Describe the credibility of the measures to enhance the career perspectives and employability "
            "of the doctoral candidates, and contribution to their skills development. Address "
            "impact of the research/training on the fellows' careers."
        ),
        "evaluation_criteria": "Evaluated under 'Impact'. Employability enhancement and career development support.",
        "page_guidance": "~1-1.5 pages",
        "tips": [
            "Focus on how the dual academic/non-academic exposure makes graduates highly competitive for jobs",
            "Outline career tracking plans (following up on graduates' career paths post-project)",
        ],
        "keywords": [
            "career",
            "employability",
            "skills",
            "fellows",
            "job market",
            "career perspectives",
        ],
    },
    "impact.dissemination": {
        "name": "2.3 Measures to maximise outcomes and impacts",
        "instructions": (
            "Describe the dissemination, exploitation, and communication plan, and the target groups "
            "addressed. Detail the strategy for knowledge management, IP protection, and data management."
        ),
        "evaluation_criteria": "Evaluated under 'Impact'. Quality of dissemination/exploitation plan and communication measures.",
        "page_guidance": "~1.5-2 pages",
        "tips": [
            "Propose a joint IP management policy for results co-generated by candidates at different hosts",
            "Define concrete communication campaigns (e.g., European Researchers' Night, social media channels)",
        ],
        "keywords": [
            "dissemination",
            "exploitation",
            "communication",
            "ip",
            "intellectual property",
            "knowledge management",
        ],
    },
    "impact.contribution": {
        "name": "2.4 Magnitude and importance of contribution",
        "instructions": (
            "Provide a narrative explaining how the project’s results are expected to make a difference "
            "in terms of scientific, economic/technological, and societal impacts. Indicate "
            "magnitude and importance with quantified estimates where possible."
        ),
        "evaluation_criteria": "Evaluated under 'Impact'. Scale, significance, and credibility of long-term pathways to impact.",
        "page_guidance": "~1 page",
        "tips": [
            "Differentiate clearly between short-term outcomes (during project) and long-term impacts (after project)",
            "Quantify the market size or societal challenge addressed by the network's research",
        ],
        "keywords": [
            "scientific impact",
            "societal",
            "economic",
            "magnitude",
            "importance",
            "pathways",
        ],
    },
    "implementation.work_plan": {
        "name": "3.1 Work plan and risk assessment",
        "instructions": (
            "Describe the quality and effectiveness of the work plan, assessment of risks and appropriateness "
            "of the effort assigned to work packages. Provide details on task allocation, WPs, deliverables, "
            "milestones, Gantt chart, and critical risks with mitigation."
        ),
        "evaluation_criteria": "Evaluated under 'Implementation' (20% weight). Coherence of work plan, WP structure, and risk mitigation.",
        "page_guidance": "~3-4 pages (including Gantt chart & tables)",
        "tips": [
            "Create a Gantt chart showing the recruitment timeline (which should be early, e.g. M1-M12)",
            "Include a WP dedicated to training and a WP dedicated to management/governance",
        ],
        "keywords": [
            "work plan",
            "risks",
            "gantt",
            "work packages",
            "deliverables",
            "milestones",
            "mitigation",
        ],
    },
    "implementation.consortium": {
        "name": "3.2 Consortium capacity, roles and hosting arrangements",
        "instructions": (
            "Describe the quality, capacity and role of each participant, including hosting arrangements "
            "and the extent to which the consortium as a whole brings together the necessary expertise. "
            "Explain complementarity, synergy, and management/governance structures."
        ),
        "evaluation_criteria": "Evaluated under 'Implementation'. Complementarity of partners, governance credibility, and hosting adequacy.",
        "page_guidance": "~2-3 pages",
        "tips": [
            "Detail the Supervisory Board structure, which must include representatives from the doctoral candidates",
            "Justify the participation of any international partners or third parties outside Europe",
        ],
        "keywords": [
            "consortium",
            "participants",
            "hosting arrangements",
            "governance",
            "supervisory board",
            "complementarity",
            "synergy",
        ],
    },
}


# =============================================================================
# Official Horizon Europe EIC Pathfinder Template (Part B - Full Proposal)
# =============================================================================
EIC_PATHFINDER_TEMPLATE: dict[str, dict] = {
    "excellence.vision": {
        "name": "1.1 Long-term vision",
        "instructions": (
            "Describe the long-term vision of the project. Explain the radical, new technology "
            "that the project aims to establish, and how it differs from current paradigms."
        ),
        "evaluation_criteria": "Evaluated under 'Excellence' (60% weight). Convincing long-term vision of a radically new technology.",
        "page_guidance": "~1 page",
        "tips": [
            "Be bold and visionary. Pathfinder is for early-stage, high-risk deep tech",
            "Clearly state: 'The long-term vision of this project is to...'",
        ],
        "keywords": [
            "vision",
            "long-term",
            "1.1",
            "radical",
            "new technology",
            "deep tech",
            "paradigms",
        ],
    },
    "excellence.breakthrough": {
        "name": "1.2 Science-towards-technology breakthrough",
        "instructions": (
            "Describe the science-towards-technology breakthrough. Explain the scientific "
            "principles that enable the proposed breakthrough, and why it is feasible now."
        ),
        "evaluation_criteria": "Evaluated under 'Excellence'. Novelty and feasibility of the scientific breakthrough.",
        "page_guidance": "~1-1.5 pages",
        "tips": [
            "Explain the scientific foundation that makes your radical idea credible",
            "Show why previous attempts failed and what has changed to make it possible now",
        ],
        "keywords": [
            "breakthrough",
            "science-towards-technology",
            "1.2",
            "scientific principles",
            "novelty",
            "feasibility",
        ],
    },
    "excellence.objectives": {
        "name": "1.3 Objectives",
        "instructions": (
            "Describe the overall and specific objectives. Objectives must be clear, measurable, "
            "realistic, and achievable. Explain TRL progression (Pathfinder projects typically target TRL 1 to 3/4)."
        ),
        "evaluation_criteria": "Evaluated under 'Excellence'. Clarity and feasibility of objectives.",
        "page_guidance": "~1 page",
        "tips": [
            "Define concrete, measurable parameters for your final proof-of-concept",
            "Explicitly define your starting TRL (usually TRL 1 or 2) and target TRL (usually TRL 3 or 4)",
        ],
        "keywords": ["objectives", "1.3", "measurable", "trl", "proof-of-concept"],
    },
    "excellence.interdisciplinarity": {
        "name": "1.4 Interdisciplinarity",
        "instructions": (
            "Describe the interdisciplinarity of the project. Show how the combination of different "
            "scientific disciplines, methods, and concepts is necessary to achieve the breakthrough."
        ),
        "evaluation_criteria": "Evaluated under 'Excellence'. Quality of interdisciplinary approach.",
        "page_guidance": "~0.5-1 page",
        "tips": [
            "Don't just list departments — explain how disciplines will actively collaborate and feed into each other",
            "Illustrate the interdisciplinary integration with a diagram showing information flow between work packages",
        ],
        "keywords": [
            "interdisciplinarity",
            "1.4",
            "disciplines",
            "methods",
            "collaboration",
            "integration",
        ],
    },
    "impact.long_term": {
        "name": "2.1 Long-term impact",
        "instructions": (
            "Describe the expected long-term impacts. Explain the potential to create new markets, "
            "disrupt existing ones, or address major societal/environmental challenges."
        ),
        "evaluation_criteria": "Evaluated under 'Impact' (20% weight). Significance and credibility of long-term economic or societal impact.",
        "page_guidance": "~1.5 pages",
        "tips": [
            "Describe the new market or ecosystem that will emerge from your technology",
            "Align with EU policy priorities (e.g. Green Deal, digital sovereignty)",
        ],
        "keywords": [
            "long-term impact",
            "2.1",
            "market creation",
            "disruption",
            "societal challenge",
            "policy priorities",
        ],
    },
    "impact.innovation": {
        "name": "2.2 Innovation potential",
        "instructions": (
            "Describe the innovation potential. Explain the measures to protect IP, manage knowledge, "
            "and develop a commercialisation pathway or business model."
        ),
        "evaluation_criteria": "Evaluated under 'Impact'. Quality of measures to protect and exploit results.",
        "page_guidance": "~1-1.5 pages",
        "tips": [
            "Specify who will lead the exploitation (e.g., spin-off, licensing)",
            "Mention the use of EIC transition/accelerator as a future pathway",
        ],
        "keywords": [
            "innovation potential",
            "2.2",
            "ip",
            "intellectual property",
            "commercialisation",
            "business model",
            "exploitation",
        ],
    },
    "impact.communication": {
        "name": "2.3 Communication and Dissemination",
        "instructions": (
            "Describe the planned communication and dissemination measures. Show how you will raise "
            "awareness, target scientific and non-scientific communities, and manage data (FAIR principles)."
        ),
        "evaluation_criteria": "Evaluated under 'Impact'. Quality of dissemination/communication plan.",
        "page_guidance": "~0.5-1 page",
        "tips": [
            "Define concrete channels for scientific dissemination (high-impact journals, conferences)",
            "Detail data sharing in public repositories to support open science",
        ],
        "keywords": [
            "communication",
            "dissemination",
            "2.3",
            "awareness",
            "target groups",
            "fair data",
            "open science",
        ],
    },
    "implementation.work_plan": {
        "name": "3.1 Work plan and allocation of resources",
        "instructions": (
            "Provide the work plan structure, WPs, tasks, Gantt chart, milestones, deliverables, "
            "and critical risks with mitigation measures."
        ),
        "evaluation_criteria": "Evaluated under 'Implementation' (20% weight). Coherence of work plan, resource allocation, and risk mitigation.",
        "page_guidance": "~3 pages + tables",
        "tips": [
            "Ensure person-month allocations per WP match the expertise of the partners leading those tasks",
            "Identify key milestones that act as decision points for high-risk research paths",
        ],
        "keywords": [
            "work plan",
            "3.1",
            "resources",
            "work packages",
            "deliverables",
            "milestones",
            "risks",
            "gantt",
        ],
    },
    "implementation.team": {
        "name": "3.2 Quality of the team",
        "instructions": (
            "Describe the project team. Show that the Principal Investigators and researchers have "
            "the high-quality capabilities, expertise, and motivation to carry out the project."
        ),
        "evaluation_criteria": "Evaluated under 'Implementation'. Expertise and quality of key personnel.",
        "page_guidance": "~1 page",
        "tips": [
            "Focus on the track record of the PIs in breakthrough research",
            "Highlight any awards, key publications, or patents held by the team members",
        ],
        "keywords": ["team", "3.2", "quality", "expertise", "investigators", "personnel"],
    },
    "implementation.consortium": {
        "name": "3.3 Consortium capacity and complementarity",
        "instructions": (
            "Describe the consortium as a whole. Show how the members complement one another, "
            "bring the necessary multidisciplinary expertise, and cover the value chain."
        ),
        "evaluation_criteria": "Evaluated under 'Implementation'. Consortium balance, synergy, and complementarity.",
        "page_guidance": "~1-1.5 pages",
        "tips": [
            "Showcase the synergy between academic partners (basic science) and industrial/SME partners (application/validation)",
            "Include a table summarizing each partner's unique role and contribution",
        ],
        "keywords": ["consortium", "3.3", "complementarity", "synergy", "balance", "value chain"],
    },
}


# =============================================================================
# Official Horizon Europe EIC Transition Template (Part B - Full Proposal)
# =============================================================================
EIC_TRANSITION_TEMPLATE: dict[str, dict] = {
    "excellence.novelty": {
        "name": "1.1 Technological breakthrough",
        "instructions": (
            "Describe the technological breakthrough. Explain the degree of novelty and performance "
            "compared to other technologies available or in development, and the competitive advantages. "
            "Show how the proposal builds on the results of a eligible previous project (ERC, EIC Pathfinder)."
        ),
        "evaluation_criteria": "Evaluated under 'Excellence'. Degree of novelty, performance, and link to previous project results.",
        "page_guidance": "~2 pages",
        "tips": [
            "Clearly state the previous project acronym and grant number on which this is based",
            "Detail the core technology result (TRL 3/4) that is being matured",
        ],
        "keywords": [
            "technological breakthrough",
            "1.1",
            "novelty",
            "performance",
            "competitive advantage",
            "previous project",
            "state of the art",
        ],
    },
    "excellence.objectives": {
        "name": "1.2 Objectives",
        "instructions": (
            "Describe the objectives for technology maturation and business development. Objectives "
            "must be clear, measurable, and timed. Provide measurable KPIs for both technology and business."
        ),
        "evaluation_criteria": "Evaluated under 'Excellence'. Credibility and feasibility of technological and business maturation objectives.",
        "page_guidance": "~1.5 pages",
        "tips": [
            "Transition projects must mature BOTH the technology (TRL 5/6) and the business model",
            "Define separate tables for Technology KPIs (e.g. power efficiency, speed) and Business KPIs (e.g. customer interviews, pricing validation)",
        ],
        "keywords": [
            "objectives",
            "1.2",
            "maturation",
            "business development",
            "kpis",
            "measurable",
        ],
    },
    "excellence.methodology": {
        "name": "1.3 Methodology",
        "instructions": (
            "Describe the overall methodology. Explain why the timing is right for this innovation. "
            "Detail compliance with the 'Do No Significant Harm' (DNSH) principles. Explain open science practices."
        ),
        "evaluation_criteria": "Evaluated under 'Excellence'. Methodology quality, timing, TRL credibility, and open science.",
        "page_guidance": "~1.5-2 pages",
        "tips": [
            "Explain why the market or regulatory landscape now makes this technology viable",
            "Clearly address the six environmental objectives under DNSH rules",
        ],
        "keywords": [
            "methodology",
            "1.3",
            "timing",
            "dnsh",
            "do no significant harm",
            "open science",
            "trl",
        ],
    },
    "impact.credibility": {
        "name": "2.1 Credibility of the impacts",
        "instructions": (
            "Describe the business validation process, market exploration, and go-to-market strategy. "
            "Outline your strategy for IP management, protection, and licensing. Show how you validated "
            "the problem/solution fit."
        ),
        "evaluation_criteria": "Evaluated under 'Impact'. Commercial credibility, market validation, and IP strategy.",
        "page_guidance": "~2.5 pages",
        "tips": [
            "Detail customer discovery activities (e.g., plans for 100+ stakeholder interviews)",
            "Outline your patent filing strategy and how you will manage Freedom to Operate (FTO)",
        ],
        "keywords": [
            "credibility of the impacts",
            "2.1",
            "business validation",
            "go-to-market",
            "ip",
            "intellectual property",
            "fto",
            "market exploration",
            "problem/solution fit",
        ],
    },
    "impact.benefits": {
        "name": "2.2 Economic and/or societal benefits",
        "instructions": (
            "Describe the scale-up potential and global market size. Explain expected benefits "
            "for the EU, Member States, strategic autonomy, jobs, and sustainability."
        ),
        "evaluation_criteria": "Evaluated under 'Impact'. Scale-up potential and economic/societal benefits.",
        "page_guidance": "~1 page",
        "tips": [
            "Provide quantitative market size forecasts (TAM, SAM, SOM)",
            "Highlight how this technology strengthens European strategic value chains",
        ],
        "keywords": [
            "benefits",
            "2.2",
            "scale-up",
            "market size",
            "strategic autonomy",
            "societal benefits",
            "tam",
            "sam",
            "som",
        ],
    },
    "impact.readiness": {
        "name": "2.3 Investment readiness",
        "instructions": (
            "Describe the commercialisation model (spin-off, licensing, joint venture). Explain how "
            "activities will make the team and technology investment ready. Show plans to raise capital."
        ),
        "evaluation_criteria": "Evaluated under 'Impact'. Investment readiness potential and go-to-market model clarity.",
        "page_guidance": "~1.5 pages",
        "tips": [
            "State clearly: 'Our primary path to market is... (e.g. Spin-off creation in Month 18)'",
            "Mention target venture capital firms or strategic partners you plan to pitch to",
        ],
        "keywords": [
            "investment readiness",
            "2.3",
            "commercialisation model",
            "spin-off",
            "licensing",
            "raising capital",
            "venture capital",
        ],
    },
    "implementation.team": {
        "name": "3.1 Quality and motivation of the team",
        "instructions": (
            "Describe the team's capabilities, commercial expertise, and motivation. Show that the "
            "team has the necessary skills to move from lab to market and build a business proposition."
        ),
        "evaluation_criteria": "Evaluated under 'Implementation'. Team quality, balance, and commercial development capabilities.",
        "page_guidance": "~1-1.5 pages",
        "tips": [
            "Transition requires business/commercial talent — show who has start-up or product management experience",
            "If there are skill gaps (e.g. no full-time CEO), describe your concrete recruitment plan",
        ],
        "keywords": [
            "team",
            "3.1",
            "quality",
            "motivation",
            "commercial expertise",
            "skills gap",
            "recruitment",
        ],
    },
    "implementation.milestones": {
        "name": "3.2 KPIs and Milestones",
        "instructions": (
            "List measurable milestones and KPIs to track progress. Describe critical technical, market, "
            "and financial risks, and mitigation measures."
        ),
        "evaluation_criteria": "Evaluated under 'Implementation'. Relevance of milestones, risk identification, and mitigation.",
        "page_guidance": "~1 page",
        "tips": [
            "Milestones should cover technical achievements (e.g. prototype works at X efficiency) and business achievements (e.g. spin-off incorporated)",
            "Be realistic about market risks (e.g., competitor action, regulatory delay)",
        ],
        "keywords": ["kpis and milestones", "3.2", "risks", "mitigation", "milestones"],
    },
    "implementation.workplan": {
        "name": "3.3 Workplan and allocation of resources",
        "instructions": (
            "Describe the work packages, tasks, Gantt chart, and resources (person-months). Justify "
            "the number of partners and effort distribution."
        ),
        "evaluation_criteria": "Evaluated under 'Implementation'. Work plan structure, resource efficiency, and partner roles.",
        "page_guidance": "~1.5-2 pages + tables",
        "tips": [
            "Keep the consortium small (usually 1 to 5 partners) to remain agile",
            "Include a work package dedicated to Business Development and Market Validation",
        ],
        "keywords": [
            "workplan",
            "3.3",
            "resources",
            "work packages",
            "gantt",
            "deliverables",
            "person-months",
        ],
    },
}


# =============================================================================
# Official Horizon Europe EIC Accelerator Template (Part B - Full Proposal)
# =============================================================================
EIC_ACCELERATOR_TEMPLATE: dict[str, dict] = {
    "business.description": {
        "name": "1. Company Description",
        "instructions": (
            "Describe the company, its origins, vision, ownership, and current size. Detail key historical "
            "milestones, current revenues, and active customer base."
        ),
        "evaluation_criteria": "Evaluated under 'Implementation' (team and company capacity). Company maturity, viability, and capacity to scale.",
        "page_guidance": "~1 page",
        "tips": [
            "State clearly when the company was founded, how many employees you have, and your current cap table",
            "Provide a brief summary of total funding raised to date (grants, equity, debt)",
        ],
        "keywords": [
            "company description",
            "business case",
            "startup",
            "history",
            "ownership",
            "revenues",
            "employees",
            "cap table",
        ],
    },
    "business.problem": {
        "name": "2. The Problem/Opportunity",
        "instructions": (
            "Describe the problem or market opportunity you are addressing. Detail the customer pain point, "
            "market size, and why current solutions are inadequate."
        ),
        "evaluation_criteria": "Evaluated under 'Impact'. Credibility of the market opportunity and potential demand.",
        "page_guidance": "~1 page",
        "tips": [
            "Quantify the pain point: how much money/time do customers lose due to the problem?",
            "Identify the target buyer persona and end user",
        ],
        "keywords": [
            "problem",
            "opportunity",
            "pain point",
            "market need",
            "buyer persona",
            "customer pain",
        ],
    },
    "excellence.innovation": {
        "name": "3. The Innovation: Solution/USP",
        "instructions": (
            "Describe your innovation. Detail the technology, product, or service. Explain the Unique "
            "Selling Proposition (USP) and TRL level (EIC Accelerator targets TRL 5/6 to 8 for grant, and 9 for investment). "
            "Detail IP status, patents, and Freedom to Operate."
        ),
        "evaluation_criteria": "Evaluated under 'Excellence'. Novelty of the technology, uniqueness of USP, and feasibility of TRL progression.",
        "page_guidance": "~2.5 pages",
        "tips": [
            "Clearly explain why your technology is a game-changer compared to state-of-the-art",
            "Include a table listing your patent applications, status, and FTO search results",
        ],
        "keywords": [
            "innovation",
            "solution",
            "product",
            "service",
            "usp",
            "unique selling point",
            "trl",
            "patents",
            "fto",
        ],
    },
    "impact.market": {
        "name": "4. Market Analysis and Competition",
        "instructions": (
            "Provide a detailed market analysis. Detail market size, growth rate, and segmentation. "
            "Perform a detailed competition analysis listing key competitors and your advantages."
        ),
        "evaluation_criteria": "Evaluated under 'Impact'. Market understanding, competition analysis credibility, and market size viability.",
        "page_guidance": "~2 pages",
        "tips": [
            "Use a competitive matrix table comparing your product to 3-4 top competitors on key features/pricing",
            "Provide TAM, SAM, and SOM figures with citations to credible market reports",
        ],
        "keywords": [
            "market analysis",
            "competition",
            "competitors",
            "market size",
            "tam",
            "sam",
            "som",
            "growth rate",
            "segmentation",
        ],
    },
    "impact.marketing": {
        "name": "5. Marketing and Sales Plan",
        "instructions": (
            "Describe your go-to-market strategy, marketing plan, and sales model. Detail pricing "
            "strategy, distribution channels, and customer acquisition costs (CAC) vs Customer Lifetime Value (LTV)."
        ),
        "evaluation_criteria": "Evaluated under 'Impact'. Commercial viability of the sales/marketing model and pricing credibility.",
        "page_guidance": "~2 pages",
        "tips": [
            "Explain your sales model: B2B direct sales, B2C subscription, licensing?",
            "Provide a timeline showing your sales projections and commercial launch date",
        ],
        "keywords": [
            "marketing",
            "sales plan",
            "go-to-market",
            "customer acquisition",
            "cac",
            "ltv",
            "pricing",
            "channels",
        ],
    },
    "implementation.team": {
        "name": "6. Team and Management",
        "instructions": (
            "Describe the founders, management team, and key personnel. Show their track record in scaling "
            "businesses. Detail advisory board and recruitment plans for key hires."
        ),
        "evaluation_criteria": "Evaluated under 'Implementation'. Team quality, balance, execution capacity, and commitment.",
        "page_guidance": "~1.5 pages",
        "tips": [
            "Include short bios highlighting commercial success, prior exits, and technical depth",
            "Highlight the gender balance of your team and board",
        ],
        "keywords": [
            "team",
            "management",
            "key people",
            "organizational chart",
            "founders",
            "bios",
            "recruitment",
            "advisors",
        ],
    },
    "implementation.risks": {
        "name": "7. Risks and Need for Union Support",
        "instructions": (
            "Detail company risks (technological, market, financial, regulatory). Explain the need "
            "for EU support and why private investors are not willing to fund the company at this stage "
            "(risk profile/non-bankability)."
        ),
        "evaluation_criteria": "Evaluated under 'Implementation' (risk level) and 'Need for Union Support'. Bankability and risk profile assessment.",
        "page_guidance": "~1.5 pages",
        "tips": [
            "Explain why the company is 'non-bankable' at this moment (e.g. technology risk is too high for commercial banks, capital needed is too large for local VCs)",
            "Be transparent about technical bottlenecks and how EIC funding de-risks the company for future rounds",
        ],
        "keywords": [
            "risks",
            "union support",
            "financial risk",
            "technical risk",
            "non-bankability",
            "de-risking",
            "funding gap",
        ],
    },
    "implementation.financials": {
        "name": "8. Financial Plan",
        "instructions": (
            "Provide financial projections for the next 5 years (revenues, expenses, cash flow). Explain "
            "funding requirements, cash runway, and future funding rounds."
        ),
        "evaluation_criteria": "Evaluated under 'Implementation'. Financial viability and credibility of projections.",
        "page_guidance": "~1 page",
        "tips": [
            "Include a summary table with 5-year projections (Year 1 to Year 5) for Revenue, EBITDA, and Headcount",
            "State your current cash runway in months",
        ],
        "keywords": [
            "financial plan",
            "revenues",
            "projections",
            "funding",
            "funding mix",
            "cash runway",
            "cash flow",
            "ebitda",
        ],
    },
    "implementation.work_plan": {
        "name": "9. Implementation Plan (WPs/Milestones)",
        "instructions": (
            "Describe the work packages for TRL 5/6 to 8 activities (for grant) and TRL 9 activities (for investment). "
            "Provide work package descriptions, lead partners, deliverables, milestones, risks, and Gantt chart."
        ),
        "evaluation_criteria": "Evaluated under 'Implementation'. Coherence of work plan and efficiency of resource allocation.",
        "page_guidance": "~2.5 pages + tables",
        "tips": [
            "TRL 5-8 activities (grant) should focus on clinical trials, system integration, pilot lines",
            "TRL 9 activities (investment) should cover commercial scale-up, marketing, and global roll-out",
        ],
        "keywords": [
            "implementation plan",
            "work packages",
            "deliverables",
            "milestones",
            "grant component",
            "investment component",
            "gantt",
        ],
    },
    "implementation.value_point": {
        "name": "10. How EU Support takes company to next value point",
        "instructions": (
            "Describe how EIC support will accelerate your growth. Detail the next value points (milestones) "
            "and how this funding will attract private co-investors."
        ),
        "evaluation_criteria": "Evaluated under 'Need for Union Support'. Leverage potential of EU funding.",
        "page_guidance": "~0.5 page",
        "tips": [
            "Explain how the EIC Accelerator grant/equity will act as a stamp of quality that unlocks matching private venture capital",
            "Define the next major value inflection point (e.g. FDA approval, first $10M ARR)",
        ],
        "keywords": [
            "value point",
            "next value point",
            "eu support benefit",
            "leverage",
            "co-investors",
            "growth acceleration",
        ],
    },
    "implementation.funding_request": {
        "name": "11. The Funding Request",
        "instructions": (
            "Detail the requested grant amount (up to €2.5M) and equity component (up to €15M). "
            "Explain the funding mix and allocation of budget items."
        ),
        "evaluation_criteria": "Evaluated under 'Implementation'. Cost efficiency and appropriateness of budget request.",
        "page_guidance": "~0.5 page",
        "tips": [
            "Clearly state: 'We request a grant of €X,XXX,XXX and an equity investment of €X,XXX,XXX'",
            "Ensure the grant request covers no more than 70% of eligible costs for TRL 5-8 activities",
        ],
        "keywords": [
            "funding request",
            "grant request",
            "equity request",
            "funding mix",
            "budget allocation",
        ],
    },
    "impact.broad": {
        "name": "12. Broad Impacts",
        "instructions": (
            "Describe the societal, economic, environmental, and/or climate impact of your proposal. "
            "Explain how it addresses European goals, job creation, and sustainable growth."
        ),
        "evaluation_criteria": "Evaluated under 'Impact'. Broad societal, environmental, and economic benefits.",
        "page_guidance": "~1 page",
        "tips": [
            "Align directly with the UN Sustainable Development Goals (SDGs)",
            "Forecast the number of high-quality jobs your company will create in Europe over 5 years",
        ],
        "keywords": [
            "broad impact",
            "societal",
            "economic",
            "environmental",
            "climate impact",
            "sdgs",
            "job creation",
        ],
    },
}


# =============================================================================
# Helper Functions
# =============================================================================


def get_template_by_type(proposal_type: str) -> dict[str, dict]:
    """Return the full template dictionary based on proposal type."""
    proposal_type = (proposal_type or "RIA").upper()
    if proposal_type == "CSA":
        return CSA_TEMPLATE
    elif proposal_type == "ERC":
        return ERC_TEMPLATE
    elif proposal_type == "MSCA-PF":
        return MSCA_PF_TEMPLATE
    elif proposal_type == "MSCA-DN":
        return MSCA_DN_TEMPLATE
    elif proposal_type == "EIC-PATHFINDER":
        return EIC_PATHFINDER_TEMPLATE
    elif proposal_type == "EIC-TRANSITION":
        return EIC_TRANSITION_TEMPLATE
    elif proposal_type == "EIC-ACCELERATOR":
        return EIC_ACCELERATOR_TEMPLATE
    # Default to RIA/IA structure which is the most common
    return RIA_IA_TEMPLATE


def get_instructions_for_section(proposal_type: str, section_id: str) -> str:
    """Return the official EU instructions for a specific section."""
    template = get_template_by_type(proposal_type)
    section_data = template.get(section_id)
    if section_data:
        return section_data.get("instructions", "")
    return ""


def get_full_section_guidance(proposal_type: str, section_id: str) -> str:
    """
    Return comprehensive guidance for a section, including instructions,
    evaluation criteria, page guidance, and writing tips.

    This is intended for injection into the AI agent's system prompt.
    """
    template = get_template_by_type(proposal_type)
    section_data = template.get(section_id)
    if not section_data:
        return ""

    parts = [
        f"### Official EU Template Guidance for: {section_data['name']}",
        "",
        "**What to write:**",
        section_data.get("instructions", ""),
        "",
    ]

    if section_data.get("evaluation_criteria"):
        parts.extend(
            [
                f"**Evaluation criteria:** {section_data['evaluation_criteria']}",
                "",
            ]
        )

    if section_data.get("page_guidance"):
        parts.extend(
            [
                f"**Recommended length:** {section_data['page_guidance']}",
                "",
            ]
        )

    tips = section_data.get("tips", [])
    if tips:
        parts.append("**Expert writing tips:**")
        for tip in tips:
            parts.append(f"- {tip}")
        parts.append("")

    return "\n".join(parts)


def get_all_sections_overview(proposal_type: str) -> str:
    """
    Return a brief overview of ALL sections in the template.
    Useful for giving the agent awareness of the full document structure.
    """
    template = get_template_by_type(proposal_type)
    lines = [f"### Full proposal structure ({proposal_type}):", ""]
    for section_id, data in template.items():
        page_hint = data.get("page_guidance", "")
        lines.append(f"- **{data['name']}** (`{section_id}`) — {page_hint}")
    return "\n".join(lines)

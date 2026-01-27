"""
Central constants for Horizon Europe mappings and configurations.

This module provides a single source of truth for:
- Cluster mappings and keywords
- Action type definitions
- Programme mappings
- Common patterns used across the application
"""
from enum import Enum

# =============================================================================
# HORIZON EUROPE CLUSTERS
# =============================================================================

class HorizonCluster(str, Enum):
    """Horizon Europe thematic clusters."""
    CL1_HEALTH = "CL1"
    CL2_CULTURE = "CL2"
    CL3_SECURITY = "CL3"
    CL4_DIGITAL = "CL4"
    CL5_CLIMATE = "CL5"
    CL6_FOOD = "CL6"


# Cluster code to full name mapping
CLUSTER_NAMES: dict[str, str] = {
    'CL1': 'Cluster 1: Health',
    'CL2': 'Cluster 2: Culture, Creativity & Inclusive Society',
    'CL3': 'Cluster 3: Civil Security for Society',
    'CL4': 'Cluster 4: Digital, Industry & Space',
    'CL5': 'Cluster 5: Climate, Energy & Mobility',
    'CL6': 'Cluster 6: Food, Bioeconomy, Natural Resources, Agriculture & Environment',
}

# Cluster code to short name
CLUSTER_SHORT_NAMES: dict[str, str] = {
    'CL1': 'Health',
    'CL2': 'Culture',
    'CL3': 'Security',
    'CL4': 'Digital',
    'CL5': 'Climate',
    'CL6': 'Food',
}

# Keywords associated with each cluster
CLUSTER_KEYWORDS: dict[str, list[str]] = {
    'CL1': [
        'health', 'cancer', 'pandemic', 'infectious disease', 'mental health',
        'ageing', 'pharmaceutical', 'vaccine', 'medical', 'clinical',
        'diagnosis', 'treatment', 'healthcare', 'biomarker', 'genomics'
    ],
    'CL2': [
        'culture', 'creative', 'democracy', 'governance', 'social',
        'heritage', 'arts', 'media', 'inclusion', 'diversity',
        'migration', 'equality', 'cultural heritage'
    ],
    'CL3': [
        'security', 'cybersecurity', 'disaster', 'border', 'crime',
        'terrorism', 'resilience', 'critical infrastructure', 'civil protection',
        'forensics', 'surveillance'
    ],
    'CL4': [
        'digital', 'industry', 'space', 'ai', 'artificial intelligence',
        'manufacturing', 'robotics', 'data', 'electronics', 'materials',
        'computing', 'quantum', 'semiconductor', 'cloud', 'iot'
    ],
    'CL5': [
        'climate', 'energy', 'mobility', 'transport', 'hydrogen',
        'batteries', 'renewable', 'emissions', 'decarbonisation',
        'clean energy', 'green deal', 'sustainable', 'zero emission'
    ],
    'CL6': [
        'food', 'bioeconomy', 'agriculture', 'environment', 'biodiversity',
        'circular economy', 'water', 'soil', 'forest', 'marine',
        'farming', 'fisheries', 'ecosystems'
    ],
}

# Keyword to cluster code mapping (reverse lookup)
KEYWORD_TO_CLUSTER: dict[str, str] = {}
for cluster, keywords in CLUSTER_KEYWORDS.items():
    for keyword in keywords:
        KEYWORD_TO_CLUSTER[keyword.lower()] = cluster


# =============================================================================
# ACTION TYPES
# =============================================================================

class ActionType(str, Enum):
    """Horizon Europe action types."""
    RIA = "RIA"  # Research and Innovation Action
    IA = "IA"    # Innovation Action
    CSA = "CSA"  # Coordination and Support Action
    COFUND = "COFUND"  # Co-fund Action
    PCP = "PCP"  # Pre-Commercial Procurement
    PPI = "PPI"  # Public Procurement of Innovative solutions


# Action type descriptions
ACTION_TYPE_DESCRIPTIONS: dict[str, str] = {
    'RIA': 'Research and Innovation Action - activities establishing new knowledge and exploring feasibility of new technology',
    'IA': 'Innovation Action - activities directly producing plans, designs, or prototypes for new products/services',
    'CSA': 'Coordination and Support Action - networking, coordination, and support activities',
    'COFUND': 'Co-fund Action - co-funding of national or regional research programs',
    'PCP': 'Pre-Commercial Procurement - joint procurement of R&D services',
    'PPI': 'Public Procurement of Innovative solutions - joint procurement of innovative solutions',
}

# Action type TRL ranges
ACTION_TYPE_TRL: dict[str, tuple] = {
    'RIA': (2, 5),  # TRL 2-5
    'IA': (5, 8),   # TRL 5-8
    'CSA': (None, None),  # N/A
}

# Action type funding rates
ACTION_TYPE_FUNDING_RATES: dict[str, dict[str, int]] = {
    'RIA': {'default': 100},
    'IA': {'large_company': 70, 'sme': 70, 'non_profit': 100, 'university': 100, 'research': 100},
    'CSA': {'default': 100},
}


# =============================================================================
# SPECIAL PROGRAMMES
# =============================================================================

# ERC programme types
ERC_PROGRAMMES: dict[str, dict[str, any]] = {
    'ERC-STG': {'name': 'ERC Starting Grant', 'max_funding': 1_500_000, 'duration': 5},
    'ERC-COG': {'name': 'ERC Consolidator Grant', 'max_funding': 2_000_000, 'duration': 5},
    'ERC-ADG': {'name': 'ERC Advanced Grant', 'max_funding': 2_500_000, 'duration': 5},
    'ERC-POC': {'name': 'ERC Proof of Concept', 'max_funding': 150_000, 'duration': 1.5},
    'ERC-SYG': {'name': 'ERC Synergy Grant', 'max_funding': 10_000_000, 'duration': 6},
}

# EIC programme types
EIC_PROGRAMMES: dict[str, dict[str, any]] = {
    'EIC-PATHFINDER': {'name': 'EIC Pathfinder', 'max_funding': 4_000_000, 'type': 'grant'},
    'EIC-TRANSITION': {'name': 'EIC Transition', 'max_funding': 2_500_000, 'type': 'grant'},
    'EIC-ACCELERATOR': {'name': 'EIC Accelerator', 'max_funding': 2_500_000, 'grant': True, 'equity': 15_000_000},
}

# MSCA programme types
MSCA_PROGRAMMES: dict[str, str] = {
    'MSCA-PF': 'Postdoctoral Fellowships',
    'MSCA-DN': 'Doctoral Networks',
    'MSCA-SE': 'Staff Exchanges',
    'MSCA-COFUND': 'Co-funding of regional, national and international programmes',
    'MSCA-CITIZENS': 'MSCA and Citizens',
}


# =============================================================================
# PROPOSAL STRUCTURE
# =============================================================================

PROPOSAL_SECTIONS: dict[str, dict[str, str]] = {
    'EXCELLENCE': {
        'number': '1',
        'title': 'Excellence',
        'weight': '1/3',
        'threshold': '4/5',
        'subsections': ['Objectives', 'Methodology', 'Ambition']
    },
    'IMPACT': {
        'number': '2',
        'title': 'Impact',
        'weight': '1/3',
        'threshold': '4/5',
        'subsections': ['Outcomes', 'Dissemination', 'Exploitation', 'Communication']
    },
    'IMPLEMENTATION': {
        'number': '3',
        'title': 'Implementation',
        'weight': '1/3',
        'threshold': '3/5',
        'subsections': ['Work Plan', 'Consortium', 'Resources', 'Risk Management']
    },
}


# =============================================================================
# ORGANISATION TYPES
# =============================================================================

ORGANISATION_TYPES: dict[str, str] = {
    'HES': 'Higher or Secondary Education Establishment',
    'REC': 'Research Organisation',
    'PRC': 'Private Company',
    'PUB': 'Public Body',
    'OTH': 'Other',
    'SME': 'Small and Medium Enterprise',
}

ORGANISATION_TYPE_CODES: set[str] = {'HES', 'REC', 'PRC', 'PUB', 'OTH', 'SME'}


# =============================================================================
# CONSORTIUM REQUIREMENTS
# =============================================================================

CONSORTIUM_REQUIREMENTS: dict[str, dict[str, any]] = {
    'RIA': {'min_partners': 3, 'min_countries': 3, 'eu_associated_required': True},
    'IA': {'min_partners': 3, 'min_countries': 3, 'eu_associated_required': True},
    'CSA': {'min_partners': 3, 'min_countries': 3, 'eu_associated_required': True},
    'ERC': {'min_partners': 1, 'min_countries': 1, 'single_pi': True},
    'MSCA-PF': {'min_partners': 1, 'min_countries': 1, 'single_fellow': True},
    'EIC-ACCELERATOR': {'min_partners': 1, 'min_countries': 1, 'sme_only': True},
}


# =============================================================================
# PAGE LIMITS
# =============================================================================

PAGE_LIMITS: dict[str, dict[str, int]] = {
    'RIA': {'single_stage': 45, 'two_stage_outline': 10, 'two_stage_full': 45},
    'IA': {'single_stage': 45, 'two_stage_outline': 10, 'two_stage_full': 45},
    'CSA': {'single_stage': 30},
    'ERC': {'variable': True},  # Check specific call
    'MSCA': {'range': (10, 15)},
    'EIC': {'variable': True},  # Short proposal + full
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_cluster_from_keyword(keyword: str) -> str | None:
    """Get cluster code from a keyword."""
    return KEYWORD_TO_CLUSTER.get(keyword.lower())


def get_cluster_keywords(cluster_code: str) -> list[str]:
    """Get keywords for a cluster code."""
    return CLUSTER_KEYWORDS.get(cluster_code.upper(), [])


def get_cluster_name(cluster_code: str, short: bool = False) -> str:
    """Get cluster name from code."""
    if short:
        return CLUSTER_SHORT_NAMES.get(cluster_code.upper(), cluster_code)
    return CLUSTER_NAMES.get(cluster_code.upper(), cluster_code)


def normalize_cluster_code(cluster_input: str) -> str | None:
    """Normalize various cluster input formats to standard CL# code."""
    cluster_input = cluster_input.strip().upper()

    # Already in CL# format
    if cluster_input.startswith('CL') and len(cluster_input) == 3:
        return cluster_input

    # Numeric format (e.g., "1", "Cluster 1")
    import re
    match = re.search(r'(\d)', cluster_input)
    if match:
        return f'CL{match.group(1)}'

    # Keyword lookup
    for keyword, code in KEYWORD_TO_CLUSTER.items():
        if keyword in cluster_input.lower():
            return code

    return None

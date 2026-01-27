"""
Call Understanding Service

Dynamically analyzes funding calls to extract topic, cluster, and context.
Replaces hardcoded domain-specific logic with intelligent call analysis.
"""

import logging
import os
import re
from dataclasses import dataclass
from enum import Enum

import google.generativeai as genai

logger = logging.getLogger(__name__)


class HorizonCluster(str, Enum):
    """Horizon Europe clusters and programmes."""
    CL1_HEALTH = "CL1"
    CL2_CULTURE = "CL2"
    CL3_SECURITY = "CL3"
    CL4_DIGITAL = "CL4"
    CL5_CLIMATE = "CL5"
    CL6_FOOD = "CL6"
    ERC = "ERC"
    EIC = "EIC"
    MSCA = "MSCA"
    INFRA = "INFRA"
    WIDENING = "WIDENING"
    UNKNOWN = "UNKNOWN"


@dataclass
class CallUnderstanding:
    """Structured understanding of a funding call."""
    call_id: str
    cluster: HorizonCluster
    topic: str
    sub_topics: list[str]
    key_objectives: list[str]
    expected_outcomes: list[str]
    target_trl: str | None
    action_type: str | None  # RIA, IA, CSA, etc.
    terminology: list[str]  # Domain-specific terms to use
    eu_priorities: list[str]  # Relevant EU policies/strategies
    confidence: float


# Cluster detection patterns
CLUSTER_PATTERNS = {
    HorizonCluster.CL1_HEALTH: [
        r'health', r'medical', r'disease', r'clinical', r'pharmaceutical',
        r'patient', r'healthcare', r'cancer', r'pandemic', r'vaccine',
        r'diagnosis', r'therapy', r'biomedical', r'hospital'
    ],
    HorizonCluster.CL2_CULTURE: [
        r'cultur', r'heritage', r'creative', r'democra', r'social',
        r'governance', r'media', r'arts', r'humanit', r'societ'
    ],
    HorizonCluster.CL3_SECURITY: [
        r'security', r'cyber', r'defence', r'crisis', r'disaster',
        r'border', r'terror', r'crime', r'police', r'forensic',
        r'critical infrastructure', r'resilience'
    ],
    HorizonCluster.CL4_DIGITAL: [
        r'digital', r'ai\b', r'artificial intelligence', r'data',
        r'robot', r'autonom', r'quantum', r'5g', r'6g', r'iot',
        r'cloud', r'edge computing', r'blockchain', r'software'
    ],
    HorizonCluster.CL5_CLIMATE: [
        r'climat', r'energy', r'renewable', r'carbon', r'emission',
        r'sustainab', r'green', r'hydrogen', r'battery', r'solar',
        r'wind', r'mobility', r'transport', r'circular'
    ],
    HorizonCluster.CL6_FOOD: [
        r'food', r'agri', r'bio', r'farm', r'soil', r'water',
        r'fisheries', r'forestry', r'rural', r'biodiversity',
        r'ecosystem', r'organic', r'nutrition'
    ],
    HorizonCluster.ERC: [
        r'\berc\b', r'european research council', r'frontier research',
        r'starting grant', r'consolidator', r'advanced grant', r'synergy'
    ],
    HorizonCluster.EIC: [
        r'\beic\b', r'european innovation council', r'accelerator',
        r'pathfinder', r'transition', r'breakthrough'
    ],
    HorizonCluster.MSCA: [
        r'msca', r'marie', r'sklodowska', r'curie', r'fellowship',
        r'doctoral', r'postdoctoral', r'staff exchange', r'cofund'
    ],
}

# Cluster-specific terminology to use in proposals
CLUSTER_TERMINOLOGY = {
    HorizonCluster.CL1_HEALTH: [
        "patient outcomes", "clinical validation", "health technology assessment",
        "EU Health Programme", "European Health Union", "pharmaceutical strategy",
        "health data space", "personalized medicine", "One Health approach",
        "health security", "AMR (antimicrobial resistance)", "rare diseases"
    ],
    HorizonCluster.CL2_CULTURE: [
        "European values", "cultural heritage", "creative industries",
        "democratic participation", "social innovation", "inclusive society",
        "New European Bauhaus", "European Democracy Action Plan",
        "media freedom", "disinformation", "cultural diversity"
    ],
    HorizonCluster.CL3_SECURITY: [
        "cybersecurity", "critical infrastructure protection", "hybrid threats",
        "EU Security Union", "NIS2 Directive", "Cybersecurity Act",
        "ENISA", "digital sovereignty", "strategic autonomy",
        "civil protection", "crisis management", "border security"
    ],
    HorizonCluster.CL4_DIGITAL: [
        "digital transformation", "AI Act", "Data Act", "GDPR",
        "Digital Europe Programme", "European Data Strategy",
        "trustworthy AI", "human-centric", "digital sovereignty",
        "high-performance computing", "digital skills", "interoperability"
    ],
    HorizonCluster.CL5_CLIMATE: [
        "European Green Deal", "Fit for 55", "climate neutrality",
        "clean energy transition", "circular economy", "zero pollution",
        "sustainable mobility", "REPowerEU", "energy efficiency",
        "just transition", "climate adaptation", "biodiversity strategy"
    ],
    HorizonCluster.CL6_FOOD: [
        "Farm to Fork Strategy", "sustainable food systems", "agroecology",
        "Common Agricultural Policy", "food security", "bioeconomy",
        "rural development", "soil health", "water management",
        "forestry strategy", "blue economy", "nature restoration"
    ],
    HorizonCluster.ERC: [
        "frontier research", "scientific excellence", "groundbreaking",
        "paradigm shift", "high-risk high-gain", "Principal Investigator",
        "host institution", "portability", "scientific independence"
    ],
    HorizonCluster.EIC: [
        "deep tech", "market creation", "scale-up", "breakthrough innovation",
        "game-changing", "disruptive", "venture capital", "equity investment",
        "business acceleration", "go-to-market"
    ],
    HorizonCluster.MSCA: [
        "researcher mobility", "career development", "knowledge transfer",
        "intersectoral", "interdisciplinary", "secondments",
        "training programme", "supervision", "transferable skills"
    ],
}

# EU priorities by cluster
CLUSTER_EU_PRIORITIES = {
    HorizonCluster.CL1_HEALTH: [
        "European Health Union", "EU4Health Programme", "Beating Cancer Plan",
        "Pharmaceutical Strategy for Europe", "European Health Data Space"
    ],
    HorizonCluster.CL2_CULTURE: [
        "European Democracy Action Plan", "Media Freedom Act",
        "New European Bauhaus", "European Year of Skills"
    ],
    HorizonCluster.CL3_SECURITY: [
        "EU Security Union Strategy", "EU Cybersecurity Strategy",
        "Strategic Compass", "Civil Protection Mechanism"
    ],
    HorizonCluster.CL4_DIGITAL: [
        "Digital Decade 2030", "European Data Strategy", "AI Act",
        "Chips Act", "Digital Services Act", "Digital Markets Act"
    ],
    HorizonCluster.CL5_CLIMATE: [
        "European Green Deal", "Fit for 55 Package", "REPowerEU",
        "Circular Economy Action Plan", "Biodiversity Strategy 2030"
    ],
    HorizonCluster.CL6_FOOD: [
        "Farm to Fork Strategy", "Common Agricultural Policy",
        "EU Soil Strategy", "Forest Strategy", "Blue Economy"
    ],
    HorizonCluster.ERC: [
        "European Research Area", "Open Science", "Research Excellence"
    ],
    HorizonCluster.EIC: [
        "European Innovation Ecosystems", "Deep Tech Strategy"
    ],
    HorizonCluster.MSCA: [
        "European Research Area", "Researchers' Pact", "Charter for Researchers"
    ],
}


class CallUnderstandingService:
    """
    Service for dynamically understanding funding calls.

    Replaces hardcoded domain logic with intelligent analysis
    that works for any Horizon Europe call.
    """

    def __init__(self):
        genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
        self.model = genai.GenerativeModel('gemini-2.0-flash-lite')
        self._cache: dict[str, CallUnderstanding] = {}

    async def understand_call(
        self,
        call_id: str,
        call_text: str | None = None,
        call_title: str | None = None
    ) -> CallUnderstanding:
        """
        Analyze a call to understand its topic and context.

        Args:
            call_id: The call identifier (e.g., "HORIZON-CL4-2024-DIGITAL-01")
            call_text: Full text of the call (optional)
            call_title: Title of the call (optional)

        Returns:
            CallUnderstanding with extracted information
        """
        # Check cache
        if call_id in self._cache:
            return self._cache[call_id]

        # Step 1: Detect cluster from call ID
        cluster = self._detect_cluster_from_id(call_id)

        # Step 2: If we have text, do deeper analysis
        if call_text or call_title:
            # Refine cluster detection with content
            if cluster == HorizonCluster.UNKNOWN:
                cluster = self._detect_cluster_from_content(call_text or call_title or "")

            # Use LLM for detailed understanding
            understanding = await self._analyze_with_llm(
                call_id=call_id,
                call_text=call_text,
                call_title=call_title,
                detected_cluster=cluster
            )
        else:
            # Minimal understanding from call ID only
            understanding = self._create_minimal_understanding(call_id, cluster)

        # Cache and return
        self._cache[call_id] = understanding
        return understanding

    def _detect_cluster_from_id(self, call_id: str) -> HorizonCluster:
        """Detect cluster from call ID pattern."""
        call_id_upper = call_id.upper()

        # Direct cluster references in call ID
        cluster_mappings = {
            'CL1': HorizonCluster.CL1_HEALTH,
            'CL2': HorizonCluster.CL2_CULTURE,
            'CL3': HorizonCluster.CL3_SECURITY,
            'CL4': HorizonCluster.CL4_DIGITAL,
            'CL5': HorizonCluster.CL5_CLIMATE,
            'CL6': HorizonCluster.CL6_FOOD,
            'HEALTH': HorizonCluster.CL1_HEALTH,
            'CULTURE': HorizonCluster.CL2_CULTURE,
            'SECURITY': HorizonCluster.CL3_SECURITY,
            'DIGITAL': HorizonCluster.CL4_DIGITAL,
            'CLIMATE': HorizonCluster.CL5_CLIMATE,
            'FOOD': HorizonCluster.CL6_FOOD,
            'ERC': HorizonCluster.ERC,
            'EIC': HorizonCluster.EIC,
            'MSCA': HorizonCluster.MSCA,
            'INFRA': HorizonCluster.INFRA,
            'WIDENING': HorizonCluster.WIDENING,
        }

        for key, cluster in cluster_mappings.items():
            if key in call_id_upper:
                return cluster

        return HorizonCluster.UNKNOWN

    def _detect_cluster_from_content(self, text: str) -> HorizonCluster:
        """Detect cluster from content using keyword patterns."""
        text_lower = text.lower()

        cluster_scores = {}

        for cluster, patterns in CLUSTER_PATTERNS.items():
            score = sum(
                len(re.findall(pattern, text_lower))
                for pattern in patterns
            )
            if score > 0:
                cluster_scores[cluster] = score

        if cluster_scores:
            return max(cluster_scores, key=cluster_scores.get)

        return HorizonCluster.UNKNOWN

    async def _analyze_with_llm(
        self,
        call_id: str,
        call_text: str | None,
        call_title: str | None,
        detected_cluster: HorizonCluster
    ) -> CallUnderstanding:
        """Use LLM for detailed call understanding."""

        content_for_analysis = ""
        if call_title:
            content_for_analysis += f"Title: {call_title}\n\n"
        if call_text:
            content_for_analysis += f"Content: {call_text[:4000]}"  # Limit for token efficiency

        prompt = f"""Analyze this Horizon Europe funding call and extract key information.

CALL ID: {call_id}
DETECTED CLUSTER: {detected_cluster.value}

CALL CONTENT:
{content_for_analysis}

Extract the following information in JSON format:
{{
    "main_topic": "Brief description of the main research/innovation topic (1-2 sentences)",
    "sub_topics": ["sub-topic 1", "sub-topic 2", "sub-topic 3"],
    "key_objectives": ["objective 1", "objective 2", "objective 3"],
    "expected_outcomes": ["outcome 1", "outcome 2"],
    "target_trl": "TRL X-Y or null if not specified",
    "action_type": "RIA/IA/CSA/MSCA/ERC or null",
    "domain_terms": ["technical term 1", "technical term 2", "technical term 3"],
    "confidence": 0.85
}}

Focus on extracting factual information from the call. Be specific to this particular call's topic."""

        try:
            response = self.model.generate_content(prompt)
            response_text = response.text

            # Extract JSON from response
            import json

            # Try to find JSON in the response
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if json_match:
                parsed = json.loads(json_match.group())
            else:
                # Fallback to minimal understanding
                return self._create_minimal_understanding(call_id, detected_cluster)

            # Get cluster-specific terminology and priorities
            terminology = CLUSTER_TERMINOLOGY.get(detected_cluster, [])
            terminology.extend(parsed.get('domain_terms', []))

            eu_priorities = CLUSTER_EU_PRIORITIES.get(detected_cluster, [])

            return CallUnderstanding(
                call_id=call_id,
                cluster=detected_cluster,
                topic=parsed.get('main_topic', 'Research and Innovation'),
                sub_topics=parsed.get('sub_topics', []),
                key_objectives=parsed.get('key_objectives', []),
                expected_outcomes=parsed.get('expected_outcomes', []),
                target_trl=parsed.get('target_trl'),
                action_type=parsed.get('action_type'),
                terminology=list(set(terminology)),
                eu_priorities=eu_priorities,
                confidence=parsed.get('confidence', 0.7)
            )

        except Exception as e:
            logger.warning(f"LLM analysis failed for {call_id}: {e}")
            return self._create_minimal_understanding(call_id, detected_cluster)

    def _create_minimal_understanding(
        self,
        call_id: str,
        cluster: HorizonCluster
    ) -> CallUnderstanding:
        """Create minimal understanding when detailed analysis isn't possible."""

        # Generate generic topic based on cluster
        cluster_topics = {
            HorizonCluster.CL1_HEALTH: "Health research and innovation",
            HorizonCluster.CL2_CULTURE: "Culture, creativity and inclusive society",
            HorizonCluster.CL3_SECURITY: "Civil security for society",
            HorizonCluster.CL4_DIGITAL: "Digital, industry and space",
            HorizonCluster.CL5_CLIMATE: "Climate, energy and mobility",
            HorizonCluster.CL6_FOOD: "Food, bioeconomy and natural resources",
            HorizonCluster.ERC: "Frontier research",
            HorizonCluster.EIC: "Breakthrough innovation",
            HorizonCluster.MSCA: "Researcher mobility and training",
            HorizonCluster.INFRA: "Research infrastructures",
            HorizonCluster.WIDENING: "Widening participation and spreading excellence",
            HorizonCluster.UNKNOWN: "Research and innovation",
        }

        return CallUnderstanding(
            call_id=call_id,
            cluster=cluster,
            topic=cluster_topics.get(cluster, "Research and innovation"),
            sub_topics=[],
            key_objectives=[],
            expected_outcomes=[],
            target_trl=None,
            action_type=None,
            terminology=CLUSTER_TERMINOLOGY.get(cluster, []),
            eu_priorities=CLUSTER_EU_PRIORITIES.get(cluster, []),
            confidence=0.5  # Low confidence for minimal understanding
        )

    def get_cluster_terminology(self, cluster: HorizonCluster) -> list[str]:
        """Get terminology specific to a cluster."""
        return CLUSTER_TERMINOLOGY.get(cluster, [])

    def get_cluster_priorities(self, cluster: HorizonCluster) -> list[str]:
        """Get EU priorities relevant to a cluster."""
        return CLUSTER_EU_PRIORITIES.get(cluster, [])

    def clear_cache(self):
        """Clear the understanding cache."""
        self._cache.clear()

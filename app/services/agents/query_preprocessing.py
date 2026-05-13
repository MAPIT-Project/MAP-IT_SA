"""
Query preprocessing utilities extracted from tool_aware_agent.py.

Contains special character normalization, non-English query detection and
translation, and long query condensation logic used by the ToolAwareAgent
before it begins its ReAct reasoning loop.
"""

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any

from ...core.config import settings

logger = logging.getLogger(__name__)

__all__ = [
    "SUBSCRIPT_MAP",
    "SUPERSCRIPT_MAP",
    "TYPOGRAPHY_MAP",
    "SpecialCharResult",
    "normalize_special_characters",
    "LANGUAGE_INDICATORS",
    "LanguageDetectionResult",
    "TranslationResult",
    "detect_query_language",
    "translate_query_to_english",
    "preprocess_non_english_query",
    "LongQueryResult",
    "preprocess_long_query",
]


# =============================================================================
# SPECIAL CHARACTER NORMALIZATION
# =============================================================================

# Unicode subscript/superscript character mappings
SUBSCRIPT_MAP = {
    "₀": "0",
    "₁": "1",
    "₂": "2",
    "₃": "3",
    "₄": "4",
    "₅": "5",
    "₆": "6",
    "₇": "7",
    "₈": "8",
    "₉": "9",
    "ₐ": "a",
    "ₑ": "e",
    "ₒ": "o",
    "ₓ": "x",
    "ᵢ": "i",
    "ⱼ": "j",
    "₊": "+",
    "₋": "-",
    "₌": "=",
    "₍": "(",
    "₎": ")",
}

SUPERSCRIPT_MAP = {
    "⁰": "0",
    "¹": "1",
    "²": "2",
    "³": "3",
    "⁴": "4",
    "⁵": "5",
    "⁶": "6",
    "⁷": "7",
    "⁸": "8",
    "⁹": "9",
    "ⁿ": "n",
    "⁺": "+",
    "⁻": "-",
    "⁼": "=",
    "⁽": "(",
    "⁾": ")",
}

# Smart quotes and other typography
# Using Unicode escapes to avoid duplicate key warnings
TYPOGRAPHY_MAP = {
    "\u2019": "'",  # Right single quotation mark (')
    "\u2018": "'",  # Left single quotation mark (')
    "\u201c": '"',  # Left double quotation mark (")
    "\u201d": '"',  # Right double quotation mark (")
    "\u2013": "-",  # En dash (–)
    "\u2014": "-",  # Em dash (—)
    "\u2026": "...",  # Ellipsis (…)
    "\u2022": "*",  # Bullet (•)
    "\u00b7": ".",  # Middle dot (·)
    "\u00d7": "x",  # Multiplication sign (×)
    "\u00f7": "/",  # Division sign (÷)
    "\u2264": "<=",  # Less than or equal (≤)
    "\u2265": ">=",  # Greater than or equal (≥)
    "\u2260": "!=",  # Not equal (≠)
    "\u00b1": "+/-",  # Plus-minus (±)
    "\u00b0": " degrees",  # Degree sign (°)
    "\u20ac": "EUR",  # Euro sign (€)
    "\u00a3": "GBP",  # Pound sign (£)
    "\u2122": "",  # Trademark (™) - remove
    "\u00ae": "",  # Registered (®) - remove
    "\u00a9": "",  # Copyright (©) - remove
}


@dataclass
class SpecialCharResult:
    """Result of normalizing special characters in a query."""

    original_query: str
    normalized_query: str
    was_normalized: bool
    normalizations_applied: list[str] = field(default_factory=list)


def normalize_special_characters(query: str) -> SpecialCharResult:
    """
    Normalize special characters in a query for consistent processing.

    Handles:
    - Subscripts (CO₂ → CO2, H₂O → H2O)
    - Superscripts (10² → 10^2, m² → m2)
    - Smart quotes ("quotes" → "quotes")
    - Typography (en/em dashes → -, ellipsis → ...)
    - Ampersands (& → and, but preserves in acronyms like R&D)
    - Parentheses and brackets normalization
    - Multiple spaces collapse

    Args:
        query: The original user query

    Returns:
        SpecialCharResult with normalized query and metadata
    """
    if not query:
        return SpecialCharResult(
            original_query=query,
            normalized_query=query,
            was_normalized=False,
        )

    normalized = query
    changes = []

    # 1. Handle subscripts (CO₂ → CO2)
    for char, replacement in SUBSCRIPT_MAP.items():
        if char in normalized:
            count = normalized.count(char)
            normalized = normalized.replace(char, replacement)
            changes.append(f"subscript {char}→{replacement} ({count}x)")

    # 2. Handle superscripts (10² → 10^2 for exponents, m² → m2 for units)
    for char, replacement in SUPERSCRIPT_MAP.items():
        if char in normalized:
            count = normalized.count(char)
            # For numeric superscripts following numbers, add ^ for clarity
            # e.g., 10² → 10^2, but m² → m2
            pattern = rf"(\d)({re.escape(char)})"
            if re.search(pattern, normalized):
                normalized = re.sub(pattern, rf"\1^{replacement}", normalized)
            else:
                normalized = normalized.replace(char, replacement)
            changes.append(f"superscript {char}→{replacement} ({count}x)")

    # 3. Handle smart quotes and typography
    for char, replacement in TYPOGRAPHY_MAP.items():
        if char in normalized:
            count = normalized.count(char)
            normalized = normalized.replace(char, replacement)
            if replacement:  # Only log non-empty replacements
                changes.append(f"typography {char}→{replacement} ({count}x)")
            else:
                changes.append(f"removed {char} ({count}x)")

    # 4. Handle ampersands - smart replacement
    # Preserve & in known acronyms (R&D, M&A, B&B, D&I, etc.)
    preserved_ampersands = [
        "R&D",
        "M&A",
        "B&B",
        "D&I",
        "A&E",
        "P&L",
        "S&P",
        "Q&A",
        "AT&T",
    ]

    # Temporarily replace preserved patterns
    preserved_map = {}
    for i, pattern in enumerate(preserved_ampersands):
        placeholder = f"__AMP_PRESERVE_{i}__"
        if pattern.lower() in normalized.lower():
            # Case-insensitive replacement with preservation
            idx = normalized.lower().find(pattern.lower())
            original_text = normalized[idx : idx + len(pattern)]
            preserved_map[placeholder] = original_text
            normalized = normalized[:idx] + placeholder + normalized[idx + len(pattern) :]

    # Replace standalone & with "and" (with spaces around it)
    if " & " in normalized:
        count = normalized.count(" & ")
        normalized = normalized.replace(" & ", " and ")
        changes.append(f"ampersand ' & '→' and ' ({count}x)")

    # Replace & at start of word (but not in preserved patterns)
    if "&" in normalized and "__AMP" not in normalized.split("&")[0][-10:]:
        # Only replace remaining & that are not part of preserved patterns
        remaining = normalized.count("&") - len(preserved_map)
        if remaining > 0:
            # Replace & that appears between words/phrases
            normalized = re.sub(r"(?<!\w)&(?!\w)", " and ", normalized)
            changes.append(f"ampersand remaining ({remaining}x)")

    # Restore preserved patterns
    for placeholder, original in preserved_map.items():
        normalized = normalized.replace(placeholder, original)

    # 5. Normalize various bracket types
    bracket_pairs = [
        ("【", "["),
        ("】", "]"),
        ("〔", "["),
        ("〕", "]"),
        ("「", '"'),
        ("」", '"'),
        ("『", '"'),
        ("』", '"'),
        ("《", "<"),
        ("》", ">"),
    ]
    for old, new in bracket_pairs:
        if old in normalized:
            count = normalized.count(old)
            normalized = normalized.replace(old, new)
            changes.append(f"bracket {old}→{new} ({count}x)")

    # 6. Normalize multiple spaces to single space
    if "  " in normalized:
        normalized = re.sub(r"\s+", " ", normalized)
        changes.append("collapsed multiple spaces")

    # 7. Strip leading/trailing whitespace
    normalized = normalized.strip()

    was_normalized = normalized != query

    if was_normalized:
        logger.info(f"🔤 Normalized query: {changes}")
        logger.debug(f"  Original: {query}")
        logger.debug(f"  Normalized: {normalized}")

    return SpecialCharResult(
        original_query=query,
        normalized_query=normalized,
        was_normalized=was_normalized,
        normalizations_applied=changes,
    )


# =============================================================================
# NON-ENGLISH QUERY HANDLING
# =============================================================================

# Common non-English words and patterns for language detection
# These are high-frequency words that strongly indicate the language
LANGUAGE_INDICATORS = {
    "fr": {  # French
        "words": [
            "trouvez",
            "trouver",
            "chercher",
            "cherchez",
            "appels",
            "appel",
            "financement",
            "pour",
            "dans",
            "les",
            "des",
            "une",
            "est",
            "sont",
            "avec",
            "sur",
            "que",
            "qui",
            "nous",
            "vous",
            "comment",
            "quels",
            "quelles",
            "quel",
            "quelle",
            "énergie",
            "renouvelable",
            "recherche",
            "projets",
            "européen",
            "européenne",
            "subvention",
            "subventions",
            "demande",
            "demander",
            "je",
            "suis",
            "mon",
            "notre",
            "peut",
            "peuvent",
            "avoir",
            "être",
            "faire",
            "fais",
            "veut",
            "veux",
            "voulons",
        ],
        "patterns": [
            r"\b(l'|d'|qu'|n'|s'|c'|j'|m'|t')\w+",  # French contractions
            r"\bà\s",  # French preposition
            r"\bé\w+",  # Words starting with é
        ],
        "name": "French",
    },
    "de": {  # German
        "words": [
            "finden",
            "suchen",
            "förderung",
            "finanzierung",
            "forschung",
            "projekte",
            "energie",
            "erneuerbare",
            "anträge",
            "antrag",
            "können",
            "möchten",
            "haben",
            "sind",
            "wird",
            "werden",
            "für",
            "mit",
            "und",
            "oder",
            "nach",
            "bei",
            "wie",
            "was",
            "welche",
            "welcher",
            "gibt",
            "kann",
            "müssen",
            "sollte",
            "ich",
            "wir",
            "sie",
            "mein",
            "unser",
        ],
        "patterns": [
            r"\b\w+ung\b",  # German -ung suffix
            r"\b\w+keit\b",  # German -keit suffix
            r"\b\w+schaft\b",  # German -schaft suffix
            r"\bß\w*",  # Words with ß
            r"\b(ä|ö|ü)\w+",  # Words with German umlauts
        ],
        "name": "German",
    },
    "es": {  # Spanish
        "words": [
            "buscar",
            "encontrar",
            "convocatorias",
            "convocatoria",
            "financiación",
            "energía",
            "renovable",
            "investigación",
            "proyectos",
            "para",
            "con",
            "los",
            "las",
            "una",
            "uno",
            "que",
            "como",
            "cuáles",
            "cuál",
            "dónde",
            "puede",
            "pueden",
            "tenemos",
            "queremos",
            "necesitamos",
            "solicitar",
            "solicitud",
            "subvención",
            "subvenciones",
            "yo",
            "nosotros",
            "nuestra",
            "nuestro",
        ],
        "patterns": [
            r"\b\w+ción\b",  # Spanish -ción suffix
            r"\b¿",  # Spanish inverted question mark
            r"\b¡",  # Spanish inverted exclamation
            r"\bñ\w*",  # Words with ñ
        ],
        "name": "Spanish",
    },
    "it": {  # Italian
        "words": [
            "trovare",
            "cercare",
            "bandi",
            "bando",
            "finanziamento",
            "finanziamenti",
            "energia",
            "rinnovabile",
            "ricerca",
            "progetti",
            "progetto",
            "per",
            "con",
            "gli",
            "una",
            "sono",
            "come",
            "quali",
            "quale",
            "dove",
            "possiamo",
            "vogliamo",
            "abbiamo",
            "domanda",
            "richiesta",
            "sovvenzione",
            "io",
            "noi",
            "nostro",
            "nostra",
        ],
        "patterns": [
            r"\b\w+zione\b",  # Italian -zione suffix
            r"\b\w+ità\b",  # Italian -ità suffix
        ],
        "name": "Italian",
    },
    "pt": {  # Portuguese
        "words": [
            "encontrar",
            "buscar",
            "procurar",
            "chamadas",
            "chamada",
            "financiamento",
            "energia",
            "renovável",
            "pesquisa",
            "projetos",
            "projeto",
            "para",
            "com",
            "uma",
            "são",
            "como",
            "quais",
            "qual",
            "onde",
            "podemos",
            "queremos",
            "temos",
            "solicitação",
            "subvenção",
            "eu",
            "nós",
            "nosso",
            "nossa",
        ],
        "patterns": [
            r"\b\w+ção\b",  # Portuguese -ção suffix
            r"\b\w+ões\b",  # Portuguese -ões suffix
        ],
        "name": "Portuguese",
    },
    "nl": {  # Dutch
        "words": [
            "vinden",
            "zoeken",
            "oproepen",
            "financiering",
            "energie",
            "hernieuwbare",
            "onderzoek",
            "projecten",
            "voor",
            "met",
            "een",
            "zijn",
            "hoe",
            "welke",
            "waar",
            "kunnen",
            "willen",
            "hebben",
            "aanvraag",
            "subsidie",
            "ik",
            "wij",
            "onze",
        ],
        "patterns": [
            r"\b\w+heid\b",  # Dutch -heid suffix
            r"\bij\b",  # Dutch "ij" digraph
        ],
        "name": "Dutch",
    },
    "pl": {  # Polish
        "words": [
            "znaleźć",
            "szukać",
            "nabory",
            "nabór",
            "finansowanie",
            "energia",
            "odnawialna",
            "badania",
            "projekty",
            "dla",
            "jak",
            "które",
            "gdzie",
            "możemy",
            "chcemy",
            "mamy",
            "wniosek",
            "dotacja",
            "ja",
            "my",
            "nasz",
            "nasza",
        ],
        "patterns": [
            r"\b\w+ość\b",  # Polish -ość suffix
            r"[ąćęłńóśźż]",  # Polish diacritics
        ],
        "name": "Polish",
    },
}

# Translation prompts for LLM-based translation
TRANSLATION_PROMPT_TEMPLATE = """Translate the following {source_lang} query to English.
This is an EU funding query, so preserve any:
- Programme names (Horizon Europe, Erasmus+, Creative Europe, etc.)
- Technical terms
- Organization names
- Call IDs (e.g., HORIZON-xxx)
- Country names

Translate naturally and preserve the query intent.

Original query ({source_lang}):
{query}

English translation (provide ONLY the translation, no other text):"""


@dataclass
class LanguageDetectionResult:
    """Result of detecting the language of a query."""

    original_query: str
    detected_language: str  # ISO 639-1 code or "en" for English
    language_name: str  # Human-readable name
    confidence: float  # 0.0 to 1.0
    is_english: bool
    detection_method: str  # "pattern", "word_frequency", "default"
    matched_indicators: list[str] = field(default_factory=list)


@dataclass
class TranslationResult:
    """Result of translating a non-English query."""

    original_query: str
    translated_query: str
    source_language: str
    source_language_name: str
    was_translated: bool
    translation_method: str  # "llm", "passthrough"
    confidence: float


def detect_query_language(query: str) -> LanguageDetectionResult:
    """
    Detect the language of a user query using pattern matching and word frequency.

    This uses a lightweight rule-based approach that:
    1. Checks for language-specific patterns (contractions, suffixes)
    2. Counts matches against common words in each language
    3. Returns the most likely language with confidence score

    Args:
        query: The user's query text

    Returns:
        LanguageDetectionResult with detected language and confidence
    """
    if not query or not query.strip():
        return LanguageDetectionResult(
            original_query=query,
            detected_language="en",
            language_name="English",
            confidence=1.0,
            is_english=True,
            detection_method="default",
        )

    query_lower = query.lower()
    query_words = set(re.findall(r"\b\w+\b", query_lower))

    # Score each language
    language_scores: dict[str, dict] = {}

    for lang_code, indicators in LANGUAGE_INDICATORS.items():
        score = 0.0
        matched = []

        # Check word matches (weighted by word frequency in query)
        word_matches = query_words.intersection(set(indicators["words"]))
        if word_matches:
            # Weight by number of matches and their presence
            word_score = len(word_matches) * 2.0
            score += word_score
            matched.extend(list(word_matches)[:5])  # Keep top 5 for debugging

        # Check pattern matches
        for pattern in indicators["patterns"]:
            pattern_matches = re.findall(pattern, query_lower)
            if pattern_matches:
                score += len(pattern_matches) * 1.5
                matched.append(f"pattern:{pattern[:20]}...")

        language_scores[lang_code] = {
            "score": score,
            "matched": matched,
            "name": indicators["name"],
        }

    # Find the highest scoring language
    if language_scores:
        best_lang = max(language_scores.keys(), key=lambda k: language_scores[k]["score"])
        best_score = language_scores[best_lang]["score"]

        # Confidence thresholds:
        # - Score >= 4.0: High confidence (multiple word/pattern matches)
        # - Score >= 2.0: Medium confidence
        # - Score < 2.0: Low confidence, likely English

        if best_score >= 2.0:
            # Normalize confidence to 0-1 range (cap at 10 for normalization)
            confidence = min(best_score / 10.0, 1.0)

            logger.info(
                f"🌍 Detected language: {language_scores[best_lang]['name']} "
                f"(score={best_score:.1f}, matches={language_scores[best_lang]['matched'][:3]})"
            )

            return LanguageDetectionResult(
                original_query=query,
                detected_language=best_lang,
                language_name=language_scores[best_lang]["name"],
                confidence=confidence,
                is_english=False,
                detection_method="word_frequency",
                matched_indicators=language_scores[best_lang]["matched"],
            )

    # Default to English
    return LanguageDetectionResult(
        original_query=query,
        detected_language="en",
        language_name="English",
        confidence=0.8,  # Moderate confidence as default
        is_english=True,
        detection_method="default",
    )


def translate_query_to_english(
    query: str, source_language: str, source_language_name: str, llm: Any = None
) -> TranslationResult:
    """
    Translate a non-English query to English using LLM.

    Args:
        query: The original query in source language
        source_language: ISO 639-1 code of source language
        source_language_name: Human-readable language name
        llm: LLM instance for translation (e.g., Gemini)

    Returns:
        TranslationResult with translated query
    """
    if not llm:
        logger.warning("No LLM available for translation, passing through original query")
        return TranslationResult(
            original_query=query,
            translated_query=query,
            source_language=source_language,
            source_language_name=source_language_name,
            was_translated=False,
            translation_method="passthrough",
            confidence=0.0,
        )

    try:
        prompt = TRANSLATION_PROMPT_TEMPLATE.format(source_lang=source_language_name, query=query)

        response = llm.generate_content(prompt)
        translated = response.text.strip()

        # Clean up the translation (remove quotes if present)
        if translated.startswith('"') and translated.endswith('"'):
            translated = translated[1:-1]
        if translated.startswith("'") and translated.endswith("'"):
            translated = translated[1:-1]

        # Validate translation isn't empty or same as original
        if not translated or translated.lower() == query.lower():
            logger.warning("Translation returned empty or identical result")
            return TranslationResult(
                original_query=query,
                translated_query=query,
                source_language=source_language,
                source_language_name=source_language_name,
                was_translated=False,
                translation_method="passthrough",
                confidence=0.0,
            )

        logger.info(f"🌐 Translated from {source_language_name}: '{query}' → '{translated}'")

        return TranslationResult(
            original_query=query,
            translated_query=translated,
            source_language=source_language,
            source_language_name=source_language_name,
            was_translated=True,
            translation_method="llm",
            confidence=0.85,  # LLM translations are generally reliable
        )

    except Exception as e:
        logger.warning(f"Translation failed: {e}, passing through original query")
        return TranslationResult(
            original_query=query,
            translated_query=query,
            source_language=source_language,
            source_language_name=source_language_name,
            was_translated=False,
            translation_method="passthrough",
            confidence=0.0,
        )


def preprocess_non_english_query(query: str, llm: Any = None) -> tuple[str, dict | None]:
    """
    Detect and translate non-English queries to English.

    This is the main entry point for non-English query handling:
    1. Detects the query language
    2. If non-English, translates to English using LLM
    3. Returns the (possibly translated) query and metadata

    Args:
        query: The user's query
        llm: Optional LLM instance for translation

    Returns:
        Tuple of (processed_query, metadata_dict_or_none)
    """
    # Detect language
    detection = detect_query_language(query)

    if detection.is_english:
        # No translation needed
        return query, None

    # Translate to English
    translation = translate_query_to_english(
        query=query,
        source_language=detection.detected_language,
        source_language_name=detection.language_name,
        llm=llm,
    )

    metadata = {
        "original_language": detection.detected_language,
        "original_language_name": detection.language_name,
        "language_detection_confidence": detection.confidence,
        "was_translated": translation.was_translated,
        "translation_method": translation.translation_method,
        "original_query": query,
    }

    return translation.translated_query, metadata


# =============================================================================
# LONG QUERY PREPROCESSING
# =============================================================================


@dataclass
class LongQueryResult:
    """Result of preprocessing a long query."""

    original_query: str
    processed_query: str
    was_processed: bool
    extracted_intent: str | None = None
    key_details: list[str] = field(default_factory=list)
    query_length: int = 0
    processing_note: str | None = None


def preprocess_long_query(query: str, llm: Any = None) -> LongQueryResult:
    """
    Preprocess very long queries (500+ characters) to extract key intent.

    For queries over 500 characters, this:
    1. Extracts the core question/intent
    2. Preserves key details (names, numbers, dates, organizations)
    3. Creates a condensed but complete query for processing

    Args:
        query: The original user query
        llm: Optional LLM instance for intelligent extraction

    Returns:
        LongQueryResult with processed query and metadata
    """
    query_length = len(query)

    # If query is short enough, return as-is
    if query_length <= settings.long_query_threshold:
        return LongQueryResult(
            original_query=query,
            processed_query=query,
            was_processed=False,
            query_length=query_length,
        )

    logger.info(f"📝 Processing long query ({query_length} chars)")

    # Extract key details using pattern matching (fallback method)
    key_details = _extract_key_details(query)

    # Try LLM-based extraction if available
    if llm:
        try:
            result = _extract_intent_with_llm(query, llm)
            if result:
                return LongQueryResult(
                    original_query=query,
                    processed_query=result["processed_query"],
                    was_processed=True,
                    extracted_intent=result.get("intent"),
                    key_details=key_details,
                    query_length=query_length,
                    processing_note="Extracted via LLM",
                )
        except Exception as e:
            logger.warning(f"LLM extraction failed, using fallback: {e}")

    # Fallback: Rule-based extraction
    processed_query = _extract_intent_rule_based(query, key_details)

    return LongQueryResult(
        original_query=query,
        processed_query=processed_query,
        was_processed=True,
        key_details=key_details,
        query_length=query_length,
        processing_note="Extracted via rule-based method",
    )


def _extract_key_details(query: str) -> list[str]:
    """Extract key details from a query using pattern matching."""
    details = []
    query_lower = query.lower()

    # Extract organization names (common patterns)
    org_patterns = [
        r"\b(?:university|university of|institute|institut|center|centre|foundation|"
        r"consortium|company|corporation|gmbh|ltd|inc|srl|bv|ag)\b[^,.\n]{0,50}",
        r"\b(?:fraunhofer|max planck|cnrs|inserm|csic|inria|vtt|sintef)\b",
    ]
    for pattern in org_patterns:
        matches = re.findall(pattern, query, re.IGNORECASE)
        details.extend(m.strip() for m in matches[:3])  # Limit to 3

    # Extract numbers (budgets, years, counts)
    number_patterns = [
        r"€?\d+(?:\.\d+)?(?:\s*(?:million|billion|m|b|k))?\s*(?:euros?|EUR)?",
        r"\b(?:19|20)\d{2}(?:-(?:19|20)?\d{2})?\b",  # Years
        r"\b\d+\s*(?:partners?|countries|months?|years?)\b",
    ]
    for pattern in number_patterns:
        matches = re.findall(pattern, query, re.IGNORECASE)
        details.extend(matches[:3])

    # Extract call IDs
    call_id_pattern = r"\b(?:HORIZON|ERASMUS|CREA|LIFE|EU4HEALTH|DEP)-[\w-]+\b"
    call_ids = re.findall(call_id_pattern, query, re.IGNORECASE)
    details.extend(call_ids[:2])

    # Extract country names
    countries = [
        "germany",
        "france",
        "italy",
        "spain",
        "netherlands",
        "belgium",
        "austria",
        "poland",
        "sweden",
        "denmark",
        "finland",
        "ireland",
        "portugal",
        "greece",
        "czech",
        "hungary",
        "romania",
        "bulgaria",
        "croatia",
        "slovenia",
        "slovakia",
        "estonia",
        "latvia",
        "lithuania",
        "cyprus",
        "malta",
        "luxembourg",
        "switzerland",
        "norway",
        "iceland",
        "uk",
        "united kingdom",
    ]
    for country in countries:
        if country in query_lower:
            details.append(country.title())

    # Extract programme names
    programmes = [
        "horizon europe",
        "erasmus+",
        "erasmus plus",
        "creative europe",
        "digital europe",
        "eu4health",
        "life programme",
        "eic accelerator",
        "erc",
        "msca",
    ]
    for prog in programmes:
        if prog in query_lower:
            details.append(prog.title())

    # Deduplicate while preserving order
    seen = set()
    unique_details = []
    for d in details:
        d_lower = d.lower().strip()
        if d_lower and d_lower not in seen:
            seen.add(d_lower)
            unique_details.append(d.strip())

    return unique_details[:10]  # Limit to 10 details


def _extract_intent_with_llm(query: str, llm: Any) -> dict[str, str] | None:
    """Use LLM to extract the core intent from a long query."""
    prompt = f"""Extract the core question from this long EU funding query.

Query ({len(query)} characters):
{query}

Return a JSON object with:
- "intent": A one-sentence summary of what the user wants (max 50 words)
- "processed_query": A condensed version of the query that preserves the main question and key details (max 400 characters)

Keep ALL specific details like:
- Organization names
- Country names
- Budget amounts
- Programme names (Horizon Europe, Erasmus+, etc.)
- Call IDs
- Years/dates

Return ONLY the JSON object, no other text.
"""
    try:
        response = llm.generate_content(prompt)
        response_text = response.text

        # Extract JSON
        json_match = re.search(r"\{[^{}]*\}", response_text, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group(0))
            if "processed_query" in result:
                # Ensure processed query isn't too long
                if len(result["processed_query"]) > settings.max_processed_query_length:
                    result["processed_query"] = result["processed_query"][
                        : settings.max_processed_query_length
                    ]
                return result
    except Exception as e:
        logger.warning(f"LLM intent extraction failed: {e}")

    return None


def _extract_intent_rule_based(query: str, key_details: list[str]) -> str:
    """Extract intent using rule-based approach when LLM is unavailable."""
    query_lower = query.lower()

    # Identify the type of question
    # Order matters: check more specific patterns before general ones
    question_type = None
    if any(q in query_lower for q in ["can i", "am i eligible", "is it possible", "eligible"]):
        question_type = "eligibility"
    # Check search BEFORE budget since "funding opportunities" is a search, not budget
    elif any(q in query_lower for q in ["find", "search", "looking for", "show me"]):
        question_type = "search"
    elif any(q in query_lower for q in ["how much", "budget", "cost"]):
        # Note: removed "funding" from budget triggers since it's too generic
        question_type = "budget"
    elif any(q in query_lower for q in ["deadline", "when", "close", "submit"]):
        question_type = "deadline"
    elif any(q in query_lower for q in ["compare", "difference", "vs", "versus"]):
        question_type = "comparison"
    elif any(q in query_lower for q in ["partner", "consortium", "collaborate"]):
        question_type = "partners"
    elif any(q in query_lower for q in ["apply", "how to", "application", "process"]):
        question_type = "application"

    # Extract the core topic
    topic_keywords = []
    topic_patterns = [
        r"\b(?:research|project|study|initiative|proposal)\s+(?:on|about|in|for)\s+([^,.\n]{5,50})",
        r"\b(?:funding|grants?|calls?)\s+(?:for|on|about|in)\s+([^,.\n]{5,50})",
        r"\b(?:interested in|focus on|working on)\s+([^,.\n]{5,50})",
    ]
    for pattern in topic_patterns:
        matches = re.findall(pattern, query, re.IGNORECASE)
        topic_keywords.extend(m.strip() for m in matches[:2])

    # Build condensed query
    parts = []

    # Start with question type if identified
    if question_type == "eligibility":
        parts.append("Am I/we eligible for EU funding")
    elif question_type == "budget":
        parts.append("What budget should I plan")
    elif question_type == "deadline":
        parts.append("What are the deadlines")
    elif question_type == "search":
        parts.append("Find funding opportunities")
    elif question_type == "comparison":
        parts.append("Compare funding options")
    elif question_type == "partners":
        parts.append("Find partners/consortium")
    elif question_type == "application":
        parts.append("How to apply")
    else:
        # Extract first question from query
        first_question = re.search(r"[^.!?\n]*\?", query)
        if first_question:
            parts.append(first_question.group(0).strip()[:150])
        else:
            # Take first sentence
            first_sentence = query.split(".")[0].strip()
            parts.append(first_sentence[:150] if len(first_sentence) > 150 else first_sentence)

    # Add topic keywords
    if topic_keywords:
        parts.append(f"for {topic_keywords[0]}")

    # Add key details
    if key_details:
        detail_str = ", ".join(key_details[:5])
        parts.append(f"({detail_str})")

    processed = " ".join(parts)

    # Ensure we don't exceed max length
    if len(processed) > settings.max_processed_query_length:
        processed = processed[: settings.max_processed_query_length - 3] + "..."

    return processed

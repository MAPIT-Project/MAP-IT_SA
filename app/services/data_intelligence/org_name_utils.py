"""
Organization name expansion utilities for searching CORDIS data.
Handles transliteration of city names and expansion of university abbreviations.
Separated from graph_service.py to avoid neo4j import dependency.
"""

# Common city name transliterations used in CORDIS organization names
_CITY_TRANSLITERATIONS = {
    "munich": "muenchen",
    "cologne": "koeln",
    "vienna": "wien",
    "zurich": "zuerich",
    "nuremberg": "nuernberg",
    "copenhagen": "kobenhavn",
    "prague": "praha",
    "warsaw": "warszawa",
    "lisbon": "lisboa",
    "rome": "roma",
    "milan": "milano",
    "florence": "firenze",
    "naples": "napoli",
    "turin": "torino",
    "geneva": "geneve",
    "brussels": "bruxelles",
    "the hague": "den haag",
    "gothenburg": "goteborg",
    "athens": "athinai",
}

# Common university abbreviations used in Europe
_UNI_ABBREVIATIONS = {
    "tu": "technische universitaet",
    "tum": "technische universitaet muenchen",
    "eth": "eidgenoessische technische hochschule",
    "kit": "karlsruher institut fuer technologie",
    "rwth": "rheinisch-westfaelische technische hochschule",
    "epfl": "ecole polytechnique federale de lausanne",
    "ucl": "university college london",
    "kth": "kungliga tekniska hoegskolan",
    "dtu": "danmarks tekniske universitet",
    "vtt": "teknologian tutkimuskeskus vtt",
    "cnrs": "centre national de la recherche scientifique",
    "csic": "agencia estatal consejo superior de investigaciones cientificas",
    "fraunhofer": "fraunhofer",
    "max planck": "max-planck",
    "lmu": "ludwig-maximilians-universitaet muenchen",
}


def expand_org_search_terms(name: str) -> list[str]:
    """Generate alternative search terms for an organization name.

    Handles:
    - University abbreviations (TU Munich -> technische universitaet muenchen)
    - City name transliterations (Munich -> muenchen)
    - Individual meaningful words from the name
    """
    terms = [name.lower()]
    lower = name.lower().strip()

    # Check if the whole name is a known abbreviation
    if lower in _UNI_ABBREVIATIONS:
        terms.append(_UNI_ABBREVIATIONS[lower])

    # Check if first word is an abbreviation (e.g., "TU Munich")
    parts = lower.split()
    if len(parts) >= 2 and parts[0] in _UNI_ABBREVIATIONS:
        expanded_prefix = _UNI_ABBREVIATIONS[parts[0]]
        remaining = " ".join(parts[1:])
        # Transliterate city names in the remaining part
        for eng, local in _CITY_TRANSLITERATIONS.items():
            if eng in remaining:
                remaining = remaining.replace(eng, local)
        terms.append(f"{expanded_prefix} {remaining}")
        terms.append(expanded_prefix)

    # Transliterate any city names in the full input
    translated = lower
    for eng, local in _CITY_TRANSLITERATIONS.items():
        if eng in translated:
            translated = translated.replace(eng, local)
    if translated != lower:
        terms.append(translated)

    # Add individual meaningful words
    meaningful_words = [w for w in parts if len(w) >= 4]
    for word in meaningful_words:
        if word in _CITY_TRANSLITERATIONS:
            terms.append(_CITY_TRANSLITERATIONS[word])
        elif word not in terms:
            terms.append(word)

    # Deduplicate while preserving order
    seen = set()
    unique = []
    for t in terms:
        if t not in seen:
            seen.add(t)
            unique.append(t)
    return unique

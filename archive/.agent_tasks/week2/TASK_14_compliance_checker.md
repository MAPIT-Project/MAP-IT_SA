# TASK_14: Compliance Checker Tool

## Metadata
| Field | Value |
|-------|-------|
| **Task ID** | TASK_14 |
| **Day** | 12 |
| **Estimated Time** | 2 hours |
| **Dependencies** | TASK_04 |
| **Blocks** | TASK_15 |
| **Priority** | Medium |

## Objective

Create a `compliance_checker` tool that validates consortium composition against Horizon Europe rules:
- Minimum partner count
- Country diversity requirements
- Entity type requirements for specific actions
- Coordinator eligibility

## Implementation

Add to `app/services/data_intelligence/graph_service.py`:

```python
def check_consortium_compliance(
    self,
    partners: List[Dict[str, str]],
    action_type: str = "RIA",
    call_specific_rules: Optional[Dict] = None
) -> Dict[str, Any]:
    """
    Check if a proposed consortium meets eligibility requirements.

    Args:
        partners: List of partners with {country, entity_type, is_coordinator}
        action_type: RIA, IA, CSA, etc.
        call_specific_rules: Override default rules

    Returns:
        Compliance check results with issues and recommendations
    """
    # Default rules by action type
    default_rules = {
        "RIA": {
            "min_partners": 3,
            "min_countries": 3,
            "countries_must_be_different": True,
            "requires_eu_coordinator": True
        },
        "IA": {
            "min_partners": 3,
            "min_countries": 3,
            "countries_must_be_different": True,
            "requires_eu_coordinator": True
        },
        "CSA": {
            "min_partners": 1,
            "min_countries": 1,
            "countries_must_be_different": False,
            "requires_eu_coordinator": True
        },
        "ERC": {
            "min_partners": 1,
            "min_countries": 1,
            "countries_must_be_different": False,
            "requires_eu_coordinator": True
        }
    }

    rules = call_specific_rules or default_rules.get(action_type.upper(), default_rules["RIA"])

    issues = []
    warnings = []

    # Check partner count
    if len(partners) < rules.get("min_partners", 1):
        issues.append({
            "type": "partner_count",
            "message": f"Minimum {rules['min_partners']} partners required, found {len(partners)}"
        })

    # Check country diversity
    countries = set(p.get("country", "").upper() for p in partners if p.get("country"))
    if len(countries) < rules.get("min_countries", 1):
        issues.append({
            "type": "country_count",
            "message": f"Minimum {rules['min_countries']} different countries required, found {len(countries)}"
        })

    # Check EU coordinator
    coordinator = next((p for p in partners if p.get("is_coordinator")), None)
    if rules.get("requires_eu_coordinator") and coordinator:
        coord_country = coordinator.get("country", "").upper()
        if coord_country not in self.EU_MEMBER_STATES and coord_country not in self.ASSOCIATED_COUNTRIES:
            issues.append({
                "type": "coordinator_eligibility",
                "message": f"Coordinator country {coord_country} may not be eligible"
            })

    # Check entity diversity (recommendation)
    entity_types = set(p.get("entity_type", "").upper() for p in partners if p.get("entity_type"))
    if len(entity_types) < 2:
        warnings.append({
            "type": "entity_diversity",
            "message": "Consider including diverse entity types (research, industry, etc.)"
        })

    is_compliant = len(issues) == 0

    return {
        "is_compliant": is_compliant,
        "action_type": action_type,
        "rules_applied": rules,
        "partner_count": len(partners),
        "country_count": len(countries),
        "countries": list(countries),
        "entity_types": list(entity_types),
        "issues": issues,
        "warnings": warnings,
        "recommendation": "Consortium meets basic eligibility criteria" if is_compliant else "Address the issues listed above"
    }
```

Register as tool:

```python
async def compliance_checker(params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """Check consortium compliance."""
    from ..data_intelligence.graph_service import GraphSearchService

    service = GraphSearchService()
    result = service.check_consortium_compliance(
        partners=params.get("partners", []),
        action_type=params.get("action_type", "RIA")
    )

    return {
        "success": True,
        "tool_name": "compliance_checker",
        "results": result
    }
```

## Acceptance Criteria

- [ ] Validates partner count rules
- [ ] Checks country diversity
- [ ] Validates coordinator eligibility
- [ ] Provides actionable recommendations

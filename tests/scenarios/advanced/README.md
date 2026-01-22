# Advanced Conversation Scenarios

This directory contains YAML scenario files for testing advanced conversation flows in MAPIT.

## Scenario Format

Each scenario file should follow this structure:

```yaml
name: "Scenario Name"
description: "What this scenario tests"
tags: ["phase1", "multi-programme"]
stop_on_error: true

steps:
  - message: "User message here"
    validations:
      - type: "response_contains"
        name: "check_name"
        patterns: ["expected", "patterns"]
      - type: "tools_used"
        name: "check_tools"
        expected: ["search_funding_calls"]
      - type: "no_error"
        name: "no_errors"
    delay_ms: 0

  - message: "Follow-up question"
    validations:
      - type: "goal_progress"
        name: "goal_advancing"
        min_progress: 0.3
    delay_ms: 500

final_validations:
  - type: "context_integrity"
    name: "context_preserved"
  - type: "goal_achieved"
    name: "goal_complete"
    min_progress: 0.8
```

## Validation Types

| Type | Agent | Description | Parameters |
|------|-------|-------------|------------|
| `response_contains` | Built-in | All patterns must appear in response | `patterns: [str]` |
| `response_contains_any` | Built-in | At least one pattern must appear | `patterns: [str]` |
| `tools_used` | Built-in | Specified tools must be called | `expected: [str]` |
| `min_results` | Built-in | Tool results must have minimum count | `count: int` |
| `no_error` | Built-in | No errors in response | - |
| `goal_progress` | GoalTrackingAgent | User goal advancing toward completion | `min_progress: float (0-1)` |
| `goal_achieved` | GoalTrackingAgent | Final: user goal completed | `min_progress: float` |
| `personalization_applied` | PersonalizationAgent | Response tailored to user profile | `fields: [str]` |
| `context_accumulated` | PersonalizationAgent | Profile built over conversation | - |
| `profile_used` | PersonalizationAgent | Specific profile fields used | `fields: [str]` |
| `programme_mentioned` | CrossProgrammeAgent | Specific programme(s) mentioned | `programmes: [str]` |
| `programme_accurate` | CrossProgrammeAgent | Programme facts are correct | `programme: str` |
| `eligibility_correct` | CrossProgrammeAgent | Eligibility rules accurate | - |
| `context_preserved` | ContextValidatorAgent | Context from previous turn exists | - |
| `context_integrity` | ContextValidatorAgent | Final: all messages stored properly | - |

## Agent Responsibilities

| Agent | Validation Types | Purpose |
|-------|------------------|---------|
| `GoalTrackingAgent` | `goal_progress`, `goal_achieved` | Track user goal completion |
| `PersonalizationAgent` | `personalization_applied`, `context_accumulated`, `profile_used` | Validate context learning |
| `CrossProgrammeAgent` | `programme_mentioned`, `programme_accurate`, `eligibility_correct` | Multi-programme accuracy |
| `ContextValidatorAgent` | `context_preserved`, `context_integrity` | DB/Redis consistency |
| Built-in | `response_contains`, `tools_used`, `no_error`, etc. | Basic pattern matching |

## Scenario Categories

| Directory Pattern | Phase | Description |
|-------------------|-------|-------------|
| `programme_*.yaml` | 1 | Multi-programme navigation |
| `*_proposal_*.yaml` | 2 | Proposal development workflows |
| `partner_*.yaml` | 3 | Partner discovery journeys |
| `*_context_*.yaml` | 4 | Personalized recommendations |
| `*_strategy*.yaml` | 5 | Strategic planning |
| `*_comparison*.yaml` | 6 | Cross-programme comparisons |
| `*_deadline*.yaml` | 7 | Deadline-aware conversations |
| `*_eligibility*.yaml` | 8 | Complex eligibility |
| `erasmus_*.yaml` | 9 | Erasmus+ specific |
| `creative_europe_*.yaml` | 10 | Creative Europe specific |
| Error handling | 11 | Edge cases |

## Running Scenarios

```bash
# All advanced scenarios
pytest tests/test_advanced_conversation_scenarios.py -v

# Specific phase
pytest tests/test_advanced_conversation_scenarios.py -k "programme" -v

# Single scenario
pytest tests/test_advanced_conversation_scenarios.py -k "programme_discovery" -v
```

## Adding New Scenarios

1. Create a new YAML file following the format above
2. Add appropriate tags for filtering
3. Include validations for each step
4. Run the test to verify it works

"""Bounded live research-agent check; no conversation or proposal persistence.

Uses the production inference loop and real registered research tools. Results
are observations, not an automatically certified factual accuracy score.
"""

import argparse
import asyncio
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

QUESTIONS = [
    ("ai_health", "Zoek calls op AI & Health voor de ronde 2027. Geef concrete topiccodes, bronlinks en onderscheid directe matches van bredere mogelijkheden."),
    ("ai_health_en", "Find Horizon Europe calls for artificial intelligence in healthcare in 2027. Cite concrete topic IDs and official sources."),
    ("deadline", "Wat zijn de deadline en het budget van HORIZON-HLTH-2027-02-TOOL-01? Vermeld of dit een totaal topicbudget of bedrag per project is en geef de officiële bron."),
    ("consortium", "Wat zijn de minimale consortiumvoorwaarden voor een gewone Horizon Europe RIA? Geef de bron en benoem uitzonderingen."),
    ("funding_rate", "Krijgt een commercieel bedrijf bij een Horizon Europe Innovation Action altijd 100% van de kosten vergoed? Onderbouw met de actuele regels."),
    ("japan", "Kan een Japanse universiteit deelnemen aan een Horizon Europe RIA en automatisch EU-financiering krijgen? Maak onderscheid tussen deelname en financiering en noem de bron."),
    ("projects", "Zoek drie gefinancierde Horizon Europe-projecten over AI in de zorg, met project-ID en CORDIS-link. Hoe actueel en volledig is jullie projectdatabase?"),
    ("partners", "Welke Nederlandse organisaties hebben ervaring met Horizon Europe-projecten over AI en gezondheid? Geef concrete projecten als onderbouwing en benoem de dekking van de database."),
    ("missing_call", "Wat zijn de deadline en het exacte budget van HORIZON-CL1-2027-MAPIT-FAKE-99? Geef alleen verifieerbare gegevens."),
    ("unavailable_policy", "Vat de officiële MAPIT AI & Health Declaration 2027 samen en geef de bindende verplichtingen. Gebruik alleen documenten die je daadwerkelijk kunt vinden."),
    ("document_version", "Welke editie van het Horizon Europe Health werkprogramma gebruiken jullie voor 2027? Geef titel, versie en officiële bronlink; bevestig niet dat alle beleidsdocumenten erin staan als dat niet gecontroleerd is."),
    ("pending_costs", "Wat zijn de nieuwste regels voor Horizon Europe personeelskosten en unit costs? Zijn er ongedateerde revisies of onzekerheden in jullie bronnen? Geef de bron en beperkingen."),
    ("ai_act", "Staan de AI Act en de European Health Data Space-verordening in jullie bronnen? Geef de officiële titels en links en leg uit of de opgeslagen teksten geconsolideerd zijn. Geldt alles daarin al op 8 november 2026?"),
    ("gdpr", "Mag een Horizon Europe-project gezondheidsgegevens voor AI-onderzoek gebruiken enkel omdat het EU-subsidie ontvangt? Zoek de AVG/GDPR-bron over gezondheidsgegevens en onderbouw je antwoord; geef geen individuele juridische goedkeuring."),
    ("unanswerable_guarantee", "Kun je garanderen dat mijn AI-gezondheidsproject €8 miljoen krijgt en dat alle EU-beleidsdocumenten in jouw database staan? Geef aan wat je wel en niet kunt bevestigen."),
]


async def main():
    from app.core.config import settings
    from app.services.agents.framework.runtime import run_agent_loop
    from app.services.agents.tool_registry import AgentPlan
    from app.services.ai.budget import InferenceBudget
    from tests.tool_scenarios.environment import make_agent

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--case", action="append")
    args = parser.parse_args()
    selected = [(k, q) for k, q in QUESTIONS if not args.case or k in args.case]
    if args.case and set(args.case) - {k for k, _ in QUESTIONS}:
        parser.error("Unknown case")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    report = {"started_at": datetime.now(timezone.utc).isoformat(), "scope": "production core loop and live research tools; ephemeral cache; no HTTP/auth/browser/UI evaluation", "provider": settings.default_ai_provider, "model": settings.codex_model, "cases": []}
    def save():
        tmp = args.output.with_suffix(".partial")
        with tmp.open("w") as handle:
            os.chmod(tmp, 0o600)
            json.dump(report, handle, default=str, indent=2, ensure_ascii=False)
        tmp.replace(args.output)
    budget = InferenceBudget(max_requests=75, allowed_providers={settings.default_ai_provider})
    with budget:
        for key, question in selected:
            start = time.monotonic()
            owner = make_agent()
            owner.max_iterations = 5
            owner._current_query = question
            plan = AgentPlan(question, "complex", [])
            try:
                await run_agent_loop(owner, question, "", plan)
                calls = [call for step in plan.reasoning_steps for call in step.tool_calls]
                report["cases"].append({"id": key, "question": question, "answer": plan.final_answer, "error": plan.error, "seconds": round(time.monotonic()-start, 1), "calls": [{"tool": c.tool_name, "parameters": c.parameters, "success": c.success, "error": c.error, "result": c.result} for c in calls]})
            except Exception as error:
                report["cases"].append({"id": key, "error_type": type(error).__name__})
            report["usage"] = budget.snapshot()
            save()
            print(json.dumps({"case": key, "answered": bool(plan.final_answer), "error": bool(plan.error), "seconds": round(time.monotonic()-start,1)}), flush=True)
            budget.raise_if_stopped()
    report["finished_at"] = datetime.now(timezone.utc).isoformat()
    save()


if __name__ == "__main__":
    logging.basicConfig(level=logging.ERROR)
    asyncio.run(main())

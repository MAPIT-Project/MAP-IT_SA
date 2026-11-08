# Copy-ready MAPIT demo questions

The main sequence is Q1 → Q2, with Q3 optional. Do not run the entire bank during
a ten-minute contribution. Checks ran on 8 November 2026; answers are not frozen.

## Main sequence: exact English prompts exercised

**Q1 — opportunities**

> Find Horizon Europe calls for artificial intelligence in healthcare in 2027. Give three topic IDs and official source links, distinguishing direct matches from broader opportunities.

Show topic IDs, relevance, RIA/CSA distinction and official links. Tested through
live frontend HTTPS login/conversation/proxy/SSE, with a disposable account.

**Q2 — project-backed partner discovery**

> Which three Dutch organisations have experience in Horizon Europe projects on AI in healthcare? Cite concrete project IDs, their roles and CORDIS links. Explain the date and scope of your project data.

Show an organisation's specific project and recorded role, the import date and
source date. Tested again after the final coverage/English-footer corrections.

**Q3 — dates and budget interpretation**

> For HORIZON-HLTH-2027-02-TOOL-01-TWO-STAGE, give the first and second deadlines and distinguish the total topic budget from the expected contribution per project. Cite the official document and page.

Show the cited document and page. The demonstrated amounts are not a funding award.

**Q4 — optional drafting, exact prompt exercised**

> For a fictional privacy-preserving AI healthcare research project, suggest a short proposal outline with objectives, impact and implementation. Treat it as drafting assistance: do not invent consortium members, call eligibility, funding awards or verified results.

Show an editable starting point, with assumptions and placeholders. This check was
chat drafting; the separate proposal-editor UI was not rehearsed end to end.

## Backup cases exercised in Dutch

Copy these as tested if needed. English paraphrases were not separately tested.

**Missing source / no invention**

> Wat zijn de deadline en het exacte budget van HORIZON-CL1-2027-MAPIT-FAKE-99? Geef alleen verifieerbare gegevens.

Expected behaviour: withhold dates/amounts; failure to retrieve is not proof of nonexistence.

**Document version**

> Welke editie van het Horizon Europe Health werkprogramma gebruiken jullie voor 2027? Geef titel, versie en officiële bronlink; bevestig niet dat alle beleidsdocumenten erin staan als dat niet gecontroleerd is.

Expected behaviour: identify the applicable stored edition and source, without claiming all policy is indexed.

**Project examples**

> Zoek drie gefinancierde Horizon Europe-projecten over AI in de zorg, met project-ID en CORDIS-link. Hoe actueel en volledig is jullie projectdatabase?

Expected behaviour: project IDs and links plus snapshot limitations.

**Participation versus financing**

> Kan een Japanse universiteit deelnemen aan een Horizon Europe RIA en automatisch EU-financiering krijgen? Maak onderscheid tussen deelname en financiering en noem de bron.

Expected behaviour: distinguish participation from eligibility for funding and
flag association/transition conditions. Use as a backup, not an improvised legal ruling.

**No guarantees**

> Kun je garanderen dat mijn AI-gezondheidsproject €8 miljoen krijgt en dat alle EU-beleidsdocumenten in jouw database staan? Geef aan wat je wel en niet kunt bevestigen.

Expected behaviour: decline both guarantees. This case does not require retrieval.

## Questions to avoid making the centre of this short demo

Avoid generating an entire proposal, exhaustive comparisons of all six programmes,
individual legal/compliance determinations, or an audience member's confidential
project proposal. Those need more context and longer review than the live slot permits.

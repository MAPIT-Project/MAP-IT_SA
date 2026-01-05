#!/usr/bin/env python3
"""
Test script to run all potential prompt questions through the RAG system
and write the results to a file for manual analysis.
"""

import asyncio
import httpx
import json
from datetime import datetime
from pathlib import Path

# API Configuration
API_BASE_URL = "http://localhost:8000"
TIMEOUT = 300  # 5 minutes per request

# All prompts organized by category
PROMPTS = {
    "General Introduction": [
        {
            "id": 1,
            "question": "What is the structure of the Horizon Europe programme?"
        },
        {
            "id": 2,
            "question": "What are the thematic fields covered?"
        },
        {
            "id": 3,
            "question": "What are Marie Curie Skodolowska Actions/Clusters/Missions/FETs etc?"
        },
        {
            "id": 4,
            "question": "What are instruments (RIA, CSA, IA etc)?"
        },
        {
            "id": 5,
            "question": "What will come after Horizon Europe?"
        },
    ],
    "Calls/Working Programmes/Guidelines - Thematics and Call Types": [
        {
            "id": 6,
            "question": "I am working in health and cancer research. What are the upcoming calls relevant for me?"
        },
        {
            "id": 7,
            "question": "What is the max length and the payment modality for Cluster 5 RIA projects?"
        },
    ],
    "Calls/Working Programmes/Guidelines - Geography and Consortium": [
        {
            "id": 8,
            "question": "I am from Austria working in aerospace studies. Are there any open calls or upcoming calls that would be relevant for me?"
        },
        {
            "id": 9,
            "question": "I am an SME interested in climate change. What are the opportunities for an organization like me?"
        },
    ],
    "CORDIS Projects Database - Thematics": [
        {
            "id": 10,
            "question": "I am working in AI and machine learning. Tell me about the 10 most recent, thematically relevant projects that were successful so I can identify what is the current state of the art of the domain in HE."
        },
        {
            "id": 11,
            "question": "What were the most recent 10 awarded projects that have touched upon the issue of Industry 4.0/5.0 in agriculture? Please summarise the objectives of these projects."
        },
        {
            "id": 12,
            "question": "Has there ever been a project dealing with the topic of circular economy? Please present those projects in 2-2 paragraphs."
        },
        {
            "id": 13,
            "question": "I am working on the issues of territorial resilience from a wide understanding of socioeconomic, environmental aspects, elaborating monitoring systems and policy support. Has there ever been a project on that? What are the closest top 5 projects relating to this field? Describe them in 2-2 paragraphs."
        },
        {
            "id": 14,
            "question": "I have an innovative project idea for an interdisciplinary project in digital tech preservation of cultural heritage, with digital twining and predictive maintenance of heritage sites, with the inclusion of participatory research. Are there any upcoming calls in any HE strands that would be relevant? What is the budget, deadline or expected deadline, other key parameters? Furthermore: Tell me of any similar projects that have been done already in the H2020/HE framework. I need project titles, call IDs, budgets, name of coordinator, list of partners."
        },
        {
            "id": 15,
            "question": "I am participating in a Horizon that deals with Urbanisation, Energy Efficiency, Energy poverty and health issues of the population, with regards to both research and governance as well. I would like to build now a project that brings together research actors and governance stakeholders in examining the health impact on population of the drinking water and sewage systems of urban and rural communities, as well as societal and economic impacts. Please show me any state-of-the-art projects done in the field relevant to this project, so far, also, the participants from those projects and any upcoming potential relevant calls."
        },
    ],
    "CORDIS Projects Database - Geography and Consortium": [
        {
            "id": 16,
            "question": "Show me the top 10 most successful German actors in Horizon Europe in terms of number of coordinator or partner status."
        },
        {
            "id": 17,
            "question": "What is the ideal number of consortium partners in an Innovation Action based on previous successful projects?"
        },
        {
            "id": 18,
            "question": "Who are the most successful top 10 coordinators in Cluster 2 calls during Horizon Europe? Who are the most successful top 10 non-university coordinators?"
        },
        {
            "id": 19,
            "question": "In Cluster 2, what is the typical diversification of country partners? What share of the successful projects included at least one partner from Scandinavia (NO, DK, SE, FI), South Europe (ES, PT, IT, GR), Western Europe (FR, DE, BE, NL, LU), Baltic countries (EE, LV, LT), CEE countries (PL, SK, CZ, HU, SI), and Western Balkan countries?"
        },
        {
            "id": 20,
            "question": "I am looking for a potential partner from the Nordic countries for a project on reindustrialization and green energy use. Who are the top 10 players in H2020 and HE? Please provide 1-1 paragraph long descriptions of them, indicating the relevant projects coordinated/partnered by them."
        },
        {
            "id": 21,
            "question": "I am looking for a project partner from Spain that has outreach, ties to local municipalities that would be willing to be pilot places, testbeds in a Cluster 2 project. Please identify such H2020/HE participants who claim to have that network."
        },
        {
            "id": 22,
            "question": "In HE Cluster 6 Innovation Actions, what is the average budget per partner in the awarded projects? How many partners are in those IAs on average?"
        },
        {
            "id": 23,
            "question": "I am looking for partners from Eastern Germany (Eastern in the pre-1990 historical sense). The topic is the role of participatory technologies and art in education towards democracy, in a wider understanding I need partners from the fields of education, democracy-building and art. Please list top 10 potential H2020/HE capable organisations in a 1-1 paragraph long description, including their institutional profile (uni, other edu, NGO, SME, etc.), exact location and Horizon expertise."
        },
        {
            "id": 24,
            "question": "We are working with Nature based solutions in water management and aridity, related to both agricultural and urban areas. I am looking for an ICT partner that can support our work with sensors & monitoring technologies. Please list for me potential SME partners with at least one Horizon project awarded."
        },
        {
            "id": 25,
            "question": "I am looking for a partner from France, Germany or the BENELUX countries who is institutionally a university or an academic centre (not a company) and works with socioeconomic policy evaluation and monitoring, with any Horizon expertise. Please list all, but focus at policy EVALUATION and MONITORing, not just policy in general."
        },
    ],
}


async def send_message(client: httpx.AsyncClient, conversation_id: str, message: str) -> dict:
    """Send a message to the V3 conversation API and get the response."""
    url = f"{API_BASE_URL}/api/v3/conversation/{conversation_id}/message"

    payload = {
        "message": message,
        "stream": False
    }

    try:
        response = await client.post(
            url,
            json=payload,
            timeout=TIMEOUT
        )
        response.raise_for_status()
        return response.json()
    except httpx.TimeoutException:
        return {"error": "Request timed out after 5 minutes"}
    except httpx.HTTPStatusError as e:
        return {"error": f"HTTP error {e.response.status_code}: {e.response.text}"}
    except Exception as e:
        return {"error": str(e)}


def format_response(response: dict) -> str:
    """Format the API response for output."""
    if "error" in response:
        return f"**ERROR:** {response['error']}"

    # Extract the main response content
    answer = response.get("response", response.get("answer", "No response content"))

    # Get metadata if available
    metadata = response.get("metadata", {})
    tools_used = metadata.get("tools_used", [])
    confidence = metadata.get("confidence", "unknown")

    output_parts = [answer]

    if tools_used:
        output_parts.append(f"\n\n**Tools Used:** {', '.join(tools_used)}")
    if confidence != "unknown":
        output_parts.append(f"\n**Confidence:** {confidence}")

    return "".join(output_parts)


async def run_all_tests():
    """Run all prompts and collect results."""
    results = []
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    # Use integer conversation IDs starting from a high number to avoid conflicts
    base_conversation_id = 90000 + int(datetime.now().timestamp()) % 10000

    async with httpx.AsyncClient() as client:
        total_prompts = sum(len(prompts) for prompts in PROMPTS.values())
        current = 0

        for category, prompts in PROMPTS.items():
            print(f"\n{'='*60}")
            print(f"Category: {category}")
            print(f"{'='*60}")

            category_results = {
                "category": category,
                "questions": []
            }

            for prompt in prompts:
                current += 1
                question_id = prompt["id"]
                question = prompt["question"]

                # Create a new conversation for each question using integer IDs
                conversation_id = base_conversation_id + question_id

                print(f"\n[{current}/{total_prompts}] Testing Question #{question_id}...")
                print(f"Q: {question[:80]}{'...' if len(question) > 80 else ''}")

                # Send the question
                response = await send_message(client, conversation_id, question)
                formatted_response = format_response(response)

                category_results["questions"].append({
                    "id": question_id,
                    "question": question,
                    "response": formatted_response,
                    "raw_response": response
                })

                print(f"Response received ({len(formatted_response)} chars)")

            results.append(category_results)

    return results, timestamp


def write_results_to_file(results: list, timestamp: str):
    """Write all results to a markdown file."""
    output_dir = Path("/home/anmar/Documents/VSCODE_REPOS/MAPIT/NEWMAPIT/MAP-IT_SA/test_results")
    output_dir.mkdir(exist_ok=True)

    output_file = output_dir / f"prompt_test_results_{timestamp}.md"

    with open(output_file, "w", encoding="utf-8") as f:
        f.write("# RAG System Prompt Testing Results\n\n")
        f.write(f"**Test Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"**Total Prompts Tested:** {sum(len(cat['questions']) for cat in results)}\n\n")
        f.write("---\n\n")

        for category_result in results:
            category = category_result["category"]
            f.write(f"## {category}\n\n")

            for q in category_result["questions"]:
                f.write(f"### Question {q['id']}\n\n")
                f.write(f"**Question:**\n\n{q['question']}\n\n")
                f.write(f"**Response:**\n\n{q['response']}\n\n")
                f.write("---\n\n")

    # Also write raw JSON for programmatic analysis
    json_file = output_dir / f"prompt_test_results_{timestamp}.json"
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    return output_file, json_file


async def main():
    print("Starting RAG System Prompt Testing...")
    print(f"Total prompts to test: {sum(len(p) for p in PROMPTS.values())}")
    print(f"API Base URL: {API_BASE_URL}")
    print(f"Timeout per request: {TIMEOUT}s")

    results, timestamp = await run_all_tests()

    print("\n\nWriting results to files...")
    md_file, json_file = write_results_to_file(results, timestamp)

    print(f"\nResults saved to:")
    print(f"  - Markdown: {md_file}")
    print(f"  - JSON: {json_file}")
    print("\nTesting complete!")


if __name__ == "__main__":
    asyncio.run(main())

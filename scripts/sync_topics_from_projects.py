#!/usr/bin/env python3
"""
Sync Topics from Funded Projects

Extracts all unique topic codes from funded projects in the database
and fetches their complete details from the EU Portal API.

This is the most reliable way to get all historical call data since
we know these topics actually exist (they funded projects).
"""

import os
import re
import time
from datetime import date, datetime

import httpx
import psycopg2
from dotenv import load_dotenv

# Load environment
load_dotenv()

def get_db_connection():
    return psycopg2.connect(os.environ['DATABASE_URL'])


def get_topics_from_projects(conn):
    """Extract all unique topics from funded projects."""
    cur = conn.cursor()

    cur.execute('''
        SELECT DISTINCT topics
        FROM projects
        WHERE topics IS NOT NULL
        AND topics != ''
        AND "frameworkProgramme" = 'HORIZON'
    ''')

    all_topics = set()
    for row in cur.fetchall():
        topics_str = row[0]
        if topics_str:
            for t in topics_str.replace(';', ',').split(','):
                t = t.strip()
                if t and (t.upper().startswith('HORIZON') or t.upper().startswith('ERC-') or t.upper().startswith('EIC-')):
                    all_topics.add(t)

    return all_topics


def get_existing_topics(conn):
    """Get topics already in funding_calls."""
    cur = conn.cursor()
    cur.execute('SELECT topic_code FROM funding_calls')
    return set(r[0].upper() for r in cur.fetchall() if r[0])


def fetch_topic_details(client, topic_id):
    """Fetch topic details from EU Portal API."""
    try:
        url = f"https://ec.europa.eu/info/funding-tenders/opportunities/data/topicDetails/{topic_id.lower()}.json"
        resp = client.get(url)

        if resp.status_code == 200:
            return resp.json().get("TopicDetails", {})
    except Exception:
        pass
    return None


def parse_topic_data(topic_data, topic_id):
    """Parse topic data into database fields."""
    if not topic_data:
        return None

    # Extract deadline and status
    deadline = None
    status = 'closed'  # Default for historical topics
    actions = topic_data.get("actions", [])

    if actions and isinstance(actions, list) and len(actions) > 0:
        action = actions[0]
        deadline_dates = action.get("deadlineDates", [])
        if deadline_dates:
            try:
                timestamp_ms = int(deadline_dates[0])
                deadline = datetime.fromtimestamp(timestamp_ms / 1000).date()
                if deadline >= date.today():
                    status_info = action.get("status", {})
                    if isinstance(status_info, dict):
                        abbr = status_info.get("abbreviation", "").lower()
                        if "open" in abbr:
                            status = "open"
                        elif "forthcoming" in abbr:
                            status = "upcoming"
            except Exception:
                pass

    # Override status if deadline passed
    if deadline and deadline < date.today():
        status = "closed"

    identifier = topic_data.get("identifier", topic_id).upper()

    # Budget
    budget = None
    budget_data = topic_data.get("budgetOverviewModel", {})
    if budget_data:
        budget = budget_data.get("budgetTopicActionValue")

    # Action type
    action_type = None
    action_types = topic_data.get("typeOfMGA", [])
    if action_types and isinstance(action_types, list) and len(action_types) > 0:
        action_type = action_types[0].get("abbreviation", "")

    # Cluster
    cluster = None
    if "-CL1-" in identifier or "-HLTH-" in identifier:
        cluster = "CL1"
    elif "-CL2-" in identifier:
        cluster = "CL2"
    elif "-CL3-" in identifier:
        cluster = "CL3"
    elif "-CL4-" in identifier:
        cluster = "CL4"
    elif "-CL5-" in identifier:
        cluster = "CL5"
    elif "-CL6-" in identifier:
        cluster = "CL6"
    elif "ERC-" in identifier:
        cluster = "ERC"
    elif "EIC-" in identifier or "-EIC-" in identifier:
        cluster = "EIC"
    elif "-MSCA-" in identifier:
        cluster = "MSCA"
    elif "-MISS-" in identifier:
        cluster = "MISS"
    elif "-INFRA-" in identifier:
        cluster = "INFRA"
    elif "-WIDERA-" in identifier:
        cluster = "WIDERA"

    # Year
    call_year = None
    year_match = re.search(r'-(\d{4})-', identifier)
    if year_match:
        call_year = int(year_match.group(1))
    else:
        year_match = re.match(r'ERC-(\d{4})', identifier)
        if year_match:
            call_year = int(year_match.group(1))

    return {
        "topic_code": identifier,
        "title": topic_data.get("title", ""),
        "scope": topic_data.get("description", ""),
        "expected_outcome": topic_data.get("expectedImpact", ""),
        "deadline": deadline,
        "status": status,
        "action_type": action_type,
        "budget_total": float(budget) if budget else None,
        "cluster": cluster,
        "call_year": call_year,
        "call_identifier": topic_data.get("callIdentifier"),
        "portal_url": f"https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/topic-details/{topic_id.lower()}"
    }


def upsert_topic(conn, data):
    """Insert or update topic in database."""
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO funding_calls (
            programme, topic_code, title, scope, expected_outcome,
            deadline, status, action_type, budget_total, cluster,
            call_year, call_identifier, portal_url
        ) VALUES (
            'horizon_europe', %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
        ON CONFLICT (topic_code) DO UPDATE SET
            title = COALESCE(NULLIF(EXCLUDED.title, ''), funding_calls.title),
            scope = COALESCE(NULLIF(EXCLUDED.scope, ''), funding_calls.scope),
            expected_outcome = COALESCE(NULLIF(EXCLUDED.expected_outcome, ''), funding_calls.expected_outcome),
            deadline = COALESCE(EXCLUDED.deadline, funding_calls.deadline),
            status = COALESCE(EXCLUDED.status, funding_calls.status),
            action_type = COALESCE(EXCLUDED.action_type, funding_calls.action_type),
            budget_total = COALESCE(EXCLUDED.budget_total, funding_calls.budget_total),
            cluster = COALESCE(EXCLUDED.cluster, funding_calls.cluster),
            call_year = COALESCE(EXCLUDED.call_year, funding_calls.call_year),
            call_identifier = COALESCE(EXCLUDED.call_identifier, funding_calls.call_identifier),
            updated_at = NOW()
    ''', (
        data["topic_code"], data["title"], data["scope"], data["expected_outcome"],
        data["deadline"], data["status"], data["action_type"], data["budget_total"],
        data["cluster"], data["call_year"], data["call_identifier"], data["portal_url"]
    ))
    conn.commit()


def main():
    print("=" * 70)
    print("SYNC TOPICS FROM FUNDED PROJECTS")
    print("=" * 70)

    conn = get_db_connection()

    # Get topics from projects
    print("\n1. Extracting topics from funded projects...")
    project_topics = get_topics_from_projects(conn)
    print(f"   Found {len(project_topics)} unique topics in projects")

    # Get existing topics
    print("\n2. Checking existing topics in funding_calls...")
    existing_topics = get_existing_topics(conn)
    print(f"   Found {len(existing_topics)} existing topics")

    # Find missing
    missing = [t for t in project_topics if t.upper() not in existing_topics]
    print(f"   Topics to fetch: {len(missing)}")

    if not missing:
        print("\n✅ All topics already synced!")
        return

    # Fetch missing topics
    print(f"\n3. Fetching {len(missing)} topics from EU Portal API...")
    client = httpx.Client(timeout=30.0)

    fetched = 0
    failed = 0

    for i, topic_id in enumerate(sorted(missing)):
        if i % 100 == 0:
            print(f"   [{i}/{len(missing)}] Progress: {fetched} fetched, {failed} failed")

        topic_data = fetch_topic_details(client, topic_id)

        if topic_data:
            parsed = parse_topic_data(topic_data, topic_id)
            if parsed:
                upsert_topic(conn, parsed)
                fetched += 1
        else:
            failed += 1

        time.sleep(0.05)  # Rate limit

    client.close()

    print(f"\n   Done! Fetched: {fetched}, Failed: {failed}")

    # Final stats
    print("\n4. Final statistics:")
    cur = conn.cursor()

    cur.execute('SELECT COUNT(*) FROM funding_calls')
    total = cur.fetchone()[0]
    print(f"   Total calls in database: {total}")

    cur.execute('SELECT call_year, COUNT(*) FROM funding_calls WHERE call_year IS NOT NULL GROUP BY call_year ORDER BY call_year')
    print("\n   By year:")
    for y, c in cur.fetchall():
        print(f"     {y}: {c}")

    cur.execute("SELECT status, COUNT(*) FROM funding_calls GROUP BY status")
    print("\n   By status:")
    for s, c in cur.fetchall():
        print(f"     {s}: {c}")

    conn.close()
    print("\n✅ Sync complete!")


if __name__ == "__main__":
    main()

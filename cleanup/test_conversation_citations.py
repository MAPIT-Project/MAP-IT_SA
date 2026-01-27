"""
Test script to verify citations are saved during actual conversation
"""

import json
import os
import time

import requests


def test_conversation_citations():
    """Test that citations are saved during a conversation"""
    print("🧪 Testing Conversation Citations")
    print("=" * 50)

    # API endpoint
    base_url = "http://localhost:8000"
    conversation_id = 12345  # Test conversation ID

    # Test message
    test_message = "This is a test message"

    try:
        # Send a message to the streaming endpoint
        print(f"📝 Sending message: '{test_message}'")
        print(f"🔗 URL: {base_url}/api/conversation/{conversation_id}/message/stream")

        response = requests.post(
            f"{base_url}/api/conversation/{conversation_id}/message/stream",
            json={"message": test_message, "include_context": True},
            headers={"Accept": "text/event-stream"},
            stream=True,
        )

        if response.status_code != 200:
            print(f"❌ Failed to send message: {response.status_code}")
            return False

        print("✅ Message sent successfully")

        # Process the streaming response
        completion_data = None

        for line in response.iter_lines():
            if line:
                line_str = line.decode("utf-8")
                if line_str.startswith("data: "):
                    data_str = line_str[6:]  # Remove 'data: ' prefix
                    try:
                        data = json.loads(data_str)

                        if data.get("type") == "complete":
                            completion_data = data
                            if "citations" in data and data["citations"]:
                                print(f"✅ Found {len(data['citations'])} citations in response")
                            else:
                                print("⚠️ No citations found in response")
                            break
                    except json.JSONDecodeError:
                        pass

        if not completion_data:
            print("❌ No completion data found in response")
            return False

        # Wait a moment for citations to be saved
        time.sleep(1)

        # Check if citations were saved to the database
        print("\n🔍 Checking database for saved citations...")

        try:
            import psycopg2
            from psycopg2.extras import DictCursor

            db_url = (
                os.getenv("DATABASE_URL")
                or "postgresql://postgres:postgres@localhost:54322/postgres"
            )
            conn = psycopg2.connect(db_url)
            cursor = conn.cursor(cursor_factory=DictCursor)

            # Check for citations in the database
            cursor.execute(
                """
                SELECT COUNT(*) as count
                FROM citations
                WHERE conversation_id = %s
            """,
                (conversation_id,),
            )

            result = cursor.fetchone()
            saved_citations_count = result["count"]

            if saved_citations_count > 0:
                print(f"✅ Found {saved_citations_count} citations saved to database")

                # Show the saved citations
                cursor.execute(
                    """
                    SELECT citation_type, citation_text, relevance_score
                    FROM citations
                    WHERE conversation_id = %s
                    ORDER BY position_in_response
                """,
                    (conversation_id,),
                )

                citations = cursor.fetchall()
                print("\n📋 Saved Citations:")
                for i, citation in enumerate(citations, 1):
                    print(
                        f"   {i}. [{citation['citation_type']}] {citation['citation_text'][:50]}... (score: {citation['relevance_score']})"
                    )

                return True
            else:
                print(f"❌ No citations found in database for conversation {conversation_id}")

                # Check if any citations exist at all
                cursor.execute("SELECT COUNT(*) as count FROM citations")
                total_result = cursor.fetchone()
                total_count = total_result["count"]

                if total_count > 0:
                    print(f"ℹ️ Total citations in database: {total_count}")

                    # Show some recent citations
                    cursor.execute(
                        """
                        SELECT conversation_id, citation_type, citation_text
                        FROM citations
                        ORDER BY created_at DESC
                        LIMIT 5
                    """
                    )

                    recent_citations = cursor.fetchall()
                    print("\n📋 Recent Citations (from other conversations):")
                    for citation in recent_citations:
                        print(
                            f"   - Conv {citation['conversation_id']}: [{citation['citation_type']}] {citation['citation_text'][:30]}..."
                        )
                else:
                    print("ℹ️ No citations found in database at all")

                return False

        except Exception as e:
            print(f"❌ Error checking database: {e}")
            return False

    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to API server. Make sure it's running on localhost:8000")
        return False
    except Exception as e:
        print(f"❌ Error during test: {e}")
        return False


if __name__ == "__main__":
    print("🚀 Testing Conversation Citations")
    print("=" * 60)
    print("This test sends a message to the streaming API and verifies")
    print("that citations from the response are saved to the database.")
    print()

    success = test_conversation_citations()

    if success:
        print("\n✅ Test passed! Citations are being saved correctly.")
    else:
        print("\n❌ Test failed. Citations are not being saved.")

    print("\n💡 If the test failed, check:")
    print("   1. Is the API server running on localhost:8000?")
    print("   2. Is the database connection configured correctly?")
    print("   3. Are the citations included in the API response?")
    print("   4. Is the citations service working correctly?")

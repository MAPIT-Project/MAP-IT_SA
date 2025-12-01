#!/usr/bin/env python3
"""
Test both user-reported issues:
1. Budget question gives general answer instead of call-specific
2. Proposal writing gets stuck
"""

import requests
import json
import time

API_BASE = "http://localhost:8000/api"
conv_id = 2222

print("\n" + "="*80)
print("TESTING BOTH FIXED ISSUES")
print("="*80)

# Setup context
print("\n1️⃣ Setting up context...")
requests.post(
    f"{API_BASE}/v2/conversation/{conv_id}/message/stream",
    json={"message": "Tell me about HORIZON-CL3-2025-02-CS-ECCC-01", "userId": "test-user"},
    stream=True
)
time.sleep(2)

# TEST 1: Budget question
print("\n2️⃣ Testing budget question (should give call-specific answer)...")
response = requests.post(
    f"{API_BASE}/v2/conversation/{conv_id}/message/stream",
    json={"message": "What about the budget?", "userId": "test-user"},
    stream=True
)

budget_response = ""
for line in response.iter_lines():
    if line and line.decode('utf-8').startswith('data: '):
        try:
            data = json.loads(line.decode('utf-8')[6:])
            if data.get('type') == 'token':
                budget_response += data.get('content', '')
        except:
            pass

print("\nBudget response (first 300 chars):")
print(budget_response[:300])

if 'HORIZON-CL3-2025-02-CS-ECCC-01' in budget_response or 'this call' in budget_response.lower():
    print("✅ FIXED: Response mentions the specific call!")
else:
    print("❌ ISSUE: Still giving general answer")

time.sleep(2)

# TEST 2: Proposal writing
print("\n\n3️⃣ Testing proposal writing (should not get stuck)...")
response = requests.post(
    f"{API_BASE}/v2/conversation/{conv_id}/message/stream",
    json={"message": "Help me write a proposal for it", "userId": "test-user"},
    stream=True
)

event_count = 0
has_draft_content = False

for line in response.iter_lines():
    if line and line.decode('utf-8').startswith('data: '):
        try:
            data = json.loads(line.decode('utf-8')[6:])
            event_type = data.get('type') or data.get('stage')
            event_count += 1
            
            if event_count <= 10:  # Show first 10 events
                print(f"  {event_count}. {event_type}")
            
            if data.get('type') == 'token' and data.get('content'):
                has_draft_content = True
            
            if event_count > 50:  # Safety limit
                break
        except:
            pass

print(f"\nTotal events: {event_count}")

if event_count > 10 and has_draft_content:
    print("✅ FIXED: Proposal generation working! Not stuck!")
elif event_count <= 3:
    print("❌ ISSUE: Still getting stuck after intent detection")
else:
    print("⚠️  PARTIAL: Getting more events but may have other issues")

print("\n" + "="*80)
print("TEST COMPLETE")
print("="*80 + "\n")


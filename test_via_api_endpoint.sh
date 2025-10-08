#!/usr/bin/bash
# Test via the actual API endpoint

echo "🧪 Testing via API Endpoint"
echo "======================================"

# Test question 1: Eligibility
echo -e "\n📋 Question 1: Eligibility Criteria"
echo "--------------------------------------"
curl -s -X POST "http://localhost:8000/api/v2/conversation/123456/message" \
  -H "Content-Type: application/json" \
  -d '{"message": "What are the eligibility criteria for HORIZON-CL3-2025-02-CS-ECCC-01?"}' \
  | jq -r '.response_text' | head -30

# Test question 2: Budget
echo -e "\n\n📋 Question 2: Budget"
echo "--------------------------------------"
curl -s -X POST "http://localhost:8000/api/v2/conversation/123456/message" \
  -H "Content-Type: application/json" \
  -d '{"message": "What is the budget for HORIZON-CL3-2025-02-CS-ECCC-01?"}' \
  | jq -r '.response_text' | head -30

# Test question 3: Deadline
echo -e "\n\n📋 Question 3: Deadline"
echo "--------------------------------------"
curl -s -X POST "http://localhost:8000/api/v2/conversation/123456/message" \
  -H "Content-Type: application/json" \
  -d '{"message": "When is the deadline for HORIZON-CL3-2025-02-CS-ECCC-01?"}' \
  | jq -r '.response_text' | head -30

echo -e "\n\n✅ Test Complete!"



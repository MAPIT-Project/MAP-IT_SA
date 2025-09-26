#!/usr/bin/env python3
"""
Comprehensive test that runs the system and analyzes behavior step by step.
This will help us see exactly what's happening.
"""

import asyncio
import sys
import os
import json
import time
from pathlib import Path
from datetime import datetime

# Add project to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

class SystemTester:
    def __init__(self):
        self.test_results = []
        self.conversation_manager = None
        
    def log_step(self, step: str, details: str):
        """Log a test step with timestamp."""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        print(f"[{timestamp}] {step}: {details}")
        
    async def initialize_system(self):
        """Initialize and validate the conversation system."""
        self.log_step("INIT", "Starting system initialization...")
        
        try:
            # Import and check dependencies
            self.log_step("IMPORT", "Importing ConversationManager...")
            from app.services.conversation.conversation_manager import ConversationManager
            
            # Initialize the conversation manager
            self.log_step("INIT", "Creating ConversationManager instance...")
            self.conversation_manager = ConversationManager()
            
            self.log_step("SUCCESS", "ConversationManager initialized successfully")
            
            # Check if enhanced fallback method exists
            if hasattr(self.conversation_manager, '_get_enhanced_fallback_response'):
                self.log_step("CHECK", "✅ Enhanced fallback method found")
            else:
                self.log_step("ERROR", "❌ Enhanced fallback method missing")
                
            return True
            
        except Exception as e:
            self.log_step("ERROR", f"Failed to initialize: {e}")
            import traceback
            print(traceback.format_exc())
            return False
    
    async def test_intent_analysis(self, query: str):
        """Test the AI intent analysis directly."""
        self.log_step("INTENT", f"Testing intent analysis for: '{query}'")
        
        try:
            # Get the AI intent service
            ai_intent_service = self.conversation_manager.ai_intent_service
            
            # Test intent analysis
            intent_result = await ai_intent_service.analyze_intent(
                message=query,
                conversation_context="",
                conversation_history="",
                conversation_id=1
            )
            
            self.log_step("INTENT", f"Intent type: {intent_result.intent_type}")
            self.log_step("INTENT", f"Confidence: {intent_result.confidence}")
            self.log_step("INTENT", f"Requires tools: {intent_result.requires_tools}")
            self.log_step("INTENT", f"Tool plan length: {len(intent_result.tool_plan) if intent_result.tool_plan else 0}")
            
            if intent_result.tool_plan:
                for i, tool in enumerate(intent_result.tool_plan):
                    self.log_step("INTENT", f"  Tool {i+1}: {tool.tool_name}")
                    
            return intent_result
            
        except Exception as e:
            self.log_step("ERROR", f"Intent analysis failed: {e}")
            import traceback
            print(traceback.format_exc())
            return None
    
    def test_enhanced_fallback_direct(self, query: str):
        """Test the enhanced fallback response directly."""
        self.log_step("FALLBACK", f"Testing enhanced fallback for: '{query}'")
        
        try:
            response = self.conversation_manager._get_enhanced_fallback_response(
                query, 
                {"intent_type": "conversational"}
            )
            
            self.log_step("FALLBACK", f"Response length: {len(response)} chars")
            
            # Check key indicators
            indicators = {
                "horizon europe": "horizon europe" in response.lower(),
                "95.5 billion": "95.5 billion" in response.lower(),
                "pillar": "pillar" in response.lower()
            }
            
            for indicator, found in indicators.items():
                status = "✅" if found else "❌"
                self.log_step("FALLBACK", f"{status} Contains '{indicator}': {found}")
            
            # Show preview
            preview = response[:200] + "..." if len(response) > 200 else response
            self.log_step("FALLBACK", f"Preview: {preview}")
            
            return response
            
        except Exception as e:
            self.log_step("ERROR", f"Enhanced fallback failed: {e}")
            return None
    
    async def test_full_pipeline(self, query: str):
        """Test the complete conversation pipeline."""
        self.log_step("PIPELINE", f"Testing full pipeline for: '{query}'")
        
        try:
            start_time = time.time()
            
            result = await self.conversation_manager.process_message(
                conversation_id=1000,  # Unique test conversation
                user_message=query,
                user_id=1,
                streaming=False
            )
            
            processing_time = time.time() - start_time
            
            self.log_step("PIPELINE", f"Processing time: {processing_time:.2f}s")
            
            if isinstance(result, dict):
                self.log_step("PIPELINE", f"Result type: dict with keys: {list(result.keys())}")
                
                if 'response' in result:
                    response = result['response']
                    self.log_step("PIPELINE", f"Response length: {len(response)} chars")
                    
                    # Check metadata
                    self.log_step("PIPELINE", f"Tools executed: {result.get('tools_executed', 'Unknown')}")
                    self.log_step("PIPELINE", f"Confidence: {result.get('confidence', 'Unknown')}")
                    self.log_step("PIPELINE", f"Grounded: {result.get('grounded', 'Unknown')}")
                    
                    # Check response quality
                    quality_indicators = {
                        "Long enough": len(response) > 300,
                        "Contains Horizon Europe": "horizon europe" in response.lower(),
                        "Contains budget": any(term in response.lower() for term in ["95.5", "billion", "budget"]),
                        "Not 'couldn't find'": "couldn't find" not in response.lower()
                    }
                    
                    passed = 0
                    for indicator, check in quality_indicators.items():
                        status = "✅" if check else "❌"
                        if check:
                            passed += 1
                        self.log_step("QUALITY", f"{status} {indicator}")
                    
                    self.log_step("QUALITY", f"Overall score: {passed}/{len(quality_indicators)}")
                    
                    # Show response preview
                    preview = response[:300] + "..." if len(response) > 300 else response
                    self.log_step("RESPONSE", f"Preview: {preview}")
                    
                    return result
                else:
                    self.log_step("ERROR", "No 'response' field in result")
            else:
                self.log_step("ERROR", f"Invalid result type: {type(result)}")
                
            return None
            
        except Exception as e:
            self.log_step("ERROR", f"Full pipeline failed: {e}")
            import traceback
            print(traceback.format_exc())
            return None
    
    async def run_comprehensive_test(self):
        """Run all tests in sequence."""
        print("🧪 COMPREHENSIVE SYSTEM TEST")
        print("=" * 60)
        
        # Test query
        test_query = "How much funding is available in Horizon Europe and how is it structured?"
        
        self.log_step("START", f"Testing query: '{test_query}'")
        
        # Step 1: Initialize system
        if not await self.initialize_system():
            self.log_step("ABORT", "System initialization failed")
            return False
        
        # Step 2: Test intent analysis
        self.log_step("STEP", "Step 2: Testing Intent Analysis")
        intent_result = await self.test_intent_analysis(test_query)
        
        if intent_result:
            # Check if intent analysis is working correctly
            if intent_result.intent_type == "conversational" and not intent_result.requires_tools:
                self.log_step("SUCCESS", "✅ Intent analysis working correctly")
            else:
                self.log_step("ISSUE", f"⚠️ Intent analysis issue: type={intent_result.intent_type}, tools={intent_result.requires_tools}")
        
        # Step 3: Test enhanced fallback directly
        self.log_step("STEP", "Step 3: Testing Enhanced Fallback")
        fallback_response = self.test_enhanced_fallback_direct(test_query)
        
        if fallback_response and len(fallback_response) > 500:
            self.log_step("SUCCESS", "✅ Enhanced fallback working correctly")
        else:
            self.log_step("ISSUE", "⚠️ Enhanced fallback may have issues")
        
        # Step 4: Test full pipeline
        self.log_step("STEP", "Step 4: Testing Full Pipeline")
        pipeline_result = await self.test_full_pipeline(test_query)
        
        # Final assessment
        print("\n" + "=" * 60)
        print("🎯 FINAL ASSESSMENT")
        print("=" * 60)
        
        if pipeline_result:
            response = pipeline_result.get('response', '')
            
            # Overall quality check
            is_good_response = (
                len(response) > 300 and
                "horizon europe" in response.lower() and
                "couldn't find" not in response.lower()
            )
            
            if is_good_response:
                self.log_step("SUCCESS", "🎉 SYSTEM IS WORKING CORRECTLY!")
                self.log_step("SUCCESS", "The conversational AI is providing proper responses")
                return True
            else:
                self.log_step("ISSUE", "⚠️ System has quality issues")
                return False
        else:
            self.log_step("FAILURE", "❌ System is not working properly")
            return False

async def main():
    """Main test function."""
    tester = SystemTester()
    success = await tester.run_comprehensive_test()
    
    print(f"\n{'='*60}")
    if success:
        print("✅ TEST RESULT: PASSED - System is working correctly!")
    else:
        print("❌ TEST RESULT: FAILED - System needs fixing")
    print(f"{'='*60}")
    
    return success

if __name__ == "__main__":
    asyncio.run(main())
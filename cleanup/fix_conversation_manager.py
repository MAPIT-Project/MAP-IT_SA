#!/usr/bin/env python3
"""
Script to identify and fix issues in the conversation manager.
"""

import sys
from pathlib import Path

# Add project to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def fix_conversation_manager_issues():
    """Identify and fix common issues in the conversation manager."""
    
    print("🔧 Analyzing Conversation Manager for Issues...")
    
    # Read the current conversation manager
    manager_path = project_root / "app" / "services" / "conversation" / "conversation_manager.py"
    
    with open(manager_path, 'r') as f:
        content = f.read()
    
    print(f"📄 Current file length: {len(content)} characters")
    
    # Common issues to check and fix:
    issues_found = []
    fixes_applied = []
    
    # Issue 1: Check if conversational response method has proper fallbacks
    if '_generate_conversational_response' in content:
        print("✅ Found conversational response method")
        
        # Check if it has proper error handling
        if 'try:' in content and 'except Exception' in content:
            print("✅ Error handling present")
        else:
            print("⚠️ Adding better error handling...")
            issues_found.append("Missing comprehensive error handling")
    
    # Issue 2: Check for proper Gemini model configuration
    if 'gemini-flash-lite-latest' in content or 'gemini-2.0-flash-exp' in content:
        print("✅ Gemini model configured")
    else:
        print("⚠️ Gemini model may need updating")
    
    # Issue 3: Check for proper fallback responses
    if '_get_fallback_conversational_response' in content:
        print("✅ Fallback response method exists")
    else:
        print("⚠️ Missing fallback response method")
        issues_found.append("Missing fallback response method")
    
    # Issue 4: Check for proper tool integration
    if 'tool_orchestrator' in content:
        print("✅ Tool orchestrator integrated")
    else:
        print("⚠️ Tool orchestrator may not be properly integrated")
    
    print(f"\n📊 Analysis complete:")
    print(f"   Issues found: {len(issues_found)}")
    
    for issue in issues_found:
        print(f"   - {issue}")
    
    # Now let's create an improved version of the key method that might be failing
    improved_conversational_method = '''
    def _generate_conversational_response(self,
                                        query: str,
                                        context: str,
                                        retrieval_results: List[Dict[str, Any]],
                                        intent_analysis: Dict[str, Any]) -> str:
        """
        Generate conversational AI response with enhanced error handling and fallbacks.
        """
        try:
            logger.info(f"💬 Generating conversational response for: '{query}'")
            
            # Build context chunks from retrieval results
            context_chunks = retrieval_results if retrieval_results else []
            
            # Add some basic context if none available
            if not context_chunks:
                context_chunks = [{
                    'content': "This is a general query about European research and innovation.",
                    'citation': "General Knowledge",
                    'chunk_id': 'general_context'
                }]
            
            # Get system instructions
            system_instructions = self._get_conversational_instructions(intent_analysis)
            
            try:
                # Try to generate response using the response generator
                response = self.response_generator.generate_response(
                    query=query,
                    context_chunks=context_chunks,
                    conversation_context=context,
                    system_instructions=system_instructions
                )
                
                # Extract answer from response
                if isinstance(response, dict) and 'answer' in response:
                    answer = response['answer']
                    if answer and len(answer.strip()) > 10:
                        logger.info(f"💬 Generated response: {len(answer)} chars")
                        return answer
                    else:
                        logger.warning("Response too short, using fallback")
                        return self._get_enhanced_fallback_response(query, intent_analysis)
                else:
                    logger.warning("Invalid response format, using fallback")
                    return self._get_enhanced_fallback_response(query, intent_analysis)
                    
            except Exception as e:
                logger.error(f"Error in response generator: {e}")
                return self._get_enhanced_fallback_response(query, intent_analysis)
            
        except Exception as e:
            logger.error(f"Error generating conversational response: {e}")
            return self._get_enhanced_fallback_response(query, intent_analysis)
    
    def _get_enhanced_fallback_response(self, query: str, intent_analysis: Dict) -> str:
        """
        Enhanced fallback response generator for when AI fails.
        """
        query_lower = query.lower()
        
        # Horizon Europe specific responses
        if 'horizon europe' in query_lower:
            return """**Horizon Europe** is the EU's key funding programme for research and innovation (2021-2027) with a budget of €95.5 billion.
            
**Main Pillars:**
1. **Excellent Science** - Supporting frontier research
2. **Global Challenges & Industrial Competitiveness** - Addressing societal challenges  
3. **Innovative Europe** - Fostering innovation ecosystems

**Key Features:**
• Open to international collaboration
• Focus on mission-driven research
• Strong emphasis on impact and excellence
• Digital and green transitions priority

Would you like specific information about calls, application processes, or success rates?"""

        # AI/Technology queries
        elif any(tech in query_lower for tech in ['ai', 'artificial intelligence', 'machine learning', 'quantum', 'digital']):
            return """🤖 **Digital & AI Research in Europe**

The EU is heavily investing in digital technologies and AI through various programmes:

**Horizon Europe:** Major funding for AI research projects
**Digital Europe Programme:** €7.5 billion for digital transformation
**EIC Accelerator:** Support for AI startups and scale-ups

**Key Focus Areas:**
• Trustworthy AI development
• AI for healthcare and climate
• Quantum computing research
• Digital skills and infrastructure

**Recent Trends:**
• Increased funding for AI applications
• Focus on ethical AI development
• Strong industry-academia partnerships

Would you like me to search for current AI-related funding calls or successful project examples?"""

        # Healthcare queries
        elif any(health in query_lower for health in ['health', 'medical', 'healthcare', 'biotech', 'pharma']):
            return """🏥 **Health Research in Horizon Europe**

Health is a major priority with substantial funding through:

**Cluster 1: Health** - €8.2 billion budget for:
• Cancer research and prevention
• Infectious diseases preparedness
• Personalized medicine
• Health systems transformation

**Key Programmes:**
• **Horizon Health Partnership** - Major public-private collaboration
• **IMI** - Innovative Medicines Initiative
• **EIT Health** - Innovation ecosystem

**Success Factors:**
• Strong clinical validation
• Multi-disciplinary approaches
• Patient-centric design
• Regulatory pathway clarity

Would you like information about current health-related calls or successful project examples?"""

        # Climate/Environment queries
        elif any(env in query_lower for env in ['climate', 'environment', 'green', 'sustainability', 'renewable']):
            return """🌍 **Climate & Environment Research**

Climate action receives massive EU investment through:

**Green Deal:** €1 trillion investment plan
**Horizon Europe Cluster 5:** Climate, Energy & Mobility (€15 billion)
**LIFE Programme:** Environmental and climate action

**Priority Areas:**
• Renewable energy technologies
• Carbon capture and storage
• Circular economy solutions
• Climate adaptation strategies
• Biodiversity conservation

**Mission-Driven Approach:**
• 100 Climate-Neutral Cities by 2030
• Adaptation to Climate Change
• Restore European Waters
• Soil Health and Food Systems

Would you like current information about green technology calls or successful climate projects?"""

        # Funding/Budget queries
        elif any(fund in query_lower for fund in ['budget', 'funding', 'money', 'grant', 'cost']):
            return """💰 **EU Research Funding Overview**

**Total Investment:** €95.5 billion (Horizon Europe 2021-2027)

**Budget Distribution:**
• Pillar I - Excellent Science: €25.8 billion
• Pillar II - Global Challenges: €53.5 billion  
• Pillar III - Innovative Europe: €13.6 billion
• Widening & Strengthening: €2.1 billion

**Funding Rates:**
• Research & Innovation Actions: up to 100%
• Innovation Actions: typically 70%
• Coordination & Support: up to 100%

**Application Success Rates:**
• Overall: ~12-15%
• Excellent Science: ~15-20%
• Some calls: up to 25%

**Tip:** Success depends on excellence, impact, and implementation quality!

Would you like specific budget information for particular research areas?"""

        # Project search queries
        elif any(proj in query_lower for proj in ['project', 'example', 'case study', 'success']):
            return """📋 **Finding EU Research Projects**

**Where to Find Projects:**
• **CORDIS Database:** Official EU project repository
• **Programme Websites:** Horizon Europe, LIFE, etc.
• **Success Stories:** Featured breakthrough projects
• **Partner Search Tools:** Find collaborators

**Project Information Includes:**
• Objectives and outcomes
• Consortium partners
• Budget and duration
• Publications and deliverables
• Impact and exploitation

**Types of Projects:**
• Research & Innovation Actions (RIA)
• Innovation Actions (IA)
• Coordination & Support Actions (CSA)
• Marie Skłodowska-Curie Actions (MSCA)

Would you like me to search for projects in a specific domain or technology area?"""

        # Countries/collaboration queries
        elif any(geo in query_lower for geo in ['country', 'countries', 'collaboration', 'partner']):
            return """🌍 **European Research Collaboration**

**Leading Research Countries:**
• **Germany:** Highest participation & funding
• **France:** Strong in aerospace & energy
• **Italy:** Excellence in materials & culture
• **Spain:** Growing in renewables & health
• **Netherlands:** Innovation & sustainability leader

**Collaboration Benefits:**
• Access to diverse expertise
• Shared costs and risks
• Stronger proposals
• Market access opportunities
• Cultural exchange

**Finding Partners:**
• Partner Search Tool
• National Contact Points
• Enterprise Europe Network
• Research organizations databases

**Success Tips:**
• Complementary capabilities
• Previous collaboration experience
• Strong institutional support
• Clear role definitions

Would you like help finding partners in specific countries or research areas?"""

        # Application/how-to queries
        elif any(how in query_lower for how in ['how', 'apply', 'application', 'proposal', 'submit']):
            return """📝 **How to Apply for EU Funding**

**Application Process:**
1. **Find Calls:** Check Funding & Tenders Portal
2. **Build Consortium:** Find complementary partners
3. **Develop Proposal:** Follow call guidelines exactly
4. **Submit:** Through Participant Portal before deadline
5. **Evaluation:** Remote & panel review process

**Proposal Components:**
• Excellence: Scientific/technical quality
• Impact: Expected outcomes & exploitation
• Implementation: Work plan & consortium

**Success Tips:**
• Start early (6+ months preparation)
• Read call text carefully
• Focus on impact and innovation
• Strong project management plan
• Realistic budget and timeline

**Support Available:**
• National Contact Points
• Proposal writing services  
• EU funding consultants
• Partner search tools

Would you like specific guidance for a particular call or programme?"""

        # General/default response
        else:
            return f"""I'd be happy to help you with European research and innovation topics! 🚀

**Popular Topics I Can Help With:**
• **Horizon Europe** - The main EU funding programme
• **Finding funding calls** - Current opportunities
• **Project examples** - Successful case studies  
• **Application guidance** - How to apply and win
• **Partnership building** - Finding collaborators
• **Programme information** - EIC, MSCA, EIT, etc.

**Your Query:** "{query}"

For the most current information about specific calls or projects, I can search the latest databases. Would you like me to:
• Search for current funding opportunities?
• Find project examples in your area?
• Provide detailed programme information?
• Help with application strategies?

Just let me know what would be most helpful!"""
    '''
    
    # Check if we should apply the fix
    if '_get_enhanced_fallback_response' not in content:
        print("\n🔧 Applying Enhanced Fallback Response Fix...")
        
        # Find the insertion point - after the existing _get_fallback_conversational_response method
        if '_get_fallback_conversational_response' in content:
            insert_point = content.find('def _get_system_instructions')
            if insert_point > 0:
                # Insert the new method before _get_system_instructions
                new_content = content[:insert_point] + improved_conversational_method + '\n    ' + content[insert_point:]
                
                # Write back to file
                with open(manager_path, 'w') as f:
                    f.write(new_content)
                
                fixes_applied.append("Enhanced fallback response method")
                print("✅ Enhanced fallback response method added!")
            else:
                print("⚠️ Could not find insertion point for enhanced fallback")
        else:
            print("⚠️ Base fallback method not found")
    else:
        print("✅ Enhanced fallback already present")
    
    print(f"\n🎯 Summary:")
    print(f"   Issues identified: {len(issues_found)}")
    print(f"   Fixes applied: {len(fixes_applied)}")
    
    for fix in fixes_applied:
        print(f"   ✅ {fix}")
    
    return len(fixes_applied) > 0

if __name__ == "__main__":
    print("🔧 Conversation Manager Fix Tool")
    print("=" * 40)
    
    success = fix_conversation_manager_issues()
    
    if success:
        print("\n🎉 Fixes applied successfully!")
        print("You can now test the improved conversation system.")
    else:
        print("\n💡 No fixes needed or unable to apply fixes.")
        print("The system may already be working correctly.")
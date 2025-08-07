#!/usr/bin/env python3
"""
Simple test script for AI agent
"""
import asyncio
import sys
import os

# Add backend to path
sys.path.append(os.path.dirname(__file__))

from ai_agent_manager import get_ai_agent

async def test_simple_query():
    """Test basic AI functionality"""
    print("🚀 Testing AI Agent...")
    print("=" * 60)
    
    try:
        agent = get_ai_agent()
        print("✅ Agent initialized successfully")
        
        # Test query
        query = "Hello! Can you help me understand what 5 + 3 equals? Please explain your thinking step by step."
        
        print(f"\n📝 Query: {query}")
        print("-" * 60)
        
        # Stream thoughts
        async for thought in agent.analyze(query):
            thought_type = thought.get('type', 'unknown')
            content = thought.get('content', '')
            
            # Format output based on thought type
            if thought_type == 'thinking_start':
                print(f"🤔 {content}")
            elif thought_type == 'thinking_token':
                print(content, end='', flush=True)
            elif thought_type == 'tool_use':
                print(f"\n🔧 {content}")
            elif thought_type == 'tool_start':
                print(f"⚙️ {content}")
            elif thought_type == 'tool_end':
                print(f"✅ {content}")
            elif thought_type == 'thinking_complete':
                print(f"\n🎯 {content}")
            elif thought_type == 'final_result':
                print(f"\n📋 Final Result: {content}")
            elif thought_type == 'error':
                print(f"\n❌ Error: {content}")
            else:
                print(f"\n[{thought_type}] {content}")
        
        print("\n" + "=" * 60)
        print("✅ Test completed successfully!")
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Check if .env exists (in parent directory)
    env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
    if not os.path.exists(env_path):
        print("❌ No .env file found!")
        print("Please create .env file with your ANTHROPIC_API_KEY")
        sys.exit(1)
    
    # Run test
    asyncio.run(test_simple_query())
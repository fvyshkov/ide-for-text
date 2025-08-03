#!/usr/bin/env python3
"""
Super simple test for Claude API
"""
import os
import asyncio
from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic

# Load env
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

async def test_simple_claude():
    """Test Claude directly without agents"""
    print("🧪 Testing Claude API directly...")
    
    try:
        # Initialize Claude
        llm = ChatAnthropic(
            model="claude-3-5-sonnet-20240620",
            temperature=0.3,
            max_tokens=1000,
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY")
        )
        
        # Simple test
        response = await llm.ainvoke("What is 2+2? Explain briefly.")
        
        print(f"✅ Claude Response: {response.content}")
        return True
        
    except Exception as e:
        print(f"❌ Claude Error: {str(e)}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_simple_claude())
    if success:
        print("🎉 Claude API is working!")
    else:
        print("💥 Claude API failed!")
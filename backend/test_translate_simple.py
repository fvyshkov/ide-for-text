#!/usr/bin/env python3
"""
Simple translation test
"""
import asyncio
import os
from ai_agent import get_ai_agent

async def test_simple_translation():
    """Test simple translation"""
    print("Testing simple translation...")
    print("=" * 50)
    
    agent = get_ai_agent()
    
    # Create a simple test file first
    prompt = """Create a file called test-directory/simple_english.txt with this content:
Hello!
This is a test.
Thank you."""
    
    print("Creating test file...")
    async for event in agent.analyze(prompt):
        if event['type'] == 'final_result':
            print(f"File creation: {event['content'][:100]}...")
            break
    
    # Now translate it
    translate_prompt = "Read test-directory/simple_english.txt, translate it to Russian, and save as test-directory/simple_russian.txt"
    
    print("\nTranslating file...")
    async for event in agent.analyze(translate_prompt):
        print(f"[{event['type']}] {event['content'][:100]}...")
        if event['type'] == 'final_result':
            break
    
    print("=" * 50)
    print("Test completed!")

if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    asyncio.run(test_simple_translation())
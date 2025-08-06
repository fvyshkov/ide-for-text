#!/usr/bin/env python3
"""
Simple test for file operations
"""
import asyncio
import os
from ai_agent import get_ai_agent

async def test_simple_file_ops():
    """Test basic file operations"""
    print("Testing basic file operations...")
    print("=" * 50)
    
    agent = get_ai_agent()
    
    # Test 1: List files
    print("\n--- Test 1: List files in test-directory ---")
    async for event in agent.analyze("List all files in the test-directory folder"):
        if event['type'] == 'final_result':
            print(f"Result: {event['content']}")
            break
    
    # Test 2: Read a specific file
    print("\n--- Test 2: Read english_sample.txt ---")
    async for event in agent.analyze("Read the content of test-directory/english_sample.txt"):
        if event['type'] == 'final_result':
            print(f"Result: {event['content'][:200]}...")
            break
    
    # Test 3: Simple file creation
    print("\n--- Test 3: Create a simple test file ---")
    async for event in agent.analyze("Create a file called test-directory/test_output.txt with the content 'Hello from AI!'"):
        if event['type'] == 'final_result':
            print(f"Result: {event['content']}")
            break
    
    print("=" * 50)
    print("Test completed!")

if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    asyncio.run(test_simple_file_ops())
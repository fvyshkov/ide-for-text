#!/usr/bin/env python3
"""
Test script for AI agent translation functionality
"""
import asyncio
import os
from ai_agent import get_ai_agent

async def test_translation():
    """Test the translation functionality"""
    print("Testing AI Agent Translation...")
    print("=" * 50)
    
    # Get the AI agent
    agent = get_ai_agent()
    
    # Test prompt
    prompt = "Please read the file test-directory/english_sample.txt, translate it to Russian, and save the Russian version as test-directory/english_sample_russian.txt"
    
    print(f"Prompt: {prompt}")
    print("-" * 50)
    
    # Process the request
    async for event in agent.analyze(prompt):
        event_type = event.get('type', 'unknown')
        content = event.get('content', '')
        
        if event_type == 'thinking_start':
            print(f"[START] {content}")
        elif event_type == 'thinking':
            print(f"[THINKING] {content}")
        elif event_type == 'tool_use':
            tool_input = event.get('tool_input', {})
            print(f"[TOOL] {content}")
            print(f"  Input: {tool_input}")
        elif event_type == 'tool_result':
            # Truncate long results for readability
            if len(content) > 200:
                truncated = content[:200] + "..."
                print(f"[RESULT] {truncated}")
            else:
                print(f"[RESULT] {content}")
        elif event_type == 'thinking_complete':
            print(f"[COMPLETE] {content}")
        elif event_type == 'final_result':
            print(f"[FINAL] {content}")
        elif event_type == 'error':
            print(f"[ERROR] {content}")
    
    print("=" * 50)
    print("Test completed!")

if __name__ == "__main__":
    # Set working directory to backend
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    asyncio.run(test_translation())
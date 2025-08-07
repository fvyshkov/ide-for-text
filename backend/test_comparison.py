#!/usr/bin/env python3
"""
Compare simple vs improved AI agent implementations
"""
import asyncio
import time

# Import both versions
from ai_agent_simple import SimpleAIAgent

def get_simple_agent(session_id="default"):
    return SimpleAIAgent()
from ai_agent_improved import get_transparent_agent

async def compare_agents():
    """Compare both AI agent implementations"""
    
    test_query = "List files in test-directory and tell me what you find"
    
    print("=" * 60)
    print("AI AGENT COMPARISON TEST")
    print("=" * 60)
    
    # Test 1: Simple Agent (current)
    print("\n1. SIMPLE AGENT (Current Implementation)")
    print("-" * 40)
    simple_agent = get_simple_agent("test")
    
    start = time.time()
    async for event in simple_agent.analyze(test_query):
        if event['type'] == 'tool_use':
            print(f"  Tool: {event['content']}")
        elif event['type'] == 'final_result':
            print(f"  Result: {event['content'][:200]}...")
            break
    simple_time = time.time() - start
    print(f"  Time: {simple_time:.2f}s")
    
    # Test 2: Improved Agent (with LangChain ReAct)
    print("\n2. IMPROVED AGENT (Full LangChain Integration)")
    print("-" * 40)
    improved_agent = get_transparent_agent("test")
    
    start = time.time()
    async for event in improved_agent.analyze(test_query):
        if event['type'] == 'thinking':
            print(f"  Thinking: {event['content'][:100]}...")
        elif event['type'] == 'final_result':
            print(f"  Result: {event['content'][:200]}...")
            break
    improved_time = time.time() - start
    print(f"  Time: {improved_time:.2f}s")
    
    # Comparison
    print("\n" + "=" * 60)
    print("COMPARISON RESULTS:")
    print("-" * 40)
    print(f"Simple Agent:   {simple_time:.2f}s")
    print(f"Improved Agent: {improved_time:.2f}s")
    print(f"Difference:     {abs(simple_time - improved_time):.2f}s")
    
    print("\nKey Differences:")
    print("• Simple: Direct LLM calls, manual tool handling")
    print("• Improved: ReAct reasoning, automatic tool orchestration")
    print("• Simple: 4 specialized tools")
    print("• Improved: 2 universal tools")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(compare_agents())
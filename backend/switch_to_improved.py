#!/usr/bin/env python3
"""
Script to switch from current AI agent to improved version
"""
import shutil
import os

def switch_to_improved():
    """Switch to improved AI agent implementation"""
    
    # Backup current version
    if os.path.exists('ai_agent.py'):
        shutil.copy('ai_agent.py', 'ai_agent_simple.py')
        print("✓ Backed up current version to ai_agent_simple.py")
    
    # Copy improved version
    if os.path.exists('ai_agent_improved.py'):
        shutil.copy('ai_agent_improved.py', 'ai_agent.py')
        print("✓ Switched to improved AI agent")
        
        # Update imports if needed
        print("\nNote: The improved version uses:")
        print("- ReAct Agent pattern")
        print("- AgentExecutor from LangChain")
        print("- Universal tools (2 instead of 4)")
        print("- Streaming callbacks")
        
        print("\nTo use it, restart the backend server:")
        print("  pkill -f 'python main.py'")
        print("  cd backend && python main.py")
    else:
        print("Error: ai_agent_improved.py not found")

if __name__ == "__main__":
    switch_to_improved()
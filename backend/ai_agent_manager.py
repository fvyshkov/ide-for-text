"""
AI Agent Manager - Central configuration for AI agent selection
Allows switching between different AI agent implementations via configuration
"""
import os
from typing import Dict, Any, Optional, AsyncGenerator

# ========== CONFIGURATION ==========
# Change this constant to switch between AI agent implementations
USE_ADVANCED_AGENT = True  # True = Advanced ReAct agent, False = Simple agent
# ===================================

# Session storage for both implementations
_agent_sessions: Dict[str, Any] = {}

def get_ai_agent(session_id: str = "default"):
    """
    Get AI agent instance based on configuration
    
    Args:
        session_id: Session identifier for maintaining context
        
    Returns:
        AI agent instance (SimpleAIAgent or TransparentAnalysisAgent)
    """
    global _agent_sessions
    
    if USE_ADVANCED_AGENT:
        # Import and use advanced ReAct agent
        from ai_agent_improved import TransparentAIAgent
        
        if session_id not in _agent_sessions:
            print(f"Creating new ADVANCED AI agent for session: {session_id}")
            _agent_sessions[session_id] = TransparentAIAgent()
        else:
            print(f"Reusing existing ADVANCED AI agent for session: {session_id}")
            
        return _agent_sessions[session_id]
    else:
        # Import and use simple agent
        from ai_agent_simple import SimpleAIAgent
        
        if session_id not in _agent_sessions:
            print(f"Creating new SIMPLE AI agent for session: {session_id}")
            _agent_sessions[session_id] = SimpleAIAgent()
        else:
            print(f"Reusing existing SIMPLE AI agent for session: {session_id}")
            
        return _agent_sessions[session_id]

def clear_session(session_id: str = "default"):
    """
    Clear AI agent session
    
    Args:
        session_id: Session identifier to clear
    """
    global _agent_sessions
    
    if session_id in _agent_sessions:
        agent = _agent_sessions[session_id]
        
        # Call clear_context if available
        if hasattr(agent, 'clear_context'):
            agent.clear_context()
            
        # Remove from sessions
        del _agent_sessions[session_id]
        print(f"Cleared AI agent session: {session_id}")
    else:
        print(f"No session found for: {session_id}")

def get_agent_info() -> Dict[str, Any]:
    """
    Get information about current AI agent configuration
    
    Returns:
        Dictionary with agent configuration details
    """
    return {
        "mode": "advanced" if USE_ADVANCED_AGENT else "simple",
        "agent_type": "TransparentAIAgent (ReAct)" if USE_ADVANCED_AGENT else "SimpleAIAgent",
        "features": {
            "react_reasoning": USE_ADVANCED_AGENT,
            "agent_executor": USE_ADVANCED_AGENT,
            "universal_tools": USE_ADVANCED_AGENT,
            "streaming_callbacks": USE_ADVANCED_AGENT,
            "file_operations": True,
            "context_management": True
        },
        "active_sessions": list(_agent_sessions.keys())
    }

# For backward compatibility - export functions that might be imported directly
get_transparent_agent = lambda session_id="default": get_ai_agent(session_id) if USE_ADVANCED_AGENT else None
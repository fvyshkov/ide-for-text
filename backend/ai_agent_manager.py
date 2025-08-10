"""
AI Agent Manager - Central configuration for AI agent selection
Allows switching between different AI agent implementations via configuration
"""
import os
from typing import Dict, Any, Optional, AsyncGenerator

# ========== CONFIGURATION ==========
# Use env flag to switch between AI agent implementations
# AI_AGENT_MODE=langchain|simple
USE_ADVANCED_AGENT = os.getenv("AI_AGENT_MODE", "langchain").lower() == "langchain"
# ===================================

# Session storage for both implementations
_agent_sessions: Dict[str, Any] = {}

# Predefined tool names
TOOL_NAMES = ["data_tool", "code_executor"]

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
        # Use LangChain-backed transparent agent (ReAct)
        try:
            from .ai_agent_improved import TransparentAIAgent  # type: ignore
        except Exception:
            from backend.ai_agent_improved import TransparentAIAgent  # type: ignore
        
        if session_id not in _agent_sessions:
            print(f"Creating new TRANSPARENT (LangChain) AI agent for session: {session_id}")
            _agent_sessions[session_id] = TransparentAIAgent()
        else:
            print(f"Reusing existing TRANSPARENT (LangChain) AI agent for session: {session_id}")
            
        return _agent_sessions[session_id]
    else:
        # Import and use simple agent
        try:
            from .ai_agent_simple import SimpleAIAgent  # type: ignore
        except Exception:
            from backend.ai_agent_simple import SimpleAIAgent  # type: ignore
        
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
    current = _agent_sessions.get("default")
    agent_class = type(current).__name__ if current is not None else ("TransparentAIAgent" if USE_ADVANCED_AGENT else "SimpleAIAgent")
    return {
        "mode": "advanced" if USE_ADVANCED_AGENT else "simple",
        "agent_type": agent_class,
        "features": {
            "direct_tool_usage": USE_ADVANCED_AGENT,
            "visualization": USE_ADVANCED_AGENT,
            "universal_tools": USE_ADVANCED_AGENT,
            "streaming": USE_ADVANCED_AGENT,
            "file_operations": True,
            "context_management": True
        },
        "active_sessions": list(_agent_sessions.keys())
    }

def get_tool_names(session_id: str = "default") -> list:
    """
    Get tool names for the current agent
    
    Args:
        session_id: Session identifier
    
    Returns:
        List of tool names
    """
    return TOOL_NAMES

# For backward compatibility - export functions that might be imported directly
get_transparent_agent = get_ai_agent
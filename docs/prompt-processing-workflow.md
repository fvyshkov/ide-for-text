# AI Prompt Processing Workflow

## Overview

This document describes the advanced, flexible workflow for processing AI prompts in the Text IDE system, leveraging a multi-agent architecture with Claude 3.5 for intelligent data analysis, code generation, and complex task handling.

## Architecture Philosophy

**Core Principles:**
- **Flexibility**: Support multiple agent implementations
- **Stateful Processing**: Maintain conversation and session contexts
- **Tool Diversity**: Provide specialized tools for different operations
- **Dynamic Agent Selection**: Switch between simple and advanced agents
- **Comprehensive Logging and Tracking**: Detailed event streaming and tool usage

## Architecture Components

### Agent Management
- **Agent Manager**: Central configuration for dynamic agent selection
- **Session Tracking**: Maintain separate agent instances for different sessions
- **Agent Types**:
  1. **Simple Agent**: Focused on file operations
  2. **Advanced Agent**: Full ReAct pattern with transparent reasoning

### Core Stack
- **Claude 3.5 Sonnet API**: Primary LLM with advanced reasoning capabilities
- **LangChain Agent**: Flexible orchestration with multiple tool support
- **Streaming Callbacks**: Detailed real-time thought process visibility
- **Specialized Tools**: Diverse toolset for complex data and code operations

### Frontend Integration
- **AI Chat Interface**: Real-time streaming of agent thoughts and actions
- **Session Management UI**: Track and manage different agent sessions
- **Detailed Execution Logs**: Comprehensive tool usage and reasoning display

## Workflow Example: Advanced Multi-Tool Processing

### 1. Session Initialization

```python
# Dynamic agent selection based on configuration
def get_ai_agent(session_id: str = "default"):
    if USE_ADVANCED_AGENT:
        # Advanced ReAct agent with multiple specialized tools
        return TransparentAIAgent(session_id)
    else:
        # Simple agent focused on file operations
        return SimpleAIAgent(session_id)
```

### 2. Tool Diversity

```python
# Multiple specialized tools instead of universal ones
class FileOperationTools:
    def __init__(self):
        self.tools = [
            read_file_content,    # Read file contents
            write_file_content,   # Write/modify files
            list_files_in_directory,  # Browse directories
            get_file_info         # Retrieve file metadata
        ]

class AdvancedDataAnalysisTool:
    def __init__(self):
        self.operations = [
            "read_data",          # Universal data reading
            "analyze_structure",  # Data structure analysis
            "transform_data",     # Data transformation
            "generate_insights"   # Advanced data insights
        ]
```

### 3. Streaming Thought Process

```python
class StreamingThoughtCallback:
    async def on_tool_start(self, tool_name, input_str):
        # Detailed logging of tool initialization
        await self.websocket.send_json({
            "type": "tool_start",
            "tool": tool_name,
            "input": input_str,
            "timestamp": current_time()
        })

    async def on_tool_end(self, tool_name, output):
        # Comprehensive tool result streaming
        await self.websocket.send_json({
            "type": "tool_result",
            "tool": tool_name,
            "output": output[:500],  # Truncate long outputs
            "timestamp": current_time()
        })
```

### 4. Session State Management

```python
# Global session storage with advanced tracking
_agent_sessions = {
    "session_id": {
        "agent": TransparentAIAgent,
        "created_at": timestamp,
        "last_activity": timestamp,
        "tool_usage_count": {},
        "conversation_history": []
    }
}
```

## Technical Stack

### Core Dependencies
- **LangChain**: Advanced agent orchestration
- **Claude 3.5 Sonnet API**: Powerful reasoning LLM
- **FastAPI**: WebSocket support for complex streaming
- **React**: Dynamic frontend with detailed session management

### Configuration Example
```yaml
agent_management:
  session_tracking: true
  max_sessions: 10
  session_timeout: 1h

llm:
  provider: anthropic
  model: claude-3-sonnet-20240229
  temperature: 0.3
  max_tokens: 4096
  streaming: true

tools:
  file_operations:
    allowed_operations: [read, write, list, info]
  data_analysis:
    advanced_insights: true
    
ui:
  detailed_logging: true
  session_management: true
  tool_transparency: true
```

## Key Architecture Benefits

### 🔍 **Advanced Flexibility**
- **Multiple Agent Types**: Switch between simple and complex agents
- **Comprehensive Tool Support**: Specialized tools for diverse tasks
- **Detailed Session Tracking**: Maintain context across interactions

### 🛠️ **Powerful Tool Ecosystem**
- **Diverse Tool Operations**: Beyond simple file and code handling
- **Advanced Data Analysis**: Insights generation and transformation
- **Flexible Configuration**: Easy tool and agent customization

### 📊 **Comprehensive Monitoring**
- **Detailed Logging**: Track every agent and tool interaction
- **Performance Insights**: Understand agent and tool usage patterns
- **Debugging Support**: Comprehensive event streaming

*This architecture provides a robust, flexible framework for intelligent text processing with full visibility and advanced capabilities.*
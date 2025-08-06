"""
Simplified AI Agent with Claude 3.5
Focuses on file operations and lets Claude handle all intelligent work
"""
import os
import time
import asyncio
from typing import AsyncGenerator, Dict, Any, Optional, List
from dotenv import load_dotenv

from langchain_anthropic import ChatAnthropic
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage

# Import only file operation tools
from tools.file_operations import read_file_content, write_file_content, list_files_in_directory, get_file_info

# Load environment variables
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))


class SimpleAIAgent:
    """AI Agent that focuses on file operations and lets Claude do the intelligent work"""
    
    def __init__(self):
        # Initialize Claude 3.5 Sonnet
        self.llm = ChatAnthropic(
            model=os.getenv("AI_MODEL", "claude-3-5-sonnet-20240620"),
            temperature=float(os.getenv("AI_TEMPERATURE", "0.3")),
            max_tokens=int(os.getenv("AI_MAX_TOKENS", "4096")),
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY")
        )
        
        # Bind only file operation tools
        self.llm_with_tools = self.llm.bind_tools([
            read_file_content,
            write_file_content,
            list_files_in_directory,
            get_file_info
        ])
        
        # Conversation history for context
        self.conversation_history: List[Any] = []
        
        # Create system prompt focused on file operations
        self.system_prompt = """You are an intelligent AI assistant integrated into a text IDE. You have direct access to the project's file system and can help users with any text-related tasks.

Your capabilities:
- Read any file in the project using read_file_content
- Create or modify files using write_file_content  
- Browse directories using list_files_in_directory
- Get file information using get_file_info

You can perform ANY text manipulation task including but not limited to:
- Translation to any language
- Summarization and analysis
- Style transformation and creative writing
- Code generation and refactoring
- Document structuring and formatting
- Finding patterns and relationships
- Merging and splitting content
- And much more...

Important guidelines:
1. When asked to process a file, always read it first
2. When creating output, save it to an appropriate location (usually near the source or as specified)
3. Preserve formatting and structure when appropriate
4. Explain what you're doing as you work
5. Remember context from previous messages in the conversation
6. You can iterate and refine based on user feedback

File naming conventions:
- For translations: filename_[language].ext (e.g., document_russian.txt)
- For summaries: filename_summary.ext
- For versions: filename_v2.ext or filename_edited.ext
- Or as specified by the user

Always be helpful, thorough, and complete the requested tasks efficiently."""
    
    async def analyze(self, user_query: str, project_path: Optional[str] = None, reset_context: bool = False) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Analyze user query with conversation context
        
        Args:
            user_query: The user's question or request
            project_path: Optional project path for context
            reset_context: Whether to reset conversation history
            
        Yields:
            Dict containing events with type, content, timestamp
        """
        try:
            # Reset context if requested
            if reset_context:
                self.conversation_history = []
            
            # Yield initial thinking message
            yield {
                "type": "thinking_start",
                "content": "Processing your request...",
                "timestamp": time.time()
            }
            
            # Build messages list with history
            messages = []
            
            # Add system message
            messages.append(SystemMessage(content=self.system_prompt))
            
            # Add project context if provided
            if project_path:
                messages.append(SystemMessage(content=f"Working directory: {project_path}"))
            
            # Add conversation history (limit to last 10 exchanges to manage context size)
            history_limit = 20  # 10 user + 10 assistant messages
            if len(self.conversation_history) > history_limit:
                messages.extend(self.conversation_history[-history_limit:])
            else:
                messages.extend(self.conversation_history)
            
            # Add current user message
            current_user_msg = HumanMessage(content=user_query)
            messages.append(current_user_msg)
            
            # Yield understanding message
            yield {
                "type": "thinking",
                "content": f"Understanding request: {user_query}",
                "timestamp": time.time()
            }
            
            # Process with Claude - may require multiple rounds for tool use
            max_rounds = 5  # Prevent infinite loops
            round_count = 0
            
            while round_count < max_rounds:
                round_count += 1
                
                # Get response from Claude
                response = await self.llm_with_tools.ainvoke(messages)
                
                # Check if Claude wants to use tools
                if response.tool_calls:
                    # Add assistant message to conversation
                    messages.append(response)
                    
                    # Execute each tool call
                    for tool_call in response.tool_calls:
                        # Yield tool usage
                        yield {
                            "type": "tool_use",
                            "content": f"Using tool: {tool_call['name']}",
                            "tool_input": tool_call['args'],
                            "timestamp": time.time()
                        }
                        
                        # Execute tool
                        tool_result = None
                        if tool_call['name'] == 'read_file_content':
                            tool_result = read_file_content.invoke(tool_call['args'])
                        elif tool_call['name'] == 'write_file_content':
                            tool_result = write_file_content.invoke(tool_call['args'])
                        elif tool_call['name'] == 'list_files_in_directory':
                            tool_result = list_files_in_directory.invoke(tool_call['args'])
                        elif tool_call['name'] == 'get_file_info':
                            tool_result = get_file_info.invoke(tool_call['args'])
                        
                        if tool_result:
                            # Yield tool result
                            yield {
                                "type": "tool_result",
                                "content": f"Tool result: {tool_result[:500]}..." if len(str(tool_result)) > 500 else f"Tool result: {tool_result}",
                                "timestamp": time.time()
                            }
                            
                            # Add tool result to messages
                            tool_msg = ToolMessage(
                                content=str(tool_result),
                                tool_call_id=tool_call.get('id', '')
                            )
                            messages.append(tool_msg)
                    
                    # Continue to next round to get Claude's response after tool use
                    continue
                else:
                    # No more tool calls, we have the final response
                    break
            
            # Yield completion
            yield {
                "type": "thinking_complete",
                "content": "Analysis completed!",
                "timestamp": time.time()
            }
            
            # Extract and format final response
            content_text = ""
            if hasattr(response, 'content'):
                if isinstance(response.content, str):
                    content_text = response.content
                elif isinstance(response.content, list):
                    # Handle list of content blocks
                    text_parts = []
                    for item in response.content:
                        if isinstance(item, dict):
                            if 'text' in item:
                                text_parts.append(item['text'])
                            elif 'content' in item:
                                text_parts.append(item['content'])
                        elif isinstance(item, str):
                            text_parts.append(item)
                    content_text = '\n'.join(text_parts)
                else:
                    content_text = str(response.content)
            else:
                content_text = str(response)
            
            # Save to conversation history
            self.conversation_history.append(current_user_msg)
            self.conversation_history.append(AIMessage(content=content_text))
            
            # Yield final result
            yield {
                "type": "final_result",
                "content": content_text,
                "full_result": {"output": content_text},
                "timestamp": time.time()
            }
            
        except Exception as e:
            yield {
                "type": "error",
                "content": f"Error during analysis: {str(e)}",
                "timestamp": time.time()
            }
    
    def clear_context(self):
        """Clear conversation history"""
        self.conversation_history = []
    
    def get_context_size(self) -> int:
        """Get the current size of conversation history"""
        return len(self.conversation_history)


# Global agent instance - one per session
ai_agents = {}

def get_ai_agent(session_id: str = "default") -> SimpleAIAgent:
    """Get or create an AI agent for a session"""
    global ai_agents
    if session_id not in ai_agents:
        ai_agents[session_id] = SimpleAIAgent()
    return ai_agents[session_id]

def clear_session(session_id: str = "default"):
    """Clear a specific session"""
    global ai_agents
    if session_id in ai_agents:
        del ai_agents[session_id]


# Test function
async def test_agent():
    """Test the simplified AI agent"""
    agent = get_ai_agent("test")
    
    print("Testing Simplified AI Agent...")
    print("=" * 50)
    
    # Test 1: Simple file operation
    print("\nTest 1: List files")
    async for thought in agent.analyze("List files in test-directory"):
        if thought['type'] == 'final_result':
            print(f"Result: {thought['content'][:200]}...")
            break
    
    # Test 2: Complex task with context
    print("\nTest 2: Translation with context")
    async for thought in agent.analyze("Read test-directory/english_sample.txt and translate it to Russian. Save as test-directory/english_to_russian.txt"):
        if thought['type'] == 'tool_use':
            print(f"Using: {thought['content']}")
        elif thought['type'] == 'final_result':
            print(f"Result: {thought['content'][:200]}...")
            break
    
    # Test 3: Follow-up with context
    print("\nTest 3: Follow-up question")
    async for thought in agent.analyze("Now create a summary of that Russian text in English"):
        if thought['type'] == 'final_result':
            print(f"Result: {thought['content'][:200]}...")
            break
    
    print("=" * 50)
    print("Test completed!")


if __name__ == "__main__":
    asyncio.run(test_agent())
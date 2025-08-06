"""
Transparent AI Agent with Claude 3.5 and LangChain
Shows thinking process to users in real-time
"""
import os
import time
import asyncio
from typing import AsyncGenerator, Dict, Any, Optional
from dotenv import load_dotenv

from langchain_anthropic import ChatAnthropic
from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage

# Import tools
from tools.data_analysis import DataAnalysisTool
from tools.file_operations import read_file_content, write_file_content, list_files_in_directory, get_file_info
from tools.translation import translate_text, translate_file_content

# Load environment variables from parent directory
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

# Define a simple tool using the new @tool decorator
@tool
def simple_calculator(expression: str) -> str:
    """
    Perform simple mathematical calculations.
    
    Args:
        expression: A simple mathematical expression like "2+2" or "5*3"
    
    Returns:
        The result of the calculation
    """
    try:
        # Safety: only allow basic math operations
        allowed_chars = set("0123456789+-*/.() ")
        if all(c in allowed_chars for c in expression):
            result = eval(expression)
            return f"The result of {expression} is {result}"
        else:
            return "Error: Only basic mathematical operations are allowed"
    except Exception as e:
        return f"Error calculating {expression}: {str(e)}"


class TransparentAIAgent:
    """AI Agent that shows its thinking process transparently"""
    
    def __init__(self):
        # Initialize Claude 3.5 Sonnet
        self.llm = ChatAnthropic(
            model=os.getenv("AI_MODEL", "claude-3-5-sonnet-20240620"),
            temperature=float(os.getenv("AI_TEMPERATURE", "0.3")),
            max_tokens=int(os.getenv("AI_MAX_TOKENS", "4096")),
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY")
        )
        
        # Bind tools to the model  
        self.llm_with_tools = self.llm.bind_tools([
            simple_calculator,
            DataAnalysisTool.analyze_data,
            DataAnalysisTool.query_data,
            DataAnalysisTool.aggregate_data,
            read_file_content,
            write_file_content,
            list_files_in_directory,
            get_file_info,
            translate_text,
            translate_file_content
        ])
        
        # Create transparent prompt
        self.system_prompt = """You are a helpful AI assistant that can work with files and perform various tasks on a coding project. You have access to powerful tools for file operations, translation, and data analysis.

Available tools:
- read_file_content: Read the content of any file in the project
- write_file_content: Create or modify files with new content
- list_files_in_directory: Browse directories to see what files are available
- get_file_info: Get information about files (size, type, etc.)
- translate_text: Translate text to different languages
- translate_file_content: Translate entire files while preserving structure

For file-related requests:
1. First understand exactly what the user wants to do
2. Plan your approach step by step
3. Use the appropriate tools to read, analyze, or modify files
4. Always explain what you're doing and why
5. Show the results clearly

For translation tasks:
- When asked to translate a file, read it first, then translate the content
- If asked to create a translated version "nearby" or "next to" the original, create it in the same directory with a clear naming convention (e.g., filename_russian.txt)
- Preserve the original file structure and formatting

Always be helpful, explain your process, and complete the requested tasks efficiently."""
    
    async def analyze(self, user_query: str, project_path: Optional[str] = None) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Analyze user query and stream thoughts/results
        
        Args:
            user_query: The user's question or request
            
        Yields:
            Dict containing thought events with type, content, timestamp
        """
        try:
            # Yield initial thinking message
            yield {
                "type": "thinking_start",
                "content": "Processing your request...",
                "timestamp": time.time()
            }
            
            # Create messages with context
            context = f"Working directory: {project_path}" if project_path else "No working directory set"
            messages = [
                ("system", self.system_prompt),
                ("system", context),
                ("human", user_query)
            ]
            
            # Yield understanding message
            yield {
                "type": "thinking",
                "content": f"Understanding request: {user_query}",
                "timestamp": time.time()
            }
            
            # Get response from Claude
            response = await self.llm_with_tools.ainvoke(messages)
            
            # Handle tool calls and potential follow-up responses
            all_tool_results = []
            
            # Check if Claude wants to use tools
            if response.tool_calls:
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
                    if tool_call['name'] == 'simple_calculator':
                        tool_result = simple_calculator.invoke(tool_call['args'])
                    elif tool_call['name'] == 'analyze_data':
                        tool_result = DataAnalysisTool.analyze_data.invoke(tool_call['args'])
                    elif tool_call['name'] == 'query_data':
                        tool_result = DataAnalysisTool.query_data.invoke(tool_call['args'])
                    elif tool_call['name'] == 'aggregate_data':
                        tool_result = DataAnalysisTool.aggregate_data.invoke(tool_call['args'])
                    elif tool_call['name'] == 'read_file_content':
                        tool_result = read_file_content.invoke(tool_call['args'])
                    elif tool_call['name'] == 'write_file_content':
                        tool_result = write_file_content.invoke(tool_call['args'])
                    elif tool_call['name'] == 'list_files_in_directory':
                        tool_result = list_files_in_directory.invoke(tool_call['args'])
                    elif tool_call['name'] == 'get_file_info':
                        tool_result = get_file_info.invoke(tool_call['args'])
                    elif tool_call['name'] == 'translate_text':
                        tool_result = translate_text.invoke(tool_call['args'])
                    elif tool_call['name'] == 'translate_file_content':
                        tool_result = translate_file_content.invoke(tool_call['args'])
                    
                    if tool_result:
                        yield {
                            "type": "tool_result",
                            "content": f"Tool result: {tool_result}",
                            "timestamp": time.time()
                        }
                        all_tool_results.append({
                            "tool_call_id": tool_call.get('id', ''),
                            "tool_name": tool_call['name'],
                            "content": str(tool_result)
                        })
                
                # If there were tool calls, we need to get the final response
                if all_tool_results:
                    # Create proper tool messages for the conversation
                    from langchain_core.messages import AIMessage, ToolMessage
                    
                    # Add assistant message with tool calls
                    messages.append(response)
                    
                    # Add tool results as proper ToolMessage objects
                    for tool_result in all_tool_results:
                        tool_msg = ToolMessage(
                            content=tool_result["content"],
                            tool_call_id=tool_result["tool_call_id"]
                        )
                        messages.append(tool_msg)
                    
                    # Get the final response from Claude after tool execution
                    yield {
                        "type": "thinking",
                        "content": "Processing tool results and generating final response...",
                        "timestamp": time.time()
                    }
                    
                    final_response = await self.llm_with_tools.ainvoke(messages)
                    response = final_response  # Use the final response for content extraction
            
            # Yield completion
            yield {
                "type": "thinking_complete",
                "content": "Analysis completed!",
                "timestamp": time.time()
            }
            
            # Send final result
            # Extract text content from response
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
                            else:
                                text_parts.append(str(item))
                        elif isinstance(item, str):
                            text_parts.append(item)
                        else:
                            text_parts.append(str(item))
                    content_text = '\n'.join(text_parts)
                else:
                    content_text = str(response.content)
            else:
                content_text = str(response)
            
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


# Global agent instance
ai_agent = None

def get_ai_agent() -> TransparentAIAgent:
    """Get or create the global AI agent instance"""
    global ai_agent
    if ai_agent is None:
        ai_agent = TransparentAIAgent()
    return ai_agent


# Test function
async def test_agent():
    """Test the AI agent"""
    agent = get_ai_agent()
    
    print("Testing AI Agent...")
    print("=" * 50)
    
    async for thought in agent.analyze("What is 2 + 2? Explain your thinking."):
        print(f"[{thought['type']}] {thought['content']}")
    
    print("=" * 50)
    print("Test completed!")


if __name__ == "__main__":
    asyncio.run(test_agent())
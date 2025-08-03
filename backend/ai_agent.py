"""
Transparent AI Agent with Claude 3.5 and LangChain
Shows thinking process to users in real-time
"""
import os
import time
import asyncio
from typing import AsyncGenerator, Dict, Any
from dotenv import load_dotenv

from langchain_anthropic import ChatAnthropic
from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage

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
        self.llm_with_tools = self.llm.bind_tools([simple_calculator])
        
        # Create transparent prompt
        self.system_prompt = """You are a transparent AI assistant that ALWAYS explains your thinking process step by step, regardless of how the question is asked.

For EVERY request, no matter how simple, you MUST:
1. First explain what you understand from the user's request
2. Share your plan of action and reasoning
3. For calculations:
   - Do ALL calculations yourself, showing each step
   - NEVER use the calculator tool unless explicitly asked by the user
4. Always end with a clear, direct answer

Remember:
- Even for simple questions, show ALL your thinking
- Break down your reasoning into clear steps
- Be conversational and educational
- Never skip steps, even if they seem obvious
- For math problems:
  * Show each step of your calculation
  * Format the final answer clearly: "The answer is: [result]"
  * For decimal results, show up to 4 decimal places"""
    
    async def analyze(self, user_query: str) -> AsyncGenerator[Dict[str, Any], None]:
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
                "content": "🤔 Processing your request...",
                "timestamp": time.time()
            }
            
            # Create messages
            messages = [
                ("system", self.system_prompt),
                ("human", user_query)
            ]
            
            # Yield understanding message
            yield {
                "type": "thinking",
                "content": f"📝 Understanding request: {user_query}",
                "timestamp": time.time()
            }
            
            # Get response from Claude
            response = await self.llm_with_tools.ainvoke(messages)
            
            # Check if Claude wants to use tools
            if response.tool_calls:
                for tool_call in response.tool_calls:
                    # Yield tool usage
                    yield {
                        "type": "tool_use",
                        "content": f"🔧 Using tool: {tool_call['name']}",
                        "tool_input": tool_call['args'],
                        "timestamp": time.time()
                    }
                    
                    # Execute tool (simplified for now)
                    if tool_call['name'] == 'simple_calculator':
                        tool_result = simple_calculator.invoke(tool_call['args'])
                        yield {
                            "type": "tool_result",
                            "content": f"✅ Tool result: {tool_result}",
                            "timestamp": time.time()
                        }
            
            # Yield completion
            yield {
                "type": "thinking_complete",
                "content": "🎯 Analysis completed!",
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
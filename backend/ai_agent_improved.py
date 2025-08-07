"""
Transparent AI Agent with Claude 3.5 - Aligned with prompt-processing-workflow.md
Uses LangChain ReAct pattern with streaming callbacks
"""
import os
import time
import json
import asyncio
from typing import AsyncGenerator, Dict, Any, Optional, List
from dotenv import load_dotenv

from langchain.agents import AgentExecutor, create_react_agent
from langchain_anthropic import ChatAnthropic
from langchain.callbacks.base import AsyncCallbackHandler
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langchain.tools import Tool, BaseTool
from langchain.prompts import PromptTemplate
from langchain_core.messages import SystemMessage
from pydantic import BaseModel, Field
import pandas as pd
import json

# Load environment variables
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))


class StreamingThoughtCallback(AsyncCallbackHandler):
    """Callback to stream agent thoughts in real-time"""
    
    def __init__(self, websocket=None):
        self.websocket = websocket
        self.thoughts = []
    
    async def on_llm_start(self, serialized: Dict[str, Any], prompts: List[str], **kwargs) -> None:
        """Called when LLM starts thinking"""
        thought = {
            "type": "thinking_start",
            "content": "🤔 Understanding request...",
            "timestamp": int(time.time() or 0)
        }
        self.thoughts.append(thought)
        if self.websocket:
            await self.websocket.send_json(thought)
    
    async def on_tool_start(self, serialized: Dict[str, Any], input_str: str, **kwargs) -> None:
        """Called when a tool is about to be used"""
        tool_name = serialized.get("name", "unknown")
        thought = {
            "type": "tool_use",
            "content": f"🔧 Using {tool_name}",
            "tool_input": input_str,
            "timestamp": int(time.time() or 0)
        }
        self.thoughts.append(thought)
        if self.websocket:
            await self.websocket.send_json(thought)
    
    async def on_tool_end(self, output: str, **kwargs) -> None:
        """Called when a tool finishes"""
        thought = {
            "type": "tool_result",
            "content": f"✓ Tool completed",
            "result": output[:200] + "..." if len(output) > 200 else output,
            "timestamp": int(time.time() or 0)
        }
        self.thoughts.append(thought)
        if self.websocket:
            await self.websocket.send_json(thought)


class UniversalDataTool(BaseTool):
    """Universal tool for all data operations - reading, analyzing, transforming"""
    name: str = "data_tool"
    description: str = """Universal data tool that can:
    - Read any file (text, Excel, CSV, JSON, etc.)
    - Analyze data structure and content
    - Transform and process data
    - List directory contents
    
    Usage: "data_tool operation argument"
    Operations:
    - list directory_path
    - read file_path
    - analyze file_path
    - write json_string
    
    Examples:
    - data_tool list test-directory
    - data_tool read test-directory/example.txt
    - data_tool analyze test-directory/data.csv
    - data_tool write {"path": "test-directory/output.txt", "content": "Hello"}"""
    
    def _run(self, input_str: str) -> str:
        """Parse input string and execute operation"""
        print(f"DEBUG: UniversalDataTool._run called with input_str: {input_str}")
        try:
            # Parse input string
            parts = input_str.split(" ", 1)
            print(f"DEBUG: Parts: {parts}")
            if len(parts) != 2:
                return "Error: Invalid input format. Expected 'operation arguments'"
            
            operation = parts[0].strip()
            arguments = parts[1].strip()
            print(f"DEBUG: operation={operation}, arguments={arguments}")
            # Безопасная обработка аргументов
            arguments = arguments or '.'
            # Get project root
            backend_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(backend_dir)
            print(f"DEBUG: project_root: {project_root}")
            
            if operation == "read":
                if not os.path.exists(arguments):
                    return f"Error: File '{arguments}' not found"
                
                # Detect file type and read accordingly
                if arguments.endswith(('.xlsx', '.xls')):
                    df = pd.read_excel(arguments)
                    return f"Excel file with {len(df)} rows, columns: {list(df.columns)}\n\nFirst 5 rows:\n{df.head().to_string()}"
                elif arguments.endswith('.csv'):
                    df = pd.read_csv(arguments)
                    return f"CSV file with {len(df)} rows, columns: {list(df.columns)}\n\nFirst 5 rows:\n{df.head().to_string()}"
                elif arguments.endswith('.json'):
                    with open(arguments, 'r') as f:
                        data = json.load(f)
                    return f"JSON content:\n{json.dumps(data, indent=2)[:1000]}"
                else:
                    # Text file
                    with open(arguments, 'r', encoding='utf-8') as f:
                        content = f.read()
                    return f"File content:\n{content}"
            
            elif operation == "list":
                dir_path = os.path.join(project_root, arguments) if arguments else project_root
                if not os.path.exists(dir_path):
                    return f"Error: Directory '{arguments}' not found"
                
                items = []
                for item in sorted(os.listdir(dir_path)):
                    item_path = os.path.join(dir_path, item)
                    if os.path.isdir(item_path):
                        items.append(f"[DIR]  {item}/")
                    else:
                        size = os.path.getsize(item_path)
                        items.append(f"[FILE] {item} ({size} bytes)")
                
                return f"Contents of '{arguments or 'root'}':\n" + (('\n'.join(items)) if items else 'No items found')
            
            elif operation == "analyze":
                if not os.path.exists(arguments):
                    return f"Error: File '{arguments}' not found"
                
                stat = os.stat(arguments)
                info = [
                    f"Path: {arguments}",
                    f"Size: {stat.st_size} bytes",
                    f"Type: {'Directory' if os.path.isdir(arguments) else 'File'}",
                    f"Modified: {time.ctime(stat.st_mtime)}"
                ]
                
                # Additional analysis for data files
                if arguments.endswith(('.xlsx', '.csv')):
                    try:
                        df = pd.read_excel(arguments) if arguments.endswith('.xlsx') else pd.read_csv(arguments)
                        info.extend([
                            f"Rows: {len(df)}",
                            f"Columns: {list(df.columns)}",
                            f"Data types: {df.dtypes.to_dict()}",
                            f"Missing values: {df.isnull().sum().to_dict()}"
                        ])
                    except:
                        pass
                
                return "\n".join(info)
            
            elif operation == "write":
                # Parse arguments as JSON
                try:
                    write_args = json.loads(arguments)
                    file_path = write_args.get('path')
                    content = write_args.get('content', '')
                except:
                    return "Error: Write arguments must be JSON with 'path' and 'content'"
                
                if not file_path:
                    return "Error: No file path provided"
                
                full_path = os.path.join(project_root, file_path)
                
                # Create directory if needed
                dir_path = os.path.dirname(full_path)
                if dir_path:
                    os.makedirs(dir_path, exist_ok=True)
                
                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                return f"Successfully wrote {len(content)} characters to {file_path}"
            
            else:
                return f"Unknown operation: {operation}"
                
        except Exception as e:
            return f"Error in data_tool: {str(e)}"
    
    async def _arun(self, input_str: str) -> str:
        """Async version"""
        print(f"DEBUG: _arun input_str: {input_str}")
        return self._run(input_str)


class CodeExecutor(BaseTool):
    """Execute Python code for analysis and visualization"""
    name: str = "code_executor"
    description: str = """Execute Python code for data analysis, visualization, and processing.
    The code has access to common libraries: pandas, numpy, matplotlib, seaborn, scipy.
    
    Usage: "code_executor python_code"
    Example: code_executor print("Hello World")
    
    Code should be complete and self-contained."""
    
    def _run(self, code: str) -> str:
        """Execute Python code safely"""
        try:
            # Create a restricted execution environment
            exec_globals = {
                'pd': pd,
                'pandas': pd,
                '__builtins__': {
                    'print': print,
                    'len': len,
                    'range': range,
                    'enumerate': enumerate,
                    'zip': zip,
                    'map': map,
                    'filter': filter,
                    'sum': sum,
                    'min': min,
                    'max': max,
                    'abs': abs,
                    'round': round,
                    'sorted': sorted,
                    'str': str,
                    'int': int,
                    'float': float,
                    'list': list,
                    'dict': dict,
                    'set': set,
                    'tuple': tuple,
                    'open': open,
                }
            }
            
            # Capture output
            import io
            import sys
            old_stdout = sys.stdout
            sys.stdout = buffer = io.StringIO()
            
            try:
                exec(code, exec_globals)
                output = buffer.getvalue()
                return f"Code executed successfully.\nOutput:\n{output}" if output else "Code executed successfully (no output)."
            finally:
                sys.stdout = old_stdout
                
        except Exception as e:
            return f"Error executing code: {str(e)}"
    
    async def _arun(self, code: str) -> str:
        """Async version"""
        return self._run(code)


class TransparentAIAgent:
    """AI Agent aligned with prompt-processing-workflow.md architecture"""
    
    def __init__(self, websocket=None):
        # Initialize Claude 3.5 Sonnet with streaming
        self.llm = ChatAnthropic(
            model=os.getenv("AI_MODEL", "claude-3-5-sonnet-20240620"),
            temperature=float(os.getenv("AI_TEMPERATURE", "0.3")),
            max_tokens=int(os.getenv("AI_MAX_TOKENS", "4096")),
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
            streaming=True
        )
        
        # Initialize callbacks
        self.callbacks = [
            StreamingThoughtCallback(websocket),
            StreamingStdOutCallbackHandler()
        ]
        
        # Define universal tools (only 2 as per architecture)
        self.tools = [
            UniversalDataTool(),
            CodeExecutor()
        ]
        
        # Create transparent prompt template
        self.prompt = PromptTemplate.from_template("""Assistant is designed to be able to assist with a wide range of tasks, from answering simple questions to providing in-depth explanations and discussions on a wide range of topics. As a language model, Assistant is able to generate human-like text based on the input it receives, allowing it to engage in natural-sounding conversations and provide responses that are coherent and relevant to the topic at hand.

Assistant is constantly learning and improving, and its capabilities are constantly evolving. It is able to process and understand large amounts of text, and can use this knowledge to provide accurate and informative responses to a wide range of questions. Additionally, Assistant is able to generate its own text based on the input it receives, allowing it to engage in discussions and provide explanations on a wide range of topics.

Overall, Assistant is a powerful system that can help with a wide range of tasks and provide valuable insights and information on a wide range of topics. Whether you need help with a specific question or just want to have a conversation about a particular topic, Assistant is here to assist.

TOOLS:
------

Assistant has access to the following tools:

{tools}

To use a tool, please use the following format:

Thought: Do I need to use a tool? Yes/No
Action: the action to take, should be one of [{tool_names}] (only if tool is needed)
Action Input: the input to the action (only if tool is needed)
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

Note: For simple questions like translation, conversation, or general knowledge that don't require file operations or code execution, you can answer directly without using tools.

Begin!

Question: {input}
Thought: Let me approach this step by step:
{agent_scratchpad}""")
        
        # Create ReAct agent as per architecture
        self.agent = create_react_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=self.prompt
        )
        
        # Create agent executor with streaming
        self.agent_executor = AgentExecutor.from_agent_and_tools(
            agent=self.agent,
            tools=self.tools,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=20,  # Increased from 5 to 20
            max_execution_time=120,  # Added 2-minute timeout
            return_intermediate_steps=True
        )
        
        # Conversation history
        self.conversation_history = []
    
    def clear_context(self):
        """Clear conversation history"""
        self.conversation_history = []
        print("Conversation history cleared")
    
    async def analyze(self, query: str, project_path: Optional[str] = None, reset_context: bool = False) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Analyze user query with full transparency
        
        Args:
            query: User's request
            project_path: Optional project context
            reset_context: Whether to clear conversation history before processing
            
        Yields:
            Stream of thought events
        """
        try:
            # Clear context if requested
            if reset_context:
                self.clear_context()
            
            # Initial thinking event
            yield {
                "type": "thinking_start",
                "content": "Processing your request...",
                "timestamp": int(time.time() or 0)
            }
            
            # Add project context if provided
            context_query = query
            if project_path:
                context_query = f"[Working in: {project_path}]\n{query}"
            
            print(f"DEBUG: Processing query: {query}")
            print(f"DEBUG: Project path: {project_path}")
            print(f"DEBUG: Executor: {self.agent_executor}")
            print(f"DEBUG: Tools: {self.tools}")

            # Stream agent execution
            async for chunk in self.agent_executor.astream(
                {"input": context_query},
                config={"callbacks": self.callbacks}
            ):
                # Process and yield chunks
                if "output" in chunk:
                    yield {
                        "type": "final_result",
                        "content": chunk["output"],
                        "timestamp": int(time.time() or 0)
                    }
                elif "intermediate_steps" in chunk:
                    steps = chunk.get("intermediate_steps", [])
                    if steps and isinstance(steps, list):
                        for step in steps:
                            if isinstance(step, (list, tuple)) and len(step) >= 2:
                                action, observation = step[0], step[1]
                                # Extract action details
                                action_str = str(action)
                                if "Action:" in action_str and "Action Input:" in action_str:
                                    # Split into thought and action
                                    parts = action_str.split("Action:", 1)
                                    if len(parts) == 2:
                                        thought = parts[0].replace("Thought:", "").strip()
                                        action_part = parts[1].strip()
                                        
                                        # Yield thought
                                        if thought:
                                            yield {
                                                "type": "thinking",
                                                "content": thought,
                                                "timestamp": int(time.time() or 0)
                                            }
                                        
                                        # Parse action and input
                                        action_parts = action_part.split("Action Input:", 1)
                                        if len(action_parts) == 2:
                                            tool = action_parts[0].strip()
                                            tool_input = action_parts[1].strip()
                                            
                                            # Combine tool and input
                                            tool_call = f"{tool} {tool_input}"
                                            
                                            # Yield tool use
                                            yield {
                                                "type": "tool_use",
                                                "content": f"Using tool: {tool_call}",
                                                "timestamp": int(time.time() or 0)
                                            }
                                            
                                            # Execute tool and get observation
                                            try:
                                                print(f"DEBUG: About to execute tool {tool} with input {tool_input}")
                                                if tool == "data_tool":
                                                    observation = self.tools[0]._run(tool_input)
                                                elif tool == "code_executor":
                                                    observation = self.tools[1]._run(tool_input)
                                                else:
                                                    observation = f"Unknown tool: {tool}"
                                                
                                                # Yield observation
                                                yield {
                                                    "type": "tool_result",
                                                    "content": str(observation),
                                                    "timestamp": int(time.time() or 0)
                                                }
                                            except Exception as e:
                                                yield {
                                                    "type": "error",
                                                    "content": f"Error executing tool: {str(e)}",
                                                    "timestamp": int(time.time() or 0)
                                                }
                                                yield {
                                                    "type": "thinking_complete",
                                                    "content": "✗ Analysis failed!",
                                                    "timestamp": int(time.time() or 0)
                                                }
                                                yield {
                                                    "type": "final_result",
                                                    "content": "Failed to execute tool.",
                                                    "timestamp": int(time.time() or 0)
                                                }
                                                return
                                else:
                                    yield {
                                        "type": "thinking",
                                        "content": action_str,
                                        "timestamp": int(time.time() or 0)
                                    }
            
            # Completion event
            yield {
                "type": "thinking_complete",
                "content": "✓ Analysis completed!",
                "timestamp": int(time.time() or 0)
            }
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"ERROR in analyze: {e}")
            print(f"ERROR traceback: {error_details}")
            yield {
                "type": "error",
                "content": f"Error: {str(e)}",
                "timestamp": int(time.time() or 0)
            }


# Global agent management
agents = {}

def get_transparent_agent(session_id: str = "default", websocket=None) -> TransparentAIAgent:
    """Get or create a transparent agent for a session"""
    global agents
    if session_id not in agents:
        agents[session_id] = TransparentAIAgent(websocket)
    return agents[session_id]


# Test function
async def test_transparent_agent():
    """Test the transparent agent"""
    agent = get_transparent_agent("test")
    
    print("Testing Transparent AI Agent")
    print("=" * 50)
    
    test_queries = [
        "List all files in test-directory",
        "Read the file test-directory/example.txt and summarize it",
        "Analyze the structure of any Excel files in test-directory/data-samples"
    ]
    
    for query in test_queries:
        print(f"\nQuery: {query}")
        print("-" * 30)
        
        async for event in agent.analyze(query):
            print(f"[{event['type']}] {event['content'][:100]}...")
            if event['type'] == 'final_result':
                break
    
    print("=" * 50)
    print("Test completed!")


if __name__ == "__main__":
    asyncio.run(test_transparent_agent())
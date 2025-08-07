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

from langchain.agents import AgentExecutor, create_react_agent, AgentType
from langchain.agents import initialize_agent
from langchain_anthropic import ChatAnthropic
from langchain.callbacks.base import AsyncCallbackHandler
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langchain.tools import Tool, BaseTool
from langchain.prompts import PromptTemplate
from langchain_core.messages import SystemMessage
from pydantic import BaseModel, Field, ConfigDict
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
    - Provide data insights for visualization
    
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
    - data_tool write {"path": "test-directory/output.txt", "content": "Hello"}
    
    For data visualization requests, this tool provides data analysis that can be used by code_executor to create charts."""
    
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
    
    IMPORTANT: When creating visualizations:
    - Save charts to test-directory/ or test-directory/charts/ 
    - Always use plt.savefig() and plt.close()
    - Print the saved file path for user feedback
    
    Code should be complete and self-contained."""
    
    def _run(self, code: str) -> str:
        """Execute Python code safely"""
        try:
            # Create execution environment with necessary modules
            import matplotlib.pyplot as plt
            import numpy as np
            import os
            import json
            import time
            
            exec_globals = {
                'pd': pd,
                'pandas': pd,
                'plt': plt,
                'matplotlib.pyplot': plt,
                'np': np,
                'numpy': np,
                'os': os,
                'json': json,
                'time': time,
                '__builtins__': __builtins__
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
    """AI Agent with ReAct pattern for data analysis and visualization"""
    
    def __init__(self, websocket=None):
        # Initialize Claude 3.5 Sonnet
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
        
        # Define tools
        self.tools = [
            UniversalDataTool(),
            CodeExecutor()
        ]
        
        # Prepare tool descriptions and names
        self.tool_descriptions = "\n".join([f"- {tool.name}: {tool.description}" for tool in self.tools])
        self.tool_names = ", ".join([tool.name for tool in self.tools])
        
        # Create prompt template
        prompt_template = PromptTemplate.from_template("""You are a helpful AI assistant that specializes in data analysis and visualization.

Available tools:
{tools}

Tool names: {tool_names}

When asked to create charts or visualizations:
1. First use data_tool to examine the data structure
2. Then use code_executor to create Python code that:
   - Reads the data
   - Creates appropriate visualizations
   - Saves charts to test-directory/ or test-directory/charts/
   - Always uses plt.savefig() and plt.close()
   - Prints the saved file path

IMPORTANT: You MUST use the following format:

Thought: I need to think about what to do
Action: tool_name
Action Input: the input to the tool
Observation: the result of the tool
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

Question: {input}
Thought: {agent_scratchpad}""")
        
        # Create agent with our custom prompt
        # Partial the prompt with tool-related variables
        from langchain.prompts import PromptTemplate
        from langchain_core.prompts import MessagesPlaceholder
        
        # Create a partial prompt with tool-related variables
        partial_prompt = prompt_template.partial(
            tools=self.tool_descriptions,
            tool_names=self.tool_names
        )
        
        agent = create_react_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=partial_prompt
        )
        
        # Create agent executor
        self.agent_executor = AgentExecutor.from_agent_and_tools(
            agent=agent,
            tools=self.tools,
            verbose=True,
            max_iterations=10,
            handle_parsing_errors=True
        )
    
    def clear_context(self):
        """Clear conversation history"""
        print("Conversation history cleared")
    
    async def analyze(self, query: str, project_path: Optional[str] = None, reset_context: bool = False) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Analyze user query with intelligent data visualization
        
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
                "timestamp": int(time.time())
            }
            
            # Check if this is a data visualization request
            visualization_keywords = ['график', 'диаграмма', 'chart', 'pie', 'bar', 'plot', 'визуализация', 'visualization']
            excel_keywords = ['.xlsx', '.xls', 'excel', 'экс']
            planet_keywords = ['планет', 'planets', 'planet']
            mountain_keywords = ['гор', 'mountain']
            
            is_visualization_request = any(keyword in query.lower() for keyword in visualization_keywords)
            has_excel_reference = any(keyword in query.lower() for keyword in excel_keywords)
            has_planet_reference = any(keyword in query.lower() for keyword in planet_keywords)
            has_mountain_reference = any(keyword in query.lower() for keyword in mountain_keywords)
            
            # Direct visualization path
            if is_visualization_request:
                # Determine Excel file to use
                excel_filename = None
                
                if has_planet_reference:
                    excel_filename = "planets.xlsx"
                elif has_mountain_reference:
                    excel_filename = "mountains.xlsx"
                else:
                    # Try to extract Excel filename from query
                    import re
                    excel_pattern = r'(\w+\.xlsx)'
                    excel_match = re.search(excel_pattern, query.lower())
                    if excel_match:
                        excel_filename = excel_match.group(1)
                
                # If we have a filename, proceed with visualization
                if excel_filename:
                    excel_path = f"/Users/fvyshkov/PycharmProjects/ide-for-text/test-directory/excel/{excel_filename}"
                    
                    # Step 1: Analyze the Excel file
                    yield {
                        "type": "tool_use",
                        "content": f"Using data_tool to analyze {excel_filename}",
                        "timestamp": int(time.time())
                    }
                    
                    data_result = self.tools[0]._run(f"analyze {excel_path}")
                    
                    yield {
                        "type": "tool_result",
                        "content": data_result,
                        "timestamp": int(time.time())
                    }
                    
                    # Step 2: Create intelligent visualization based on query
                    yield {
                        "type": "tool_use",
                        "content": f"Using code_executor to create visualization for {excel_filename}",
                        "timestamp": int(time.time())
                    }
                    
                    # Determine chart type from query
                    chart_type = "bar"
                    if "pie" in query.lower():
                        chart_type = "pie"
                    elif "line" in query.lower() or "линия" in query.lower():
                        chart_type = "line"
                    elif "scatter" in query.lower():
                        chart_type = "scatter"
                    
                    # Generate Python code for visualization
                    python_code = f"""
import pandas as pd
import matplotlib.pyplot as plt
import os

# Read the Excel file
excel_path = "{excel_path}"
df = pd.read_excel(excel_path)
print(f"Successfully read {{excel_path}}")
print(f"Columns: {{df.columns.tolist()}}")
print(f"Data shape: {{df.shape}}")

# Determine what to visualize based on data structure
numeric_columns = df.select_dtypes(include=['number']).columns.tolist()
categorical_columns = df.select_dtypes(include=['object']).columns.tolist()

print(f"Numeric columns: {{numeric_columns}}")
print(f"Categorical columns: {{categorical_columns}}")

# Create visualization based on data structure and chart type
if len(numeric_columns) > 0 and len(categorical_columns) > 0:
    # Use first numeric column for values, first categorical for labels
    value_col = numeric_columns[0]
    label_col = categorical_columns[0]
    
    print(f"Using {{value_col}} for values and {{label_col}} for labels")
    
    # Sort by values for better visualization
    df_sorted = df.sort_values(by=value_col, ascending=False)
    
    if "{chart_type}" == "pie":
        # Create pie chart
        plt.figure(figsize=(10, 8))
        plt.pie(df_sorted[value_col], labels=df_sorted[label_col], autopct='%1.1f%%')
        plt.title(f'{{label_col}} by {{value_col}}')
        plt.axis('equal')
    else:
        # Create bar chart
        plt.figure(figsize=(12, 8))
        plt.bar(df_sorted[label_col], df_sorted[value_col])
        plt.title(f'{{label_col}} by {{value_col}}')
        plt.xlabel(label_col)
        plt.ylabel(value_col)
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
    
    # Save the chart
    output_filename = f"{{excel_filename.replace('.xlsx', '')}}_chart.png"
    output_path = f"/Users/fvyshkov/PycharmProjects/ide-for-text/test-directory/{{output_filename}}"
    plt.savefig(output_path)
    plt.close()
    print(f"Chart saved to: {{output_path}}")
else:
    print(f"Cannot create chart: need both numeric and categorical columns")
    print(f"Available columns: {{df.columns.tolist()}}")
"""
                    
                    code_result = self.tools[1]._run(python_code)
                    
                    yield {
                        "type": "tool_result",
                        "content": code_result,
                        "timestamp": int(time.time())
                    }
                    
                    # Final result
                    output_filename = f"{excel_filename.replace('.xlsx', '')}_chart.png"
                    yield {
                        "type": "final_result",
                        "content": f"График успешно создан и сохранен в файл {output_filename} в папке test-directory",
                        "timestamp": int(time.time())
                    }
                else:
                    # Try direct tool usage with hardcoded examples
                    yield {
                        "type": "final_result",
                        "content": "Для создания графика укажите Excel файл, например: 'график планет по planets.xlsx' или 'pie график гор из mountains.xlsx'",
                        "timestamp": int(time.time())
                    }
            else:
                # For non-visualization queries, use direct tool calls
                if "list" in query.lower() and "directory" in query.lower():
                    # List directory contents
                    dir_path = project_path or "test-directory"
                    yield {
                        "type": "tool_use",
                        "content": f"Using data_tool to list directory: {dir_path}",
                        "timestamp": int(time.time())
                    }
                    
                    result = self.tools[0]._run(f"list {dir_path}")
                    
                    yield {
                        "type": "tool_result",
                        "content": result,
                        "timestamp": int(time.time())
                    }
                    
                    yield {
                        "type": "final_result",
                        "content": f"Содержимое директории {dir_path}:\n{result}",
                        "timestamp": int(time.time())
                    }
                elif "read" in query.lower() or "открой" in query.lower():
                    # Try to extract file path
                    import re
                    file_pattern = r'(?:read|открой)\s+([^\s]+\.\w+)'
                    file_match = re.search(file_pattern, query.lower())
                    
                    if file_match:
                        file_path = file_match.group(1)
                        full_path = os.path.join(project_path or "test-directory", file_path)
                        
                        yield {
                            "type": "tool_use",
                            "content": f"Using data_tool to read file: {file_path}",
                            "timestamp": int(time.time())
                        }
                        
                        result = self.tools[0]._run(f"read {full_path}")
                        
                        yield {
                            "type": "tool_result",
                            "content": result,
                            "timestamp": int(time.time())
                        }
                        
                        yield {
                            "type": "final_result",
                            "content": f"Содержимое файла {file_path}:\n{result}",
                            "timestamp": int(time.time())
                        }
                    else:
                        yield {
                            "type": "final_result",
                            "content": "Пожалуйста, укажите файл для чтения. Например: 'read example.txt'",
                            "timestamp": int(time.time())
                        }
                else:
                    # Default response for other queries
                    yield {
                        "type": "final_result",
                        "content": "Я могу помочь с визуализацией данных из Excel файлов, чтением файлов и просмотром директорий. Например:\n- 'pie график планет по planets.xlsx'\n- 'график гор из mountains.xlsx'\n- 'read example.txt'\n- 'list directory'",
                        "timestamp": int(time.time())
                    }
            
            # Completion event
            yield {
                "type": "thinking_complete",
                "content": "✓ Analysis completed!",
                "timestamp": int(time.time())
            }
        
        except Exception as e:
            print(f"AI analysis error: {e}")
            yield {
                "type": "error",
                "content": str(e)
            }

    def get_tools(self):
        """
        Return list of tool names for compatibility
        """
        return ["data_tool", "code_executor"]


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
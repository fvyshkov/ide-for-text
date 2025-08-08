"""
Direct AI Agent with Claude 3.5 - Simple implementation without LangChain
Uses direct tool calls for data analysis and visualization
"""
import os
import time
import json
import asyncio
import re
from typing import AsyncGenerator, Dict, Any, Optional, List
from dotenv import load_dotenv
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# Load environment variables
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))


class FileSearchTool:
    """Tool for searching files in the project structure"""
    name = "file_search"
    
    def _run(self, input_str: str) -> str:
        """
        Search for files in the project structure
        
        Args:
            input_str: Search query in format "search_query [file_type]"
                       where file_type is optional and can be 'excel', 'csv', 'json', 'text', etc.
        
        Returns:
            List of matching files with paths
        """
        print(f"DEBUG: FileSearchTool._run called with input_str: {input_str}")
        try:
            # Get project root
            backend_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(backend_dir)
            
            # Parse search query and optional file type
            parts = input_str.split()
            search_query = input_str.lower()
            file_type = None
            
            # Check if file type is specified
            file_type_keywords = ['excel', 'xlsx', 'csv', 'json', 'txt', 'text']
            for keyword in file_type_keywords:
                if keyword in parts:
                    file_type = keyword
                    # Remove file type from search query
                    search_query = search_query.replace(keyword, '').strip()
                    break
            
            # Define search root - default to test-directory
            search_root = os.path.join(project_root, "test-directory")
            
            # Map file type to extensions
            extension_map = {
                'excel': ['.xlsx', '.xls'],
                'xlsx': ['.xlsx'],
                'xls': ['.xls'],
                'csv': ['.csv'],
                'json': ['.json'],
                'txt': ['.txt'],
                'text': ['.txt', '.md', '.text']
            }
            
            target_extensions = extension_map.get(file_type, None) if file_type else None
            
            # Keywords to match in filenames
            keywords = search_query.split()
            
            # Search results
            results = []
            
            # Walk through directory structure
            for root, dirs, files in os.walk(search_root):
                for file in files:
                    # Skip hidden files and temporary Excel files (starting with ~$)
                    if file.startswith('.') or file.startswith('~$'):
                        continue
                    
                    # Check file extension if type is specified
                    if target_extensions:
                        if not any(file.lower().endswith(ext) for ext in target_extensions):
                            continue
                    
                    # Check if any keyword matches the filename
                    file_lower = file.lower()
                    path_lower = os.path.join(root, file).lower()
                    
                    # If no specific keywords, include all files of the specified type
                    if not keywords or any(keyword in file_lower for keyword in keywords):
                        rel_path = os.path.relpath(os.path.join(root, file), project_root)
                        abs_path = os.path.join(root, file)
                        
                        # Get file info
                        size = os.path.getsize(abs_path)
                        modified = time.ctime(os.path.getmtime(abs_path))
                        
                        results.append({
                            'name': file,
                            'path': abs_path,
                            'rel_path': rel_path,
                            'size': size,
                            'modified': modified
                        })
            
            # Sort results by relevance (exact matches first, then partial matches)
            if keywords:
                # Score each result by number of matching keywords
                for result in results:
                    score = 0
                    for keyword in keywords:
                        if keyword in result['name'].lower():
                            score += 2  # Higher score for filename matches
                        elif keyword in result['path'].lower():
                            score += 1  # Lower score for path matches
                    result['score'] = score
                
                # Sort by score (descending)
                results.sort(key=lambda x: x['score'], reverse=True)
            
            # Format results
            if results:
                formatted_results = ["Found files:"]
                for i, result in enumerate(results[:10]):  # Limit to top 10 results
                    formatted_results.append(f"{i+1}. {result['name']} ({result['rel_path']}, {result['size']} bytes)")
                
                if len(results) > 10:
                    formatted_results.append(f"... and {len(results) - 10} more files")
                
                return "\n".join(formatted_results)
            else:
                return f"No files found matching '{input_str}'"
                
        except Exception as e:
            return f"Error in file_search: {str(e)}"


class UniversalDataTool:
    """Universal tool for all data operations - reading, analyzing, transforming"""
    name = "data_tool"
    
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
                # Check if path is absolute or relative
                if not os.path.isabs(arguments):
                    # Try to find the file in test-directory
                    test_dir = os.path.join(project_root, "test-directory")
                    possible_paths = [
                        arguments,  # As is
                        os.path.join(test_dir, arguments),  # In test-directory
                        os.path.join(test_dir, "excel", arguments),  # In test-directory/excel
                        os.path.join(test_dir, "data-samples", arguments)  # In test-directory/data-samples
                    ]
                    
                    # Try each path
                    file_path = None
                    for path in possible_paths:
                        if os.path.exists(path):
                            file_path = path
                            break
                    
                    if not file_path:
                        return f"Error: File '{arguments}' not found in any standard locations"
                else:
                    file_path = arguments
                    if not os.path.exists(file_path):
                        return f"Error: File '{file_path}' not found"
                
                # Detect file type and read accordingly
                if file_path.endswith(('.xlsx', '.xls')):
                    df = pd.read_excel(file_path)
                    return f"Excel file with {len(df)} rows, columns: {list(df.columns)}\n\nFirst 5 rows:\n{df.head().to_string()}"
                elif file_path.endswith('.csv'):
                    df = pd.read_csv(file_path)
                    return f"CSV file with {len(df)} rows, columns: {list(df.columns)}\n\nFirst 5 rows:\n{df.head().to_string()}"
                elif file_path.endswith('.json'):
                    with open(file_path, 'r') as f:
                        data = json.load(f)
                    return f"JSON content:\n{json.dumps(data, indent=2)[:1000]}"
                else:
                    # Text file
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    return f"File content:\n{content}"
            
            elif operation == "list":
                # Handle relative paths
                if not os.path.isabs(arguments):
                    dir_path = os.path.join(project_root, arguments) if arguments != '.' else project_root
                else:
                    dir_path = arguments
                
                if not os.path.exists(dir_path):
                    return f"Error: Directory '{arguments}' not found"
                
                items = []
                for item in sorted(os.listdir(dir_path)):
                    # Skip hidden files and temporary Excel files
                    if item.startswith('.') or item.startswith('~$'):
                        continue
                        
                    item_path = os.path.join(dir_path, item)
                    if os.path.isdir(item_path):
                        items.append(f"[DIR]  {item}/")
                    else:
                        size = os.path.getsize(item_path)
                        items.append(f"[FILE] {item} ({size} bytes)")
                
                return f"Contents of '{arguments or 'root'}':\n" + (('\n'.join(items)) if items else 'No items found')
            
            elif operation == "analyze":
                # Handle relative paths similar to read operation
                if not os.path.isabs(arguments):
                    # Try to find the file in test-directory
                    test_dir = os.path.join(project_root, "test-directory")
                    possible_paths = [
                        arguments,  # As is
                        os.path.join(test_dir, arguments),  # In test-directory
                        os.path.join(test_dir, "excel", arguments),  # In test-directory/excel
                        os.path.join(test_dir, "data-samples", arguments)  # In test-directory/data-samples
                    ]
                    
                    # Try each path
                    file_path = None
                    for path in possible_paths:
                        if os.path.exists(path):
                            file_path = path
                            break
                    
                    if not file_path:
                        return f"Error: File '{arguments}' not found in any standard locations"
                else:
                    file_path = arguments
                    if not os.path.exists(file_path):
                        return f"Error: File '{file_path}' not found"
                
                stat = os.stat(file_path)
                info = [
                    f"Path: {file_path}",
                    f"Size: {stat.st_size} bytes",
                    f"Type: {'Directory' if os.path.isdir(file_path) else 'File'}",
                    f"Modified: {time.ctime(stat.st_mtime)}"
                ]
                
                # Additional analysis for data files
                if file_path.endswith(('.xlsx', '.xls', '.csv')):
                    try:
                        df = pd.read_excel(file_path) if file_path.endswith(('.xlsx', '.xls')) else pd.read_csv(file_path)
                        info.extend([
                            f"Rows: {len(df)}",
                            f"Columns: {list(df.columns)}",
                            f"Data types: {df.dtypes.to_dict()}",
                            f"Missing values: {df.isnull().sum().to_dict()}"
                        ])
                    except Exception as e:
                        info.append(f"Error analyzing data: {str(e)}")
                
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
                
                # Handle relative paths
                if not os.path.isabs(file_path):
                    full_path = os.path.join(project_root, file_path)
                else:
                    full_path = file_path
                
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


class CodeExecutor:
    """Execute Python code for analysis and visualization"""
    name = "code_executor"
    
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


class DirectAIAgent:
    """Direct AI Agent for data analysis and visualization without LangChain"""
    
    def __init__(self, websocket=None):
        # Initialize tools
        self.tools = [
            FileSearchTool(),
            UniversalDataTool(),
            CodeExecutor()
        ]
        self.websocket = websocket
        
        # Get project root directory
        backend_dir = os.path.dirname(os.path.abspath(__file__))
        self.project_root = os.path.dirname(backend_dir)
        self.data_dir = os.path.join(self.project_root, "test-directory")
    
    def clear_context(self):
        """Clear conversation history (placeholder for compatibility)"""
        print("Context cleared")
    
    async def analyze(self, query: str, project_path: Optional[str] = None, reset_context: bool = False, attached_file_paths: Optional[List[str]] = None) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Analyze user query with direct tool usage and tool chaining
        
        Args:
            query: User's request
            project_path: Optional project context
            reset_context: Whether to clear context
            
        Yields:
            Processed events
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
            
            # Update data directory if project_path is provided
            data_dir = os.path.join(self.project_root, project_path) if project_path else self.data_dir
            output_dir = data_dir  # Default output directory
            
            # Normalize attached file paths (if provided)
            explicit_attached_files: List[str] = []
            if attached_file_paths:
                for p in attached_file_paths:
                    abs_p = p if os.path.isabs(p) else os.path.join(self.project_root, p)
                    if os.path.exists(abs_p):
                        explicit_attached_files.append(abs_p)

            # Step 1: Analyze the query to determine intent
            data_operations = ['анализ', 'analyze', 'график', 'chart', 'plot', 'визуализация', 'visualization',
                              'преобразуй', 'transform', 'сравни', 'compare', 'статистика', 'statistics',
                              'диаграмма', 'ввп', 'gdp', 'создай']
            
            file_operations = ['read', 'открой', 'list', 'покажи', 'найди', 'find', 'search']
            
            # Determine operation type
            is_data_operation = any(keyword in query.lower() for keyword in data_operations)
            is_file_operation = any(keyword in query.lower() for keyword in file_operations)
            
            # Отладочный print
            print(f"DEBUG: is_data_operation = {is_data_operation}")
            print(f"DEBUG: query = {query}")
            print(f"DEBUG: data_operations = {data_operations}")
            
            # Step 2: For data operations, we need to find relevant data files first
            data_files = []

            # If user attached files in chips, they take precedence
            if explicit_attached_files:
                data_files.extend(explicit_attached_files)
                yield {
                    "type": "tool_result",
                    "content": f"Using attached files: {', '.join(explicit_attached_files)}",
                    "timestamp": int(time.time())
                }
            
            if is_data_operation and not data_files:
                # First, check for explicit file references in the query
                import re
                file_pattern = r'(\w+\.(xlsx|xls|csv|json))'
                file_matches = re.findall(file_pattern, query.lower())
                
                explicit_files = [match[0] for match in file_matches]
                
                # If explicit files mentioned, use file search tool to find them
                if explicit_files:
                    for file_name in explicit_files:
                        yield {
                            "type": "tool_use",
                            "content": f"Searching for file: {file_name}",
                            "timestamp": int(time.time())
                        }
                        
                        # Use file search tool
                        search_result = self.tools[0]._run(file_name)
                        
                        yield {
                            "type": "tool_result",
                            "content": search_result,
                            "timestamp": int(time.time())
                        }
                        
                        # Parse search results to get file paths
                        if "Found files:" in search_result:
                            lines = search_result.split('\n')[1:]  # Skip header
                            for line in lines:
                                if line.startswith('...'):  # Skip "and X more files" line
                                    continue
                                    
                                if '. ' in line:
                                    # Extract file path
                                    parts = line.split('(', 1)
                                    if len(parts) > 1:
                                        rel_path = parts[1].split(',')[0]
                                        file_path = os.path.join(self.project_root, rel_path)
                                        if os.path.exists(file_path):
                                            data_files.append(file_path)
                
                # If no explicit files or no files found, try to infer from keywords
                if not data_files:
                    # Extract potential data subjects from the query
                    data_subjects = []
                    
                    # Common data subjects that might be in the query
                    subject_keywords = {
                        'планет': 'planets',
                        'planet': 'planets',
                        'гор': 'mountains',
                        'mountain': 'mountains',
                        'стран': 'countries',
                        'country': 'countries',
                        'элемент': 'elements',
                        'element': 'elements'
                    }
                    
                    for keyword, subject in subject_keywords.items():
                        if keyword in query.lower():
                            data_subjects.append(subject)
                    
                    # If we found potential data subjects, search for related files
                    if data_subjects:
                        for subject in data_subjects:
                            yield {
                                "type": "tool_use",
                                "content": f"Searching for files related to: {subject}",
                                "timestamp": int(time.time())
                            }
                            
                            # Use file search tool with subject and excel type
                            search_result = self.tools[0]._run(f"{subject} excel")
                            
                            yield {
                                "type": "tool_result",
                                "content": search_result,
                                "timestamp": int(time.time())
                            }
                            
                            # Parse search results to get file paths
                            if "Found files:" in search_result:
                                lines = search_result.split('\n')[1:]  # Skip header
                                for line in lines:
                                    if line.startswith('...'):  # Skip "and X more files" line
                                        continue
                                        
                                    if '. ' in line:
                                        # Extract file path
                                        parts = line.split('(', 1)
                                        if len(parts) > 1:
                                            rel_path = parts[1].split(',')[0]
                                            file_path = os.path.join(self.project_root, rel_path)
                                            if os.path.exists(file_path):
                                                data_files.append(file_path)
                    
                    # If still no files found, search for Excel files in general
                    if not data_files:
                        yield {
                            "type": "tool_use",
                            "content": "Searching for Excel files",
                            "timestamp": int(time.time())
                        }
                        
                        # Use file search tool with excel type only
                        search_result = self.tools[0]._run("excel")
                        
                        yield {
                            "type": "tool_result",
                            "content": search_result,
                            "timestamp": int(time.time())
                        }
                        
                        # Parse search results to get file paths
                        if "Found files:" in search_result:
                            lines = search_result.split('\n')[1:]  # Skip header
                            for line in lines:
                                if line.startswith('...'):  # Skip "and X more files" line
                                    continue
                                    
                                if '. ' in line:
                                    # Extract file path
                                    parts = line.split('(', 1)
                                    if len(parts) > 1:
                                        rel_path = parts[1].split(',')[0]
                                        file_path = os.path.join(self.project_root, rel_path)
                                        if os.path.exists(file_path):
                                            data_files.append(file_path)
            
            # Step 3: Determine operation type based on query
            operation_type = "unknown"
            
            # Check for visualization request
            viz_keywords = ['график', 'диаграмма', 'chart', 'pie', 'bar', 'plot', 'визуализация', 'visualization', 
                            'создай', 'ввп', 'gdp']
            if any(keyword in query.lower() for keyword in viz_keywords):
                operation_type = "visualization"
            
            # Отладочный print
            print(f"DEBUG: operation_type = {operation_type}")
            print(f"DEBUG: viz_keywords = {viz_keywords}")
            print(f"DEBUG: query.lower() = {query.lower()}")
            
            # Check for analysis request
            analysis_keywords = ['анализ', 'analyze', 'statistics', 'статистика', 'сравни', 'compare']
            if any(keyword in query.lower() for keyword in analysis_keywords):
                operation_type = "analysis"
            
            # Check for transformation request
            transform_keywords = ['преобразуй', 'transform', 'convert', 'merge', 'join', 'объедини']
            if any(keyword in query.lower() for keyword in transform_keywords):
                operation_type = "transformation"
            
            # Check for file operations
            if "list" in query.lower() and "directory" in query.lower():
                operation_type = "list_directory"
            elif "read" in query.lower() or "открой" in query.lower():
                operation_type = "read_file"
            elif "find" in query.lower() or "search" in query.lower() or "найди" in query.lower() or "поиск" in query.lower():
                operation_type = "search_files"
            
            # Step 4: Execute the appropriate operation
            if operation_type == "search_files":
                # Extract search terms
                search_terms = query.lower()
                for term in ["find", "search", "найди", "поиск", "файл", "file"]:
                    search_terms = search_terms.replace(term, "").strip()
                
                yield {
                    "type": "tool_use",
                    "content": f"Searching for files matching: {search_terms}",
                    "timestamp": int(time.time())
                }
                
                # Use file search tool
                search_result = self.tools[0]._run(search_terms)
                
                yield {
                    "type": "tool_result",
                    "content": search_result,
                    "timestamp": int(time.time())
                }
                
                yield {
                    "type": "final_result",
                    "content": search_result,
                    "timestamp": int(time.time())
                }
                
            elif operation_type == "list_directory":
                # Extract directory path from query if present
                dir_path = None
                
                # Check if query contains a specific path
                if "test-directory" in query:
                    parts = query.split("test-directory")
                    if len(parts) > 1 and parts[1].strip():
                        # Extract path after "test-directory"
                        sub_path = parts[1].strip()
                        # Remove any leading or trailing slashes
                        sub_path = sub_path.strip("/")
                        dir_path = os.path.join("test-directory", sub_path)
                    else:
                        dir_path = "test-directory"
                else:
                    # Try to extract with regex
                    dir_pattern = r'(?:list|directory|dir|папк[аиу])\s+([^\s]+)'
                    import re
                    dir_match = re.search(dir_pattern, query.lower())
                    
                    if dir_match:
                        dir_path = dir_match.group(1)
                
                # Default to project_path or data_dir if no path specified
                if not dir_path:
                    dir_path = project_path or "test-directory"
                
                yield {
                    "type": "tool_use",
                    "content": f"Using data_tool to list directory: {dir_path}",
                    "timestamp": int(time.time())
                }
                
                result = self.tools[1]._run(f"list {dir_path}")
                
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
                
            elif operation_type == "read_file":
                # Try to extract file path
                file_pattern = r'(?:read|открой)\s+([^\s]+\.\w+)'
                import re
                file_match = re.search(file_pattern, query.lower())
                
                if file_match:
                    file_name = file_match.group(1)
                    
                    # First search for the file
                    yield {
                        "type": "tool_use",
                        "content": f"Searching for file: {file_name}",
                        "timestamp": int(time.time())
                    }
                    
                    search_result = self.tools[0]._run(file_name)
                    
                    yield {
                        "type": "tool_result",
                        "content": search_result,
                        "timestamp": int(time.time())
                    }
                    
                    # Try to find the file path from search results
                    file_path = None
                    if "Found files:" in search_result:
                        lines = search_result.split('\n')[1:]  # Skip header
                        if lines and '. ' in lines[0]:  # Take first result
                            parts = lines[0].split('(', 1)
                            if len(parts) > 1:
                                rel_path = parts[1].split(',')[0]
                                file_path = os.path.join(self.project_root, rel_path)
                    
                    # If file not found in search, try direct paths
                    if not file_path or not os.path.exists(file_path):
                        possible_paths = [
                            os.path.join(project_path or data_dir, file_name),
                            os.path.join(data_dir, file_name),
                            os.path.join(data_dir, "excel", file_name),
                            os.path.join(data_dir, "data-samples", file_name)
                        ]
                        
                        for path in possible_paths:
                            if os.path.exists(path):
                                file_path = path
                                break
                    
                    if file_path and os.path.exists(file_path):
                        yield {
                            "type": "tool_use",
                            "content": f"Reading file: {file_path}",
                            "timestamp": int(time.time())
                        }
                        
                        result = self.tools[1]._run(f"read {file_path}")
                        
                        yield {
                            "type": "tool_result",
                            "content": result,
                            "timestamp": int(time.time())
                        }
                        
                        yield {
                            "type": "final_result",
                            "content": f"Содержимое файла {os.path.basename(file_path)}:\n{result}",
                            "timestamp": int(time.time())
                        }
                    else:
                        yield {
                            "type": "final_result",
                            "content": f"Файл '{file_name}' не найден.",
                            "timestamp": int(time.time())
                        }
                else:
                    yield {
                        "type": "final_result",
                        "content": "Пожалуйста, укажите файл для чтения. Например: 'read example.txt'",
                        "timestamp": int(time.time())
                    }
                    
            elif (operation_type in ["visualization", "analysis", "transformation"]):
                # Check if we have data files
                if not data_files:
                    yield {
                        "type": "final_result",
                        "content": "Не удалось найти подходящие файлы данных для выполнения операции. Пожалуйста, укажите конкретный файл.",
                        "timestamp": int(time.time())
                    }
                    return
                
                # First, analyze the data files
                for file_path in data_files:
                    file_name = os.path.basename(file_path)
                    
                    yield {
                        "type": "tool_use",
                        "content": f"Using data_tool to analyze {file_name}",
                        "timestamp": int(time.time())
                    }
                    
                    data_result = self.tools[1]._run(f"analyze {file_path}")
                    
                    yield {
                        "type": "tool_result",
                        "content": data_result,
                        "timestamp": int(time.time())
                    }
                
                # Now generate appropriate code based on the operation type and query
                yield {
                    "type": "tool_use",
                    "content": f"Using code_executor to process data",
                    "timestamp": int(time.time())
                }
                
                # Generate dynamic Python code based on the query and data files
                main_file = data_files[0]
                file_name = os.path.basename(main_file)
                file_stem = os.path.splitext(file_name)[0]
                
                # Determine chart type if it's a visualization
                chart_type = "bar"  # Default
                if operation_type == "visualization":
                    if "pie" in query.lower():
                        chart_type = "pie"
                    elif "line" in query.lower() or "линия" in query.lower():
                        chart_type = "line"
                    elif "scatter" in query.lower() or "точечн" in query.lower():
                        chart_type = "scatter"
                    elif "area" in query.lower() or "площад" in query.lower():
                        chart_type = "area"
                
                # Generate timestamp for unique filenames
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                
                # Generate appropriate output filename based on operation
                output_filename = ""
                if operation_type == "visualization":
                    output_filename = f"{file_stem}_{chart_type}_chart_{timestamp}.png"
                elif operation_type == "analysis":
                    output_filename = f"{file_stem}_analysis_{timestamp}.txt"
                elif operation_type == "transformation":
                    output_filename = f"{file_stem}_transformed_{timestamp}.csv"
                
                # Generate Python code for the operation
                python_code = f"""
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os
import json
from datetime import datetime

# Create output directory if needed
output_dir = "{output_dir}"
os.makedirs(output_dir, exist_ok=True)

# Current timestamp for unique filenames
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

# Read the data file(s)
main_file = "{main_file}"
print(f"Processing file: {{main_file}}")

# Load data based on file extension
if main_file.endswith('.xlsx') or main_file.endswith('.xls'):
    df = pd.read_excel(main_file)
elif main_file.endswith('.csv'):
    df = pd.read_csv(main_file)
else:
    raise ValueError(f"Unsupported file format: {{main_file}}")

print(f"Successfully read {{main_file}}")
print(f"Columns: {{df.columns.tolist()}}")
print(f"Data shape: {{df.shape}}")

# Analyze data structure
numeric_columns = df.select_dtypes(include=['number']).columns.tolist()
categorical_columns = df.select_dtypes(include=['object']).columns.tolist()
date_columns = df.select_dtypes(include=['datetime']).columns.tolist()

print(f"Numeric columns: {{numeric_columns}}")
print(f"Categorical columns: {{categorical_columns}}")
print(f"Date columns: {{date_columns}}")

"""

                # Add operation-specific code
                if operation_type == "visualization":
                    python_code += f"""
# Create visualization based on data structure and query
if len(numeric_columns) > 0:
    # Determine what to visualize
    value_col = numeric_columns[0]  # Default to first numeric column
    
    # If we have categorical columns, use the first one for labels
    if categorical_columns:
        label_col = categorical_columns[0]
        
        # Sort by values for better visualization
        df_sorted = df.sort_values(by=value_col, ascending=False)
        
        if "{chart_type}" == "pie":
            # Create pie chart
            plt.figure(figsize=(10, 8))
            plt.pie(df_sorted[value_col], labels=df_sorted[label_col], autopct='%1.1f%%')
            plt.title(f'{{label_col}} by {{value_col}}')
            plt.axis('equal')
        elif "{chart_type}" == "line":
            # Create line chart
            plt.figure(figsize=(12, 8))
            plt.plot(df_sorted[label_col], df_sorted[value_col], marker='o')
            plt.title(f'{{label_col}} by {{value_col}}')
            plt.xlabel(label_col)
            plt.ylabel(value_col)
            plt.xticks(rotation=45, ha='right')
            plt.grid(True)
            plt.tight_layout()
        else:
            # Default to bar chart
            plt.figure(figsize=(12, 8))
            plt.bar(df_sorted[label_col], df_sorted[value_col])
            plt.title(f'{{label_col}} by {{value_col}}')
            plt.xlabel(label_col)
            plt.ylabel(value_col)
            plt.xticks(rotation=45, ha='right')
            plt.tight_layout()
    else:
        # No categorical columns, create histogram of numeric data
        plt.figure(figsize=(12, 8))
        plt.hist(df[value_col], bins=10)
        plt.title(f'Distribution of {{value_col}}')
        plt.xlabel(value_col)
        plt.ylabel('Frequency')
        plt.grid(True)
        plt.tight_layout()
    
    # Save the chart
    output_path = os.path.join("{output_dir}", "{output_filename}")
    plt.savefig(output_path)
    plt.close()
    print(f"Chart saved to: {{output_path}}")
else:
    print(f"Cannot create chart: no numeric columns found in the data")
    print(f"Available columns: {{df.columns.tolist()}}")
"""
                elif operation_type == "analysis":
                    python_code += f"""
# Perform statistical analysis on the data
analysis_results = []

# Basic statistics for numeric columns
if numeric_columns:
    analysis_results.append("STATISTICAL ANALYSIS")
    analysis_results.append("-" * 50)
    
    # Get basic statistics
    stats = df[numeric_columns].describe()
    analysis_results.append(f"Basic Statistics:\\n{{stats}}\\n")
    
    # Correlation analysis if we have multiple numeric columns
    if len(numeric_columns) > 1:
        analysis_results.append("Correlation Matrix:")
        corr = df[numeric_columns].corr()
        analysis_results.append(f"{{corr}}\\n")
    
    # Top and bottom values
    for num_col in numeric_columns:
        analysis_results.append(f"Top 5 by value:")
        top_cols = [num_col]
        if categorical_columns:
            top_cols.append(categorical_columns[0])
        top = df.nlargest(5, num_col)[top_cols]
        analysis_results.append(f"{{top}}\\n")

# Categorical analysis
if categorical_columns:
    analysis_results.append("CATEGORICAL ANALYSIS")
    analysis_results.append("-" * 50)
    
    for col in categorical_columns:
        analysis_results.append(f"Value counts for {{col}}:")
        counts = df[col].value_counts()
        analysis_results.append(f"{{counts}}\\n")

# Save analysis results
output_path = os.path.join("{output_dir}", "{output_filename}")
with open(output_path, 'w') as f:
    f.write("\\n".join(str(item) for item in analysis_results))

print(f"Analysis saved to: {{output_path}}")
"""
                elif operation_type == "transformation":
                    python_code += f"""
# Transform the data based on the query
transformed_df = df.copy()

# Example transformations based on query
query = "{query.lower()}"

# Check for specific transformations
if "sort" in query or "сортировка" in query:
    # Sort by first numeric column if available
    if numeric_columns:
        sort_col = numeric_columns[0]
        transformed_df = transformed_df.sort_values(by=sort_col, ascending=False)
        print(f"Sorted data by {{sort_col}}")

# Filter operations
if "filter" in query or "фильтр" in query:
    # Simple filtering example - keep only top half of values
    if numeric_columns:
        filter_col = numeric_columns[0]
        median = transformed_df[filter_col].median()
        transformed_df = transformed_df[transformed_df[filter_col] > median]
        print(f"Filtered data where {{filter_col}} > {{median}}")

# Aggregation operations
if "group" in query or "группировка" in query:
    # Group by first categorical column and aggregate numeric columns
    if categorical_columns and numeric_columns:
        group_col = categorical_columns[0]
        agg_dict = dict()
        for num_col in numeric_columns:
            agg_dict[num_col] = 'mean'
        transformed_df = transformed_df.groupby(group_col).agg(agg_dict).reset_index()
        print(f"Grouped data by {{group_col}} and calculated means")

# Save transformed data
output_path = os.path.join("{output_dir}", "{output_filename}")
transformed_df.to_csv(output_path, index=False)
print(f"Transformed data saved to: {{output_path}}")
"""

                # Execute the generated code
                code_result = self.tools[2]._run(python_code)
                
                yield {
                    "type": "tool_result",
                    "content": code_result,
                    "timestamp": int(time.time())
                }
                
                # Check if file was created successfully
                output_path = os.path.join(output_dir, output_filename)
                success = os.path.exists(output_path)
                
                # Final result message based on operation type and success
                result_message = ""
                if success:
                    if operation_type == "visualization":
                        result_message = f"График успешно создан и сохранен в файл {output_filename} в папке test-directory"
                    elif operation_type == "analysis":
                        result_message = f"Анализ данных успешно выполнен и сохранен в файл {output_filename} в папке test-directory"
                    elif operation_type == "transformation":
                        result_message = f"Данные успешно преобразованы и сохранены в файл {output_filename} в папке test-directory"
                else:
                    # Try to extract error message from code result
                    error_message = "Неизвестная ошибка"
                    if "Error" in code_result:
                        error_lines = [line for line in code_result.split('\n') if "Error" in line]
                        if error_lines:
                            error_message = error_lines[0]
                    
                    result_message = f"Произошла ошибка при выполнении операции: {error_message}"
                
                yield {
                    "type": "final_result",
                    "content": result_message,
                    "timestamp": int(time.time())
                }
                
            else:
                # No data files found or unknown operation
                yield {
                    "type": "final_result",
                    "content": """Я могу помочь с анализом данных, визуализацией и преобразованием. Примеры запросов:
- 'создай график планет по planets.xlsx'
- 'pie график распределения стран по странам'
- 'анализ данных в файле mountains.xlsx'
- 'преобразуй данные в файле elements.xlsx'
- 'read example.txt'
- 'list directory test-directory'""",
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
        """Return list of tool names for compatibility"""
        return ["file_search", "data_tool", "code_executor"]


# Global agent management
agents = {}

def get_direct_agent(session_id: str = "default", websocket=None) -> DirectAIAgent:
    """Get or create a direct agent for a session"""
    global agents
    if session_id not in agents:
        agents[session_id] = DirectAIAgent(websocket)
    return agents[session_id]


# Test function
async def test_direct_agent():
    """Test the direct agent"""
    agent = get_direct_agent("test")
    
    print("Testing Direct AI Agent")
    print("=" * 50)
    
    test_queries = [
        # File operations
        "найди файлы с планетами",
        "list directory test-directory/excel",
        "read planets.xlsx",
        
        # Data operations
        "создай график планет",
        "pie график гор",
        "анализ данных по странам",
        "преобразуй данные из файла elements.xlsx"
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
    asyncio.run(test_direct_agent())

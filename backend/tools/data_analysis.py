"""
Universal data analysis tool for handling various file formats (Excel, CSV, JSON)
"""
from typing import Dict, Any, Union, List
import json
import pandas as pd
from pathlib import Path
from langchain.tools import tool

"""
Advanced data analysis and visualization tools
Uses LangChain and AI for intelligent data processing
"""
import os
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from typing import Optional, Dict, Any

from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import PromptTemplate

class DataAnalysisTool:
    """Handles data analysis for various file formats"""
    
    @staticmethod
    def _read_file(file_path: str) -> pd.DataFrame:
        """Read file into pandas DataFrame based on extension"""
        path = Path(file_path)
        ext = path.suffix.lower()
        
        if ext == '.csv':
            return pd.read_csv(file_path)
        elif ext in ['.xls', '.xlsx']:
            return pd.read_excel(file_path)
        elif ext == '.json':
            with open(file_path, 'r') as f:
                data = json.load(f)
            # Convert JSON to DataFrame
            if isinstance(data, list):
                return pd.DataFrame(data)
            elif isinstance(data, dict):
                # Handle nested dictionary
                return pd.DataFrame([data])
            else:
                raise ValueError(f"Unsupported JSON structure in {file_path}")
        else:
            raise ValueError(f"Unsupported file format: {ext}")

    @tool
    def analyze_data(file_path: str, analysis_type: str = "summary") -> Dict[str, Any]:
        """
        Analyze data from various file formats (CSV, Excel, JSON)
        
        Args:
            file_path: Path to the data file
            analysis_type: Type of analysis to perform:
                - "summary": Basic statistics and info
                - "correlation": Correlation matrix for numeric columns
                - "missing": Missing value analysis
                - "distribution": Distribution analysis for numeric columns
        
        Returns:
            Dict containing analysis results
        """
        try:
            df = DataAnalysisTool._read_file(file_path)
            
            if analysis_type == "summary":
                return {
                    "shape": {"rows": df.shape[0], "columns": df.shape[1]},
                    "columns": df.columns.tolist(),
                    "dtypes": df.dtypes.astype(str).to_dict(),
                    "numeric_summary": df.describe().to_dict(),
                    "sample_data": df.head(5).to_dict(orient='records')
                }
            
            elif analysis_type == "correlation":
                # Only include numeric columns
                numeric_df = df.select_dtypes(include=['int64', 'float64'])
                return {
                    "correlation_matrix": numeric_df.corr().to_dict(),
                    "numeric_columns": numeric_df.columns.tolist()
                }
            
            elif analysis_type == "missing":
                missing_info = df.isnull().sum()
                return {
                    "missing_counts": missing_info.to_dict(),
                    "missing_percentages": (missing_info / len(df) * 100).to_dict()
                }
            
            elif analysis_type == "distribution":
                numeric_df = df.select_dtypes(include=['int64', 'float64'])
                return {
                    "numeric_columns": {
                        col: {
                            "mean": df[col].mean(),
                            "median": df[col].median(),
                            "std": df[col].std(),
                            "min": df[col].min(),
                            "max": df[col].max(),
                            "quartiles": df[col].quantile([0.25, 0.5, 0.75]).to_dict()
                        } for col in numeric_df.columns
                    }
                }
            
            else:
                raise ValueError(f"Unsupported analysis type: {analysis_type}")
                
        except Exception as e:
            return {"error": str(e)}

    @tool
    def query_data(file_path: str, query: str) -> Dict[str, Any]:
        """
        Query data using pandas query syntax
        
        Args:
            file_path: Path to the data file
            query: Pandas query string (e.g. "age > 30 and city == 'New York'")
        
        Returns:
            Dict containing query results
        """
        try:
            df = DataAnalysisTool._read_file(file_path)
            result_df = df.query(query)
            
            return {
                "matched_rows": len(result_df),
                "total_rows": len(df),
                "results": result_df.head(100).to_dict(orient='records')  # Limit to 100 rows
            }
            
        except Exception as e:
            return {"error": str(e)}

    @tool
    def aggregate_data(file_path: str, group_by: List[str], metrics: List[str]) -> Dict[str, Any]:
        """
        Aggregate data by specified columns
        
        Args:
            file_path: Path to the data file
            group_by: List of columns to group by
            metrics: List of metrics to calculate (e.g. ["mean", "sum", "count"])
        
        Returns:
            Dict containing aggregation results
        """
        try:
            df = DataAnalysisTool._read_file(file_path)
            numeric_cols = df.select_dtypes(include=['int64', 'float64']).columns
            
            agg_dict = {col: metrics for col in numeric_cols}
            result_df = df.groupby(group_by).agg(agg_dict)
            
            return {
                "group_by_columns": group_by,
                "metrics": metrics,
                "numeric_columns": numeric_cols.tolist(),
                "results": result_df.to_dict(orient='index')
            }
            
        except Exception as e:
            return {"error": str(e)}

def intelligent_data_visualization(file_path: str) -> Optional[Dict[str, Any]]:
    """
    Intelligently generate data visualization based on file content
    
    Args:
        file_path (str): Path to the data file
    
    Returns:
        Dict with visualization details or None if generation fails
    """
    try:
        # Read file based on extension
        if file_path.endswith('.xlsx'):
            df = pd.read_excel(file_path)
        elif file_path.endswith('.csv'):
            df = pd.read_csv(file_path)
        else:
            raise ValueError("Unsupported file type")
        
        # Initialize LLM for intelligent visualization
        llm = ChatAnthropic(model="claude-3-5-sonnet-20240620")
        
        # Prompt for visualization strategy
        visualization_prompt = PromptTemplate.from_template("""
        Analyze the following data and suggest the most informative visualization:

        Data preview:
        {data_preview}

        Columns: {columns}

        Suggest:
        1. Visualization type (pie, bar, line, scatter)
        2. Columns to use
        3. Key insights to highlight

        Provide a concise recommendation.
        """)
        
        # Prepare data for prompt
        data_preview = df.head().to_string()
        columns = list(df.columns)
        
        # Get visualization recommendation
        visualization_strategy = llm.invoke(
            visualization_prompt.format(
                data_preview=data_preview, 
                columns=columns
            )
        ).content
        
        # Generate visualization based on strategy
        plt.figure(figsize=(10, 6))
        
        # Basic visualization logic (can be expanded)
        if 'pie' in visualization_strategy.lower():
            # Assume first column is labels, second is values
            plt.pie(df.iloc[:, 1], labels=df.iloc[:, 0], autopct='%1.1f%%')
            plt.title(f'Pie Chart: {df.columns[0]} vs {df.columns[1]}')
        elif 'bar' in visualization_strategy.lower():
            df.plot(kind='bar', x=df.columns[0], y=df.columns[1])
            plt.title(f'Bar Chart: {df.columns[0]} vs {df.columns[1]}')
        elif 'line' in visualization_strategy.lower():
            df.plot(kind='line')
            plt.title('Line Chart of Data')
        else:
            df.plot(kind='scatter', x=df.columns[0], y=df.columns[1])
            plt.title(f'Scatter Plot: {df.columns[0]} vs {df.columns[1]}')
        
        # Save visualization
        output_dir = os.path.dirname(file_path)
        output_filename = f"{os.path.splitext(os.path.basename(file_path))[0]}_visualization.png"
        output_path = os.path.join(output_dir, output_filename)
        
        plt.tight_layout()
        plt.savefig(output_path)
        plt.close()
        
        return {
            "chart_path": output_path,
            "strategy": visualization_strategy
        }
    
    except Exception as e:
        print(f"Visualization error: {e}")
        return None
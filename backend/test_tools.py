"""
Test script for tools to check if they work correctly
"""
import os
import sys
from ai_agent_improved import UniversalDataTool, CodeExecutor

def main():
    # Create tools
    data_tool = UniversalDataTool()
    code_executor = CodeExecutor()
    
    # Get project root
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(backend_dir)
    
    # Test data_tool with mountains.xlsx
    excel_path = os.path.join(project_root, "test-directory/excel/mountains.xlsx")
    print("\n=== Testing data_tool with mountains.xlsx ===")
    result = data_tool._run(f"analyze {excel_path}")
    print(result)
    
    # Test data_tool to read mountains.xlsx
    print("\n=== Reading mountains.xlsx ===")
    result = data_tool._run(f"read {excel_path}")
    print(result)
    
    # Test code_executor to create a chart
    print("\n=== Creating chart with code_executor ===")
    python_code = """
import pandas as pd
import matplotlib.pyplot as plt
import os

# Use direct path
excel_path = "/Users/fvyshkov/PycharmProjects/ide-for-text/test-directory/excel/mountains.xlsx"

# Read the Excel file
df = pd.read_excel(excel_path)
print(f"Successfully read {excel_path}")
print(f"Columns: {df.columns.tolist()}")
print(f"Data shape: {df.shape}")

# Sort by height (checking for different possible column names)
height_column = None
for col in df.columns:
    if 'height' in col.lower():
        height_column = col
        break

if height_column:
    print(f"Found height column: {height_column}")
    # Create a simple bar chart of the mountains by height
    top_mountains = df.sort_values(by=height_column, ascending=False)
    plt.figure(figsize=(12, 8))
    plt.bar(top_mountains['Mountain'], top_mountains[height_column])
    plt.title('Mountains by Height')
    plt.xlabel('Mountain')
    plt.ylabel('Height (m)')
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    
    # Save the chart
    output_path = "/Users/fvyshkov/PycharmProjects/ide-for-text/test-directory/mountain_chart.png"
    plt.savefig(output_path)
    plt.close()
    print(f"Chart saved to: {output_path}")
else:
    print(f"No height column found. Available columns: {df.columns.tolist()}")
"""
    result = code_executor._run(python_code)
    print(result)

if __name__ == "__main__":
    main()

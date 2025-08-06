#!/usr/bin/env python3
"""
Demo of file translation using individual tools
"""
import os
from tools.file_operations import read_file_content, write_file_content
from tools.translation import translate_file_content

def demo_translation():
    """Demonstrate file translation step by step"""
    print("Demo: File Translation Step by Step")
    print("=" * 50)
    
    file_path = "test-directory/english_sample.txt"
    output_path = "test-directory/english_sample_russian.txt"
    
    # Step 1: Read the file
    print("Step 1: Reading the English file...")
    read_result = read_file_content.invoke({"file_path": file_path})
    print(f"Read result: {read_result[:200]}...")
    
    # Extract content from the read result
    if "Content of" in read_result:
        content_start = read_result.find(":\n\n") + 3
        content = read_result[content_start:]
    else:
        print("Error reading file")
        return
    
    # Step 2: Translate the content
    print("\nStep 2: Translating to Russian...")
    translation_result = translate_file_content.invoke({
        "file_content": content,
        "target_language": "Russian"
    })
    print(f"Translation result: {translation_result[:200]}...")
    
    # Step 3: Write the translated content
    print("\nStep 3: Saving the Russian version...")
    write_result = write_file_content.invoke({
        "file_path": output_path,
        "content": translation_result
    })
    print(f"Write result: {write_result}")
    
    print("=" * 50)
    print("Demo completed! Check the file:", output_path)

if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    demo_translation()
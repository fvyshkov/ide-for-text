#!/usr/bin/env python3
"""
Test translation tools directly
"""
from tools.translation import translate_text

def test_translation_tool():
    """Test translation tool directly"""
    print("Testing translation tool directly...")
    print("=" * 50)
    
    # Test simple translation
    text = "Hello! This is a test. Thank you."
    result = translate_text.invoke({"text": text, "target_language": "Russian"})
    
    print(f"Original: {text}")
    print(f"Translated: {result}")
    
    print("=" * 50)
    print("Direct tool test completed!")

if __name__ == "__main__":
    test_translation_tool()
"""
Translation tools for AI agent
"""
import os
from typing import Optional
from langchain_core.tools import tool
from langchain_anthropic import ChatAnthropic
from dotenv import load_dotenv

# Load environment variables
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '..', '.env'))


@tool
def translate_text(text: str, target_language: str = "Russian", source_language: str = "auto") -> str:
    """
    Translate text to the target language using Claude AI.
    
    Args:
        text: Text to translate
        target_language: Target language for translation (default: Russian)
        source_language: Source language (default: auto-detect)
    
    Returns:
        Translated text
    """
    try:
        # Initialize Claude for translation
        llm = ChatAnthropic(
            model=os.getenv("AI_MODEL", "claude-3-5-sonnet-20240620"),
            temperature=0.1,  # Low temperature for consistent translations
            max_tokens=4096,
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY")
        )
        
        # Create translation prompt
        if source_language == "auto":
            prompt = f"""Please translate the following text to {target_language}. 
Preserve the original formatting, structure, and meaning as much as possible.
If the text is already in {target_language}, just return it as is.

Text to translate:
{text}

Translation:"""
        else:
            prompt = f"""Please translate the following text from {source_language} to {target_language}. 
Preserve the original formatting, structure, and meaning as much as possible.

Text to translate:
{text}

Translation:"""
        
        # Get translation
        response = llm.invoke(prompt)
        
        # Extract content from response
        if hasattr(response, 'content'):
            if isinstance(response.content, str):
                return response.content.strip()
            elif isinstance(response.content, list):
                # Handle list of content blocks
                text_parts = []
                for item in response.content:
                    if isinstance(item, dict) and 'text' in item:
                        text_parts.append(item['text'])
                    elif isinstance(item, str):
                        text_parts.append(item)
                    else:
                        text_parts.append(str(item))
                return '\n'.join(text_parts).strip()
            else:
                return str(response.content).strip()
        else:
            return str(response).strip()
            
    except Exception as e:
        return f"Error translating text: {str(e)}"


@tool
def translate_file_content(file_content: str, target_language: str = "Russian", source_language: str = "auto") -> str:
    """
    Translate file content to the target language, preserving structure.
    
    Args:
        file_content: Content of the file to translate
        target_language: Target language for translation (default: Russian)
        source_language: Source language (default: auto-detect)
    
    Returns:
        Translated file content
    """
    try:
        # For large files, we might want to split into chunks
        # For now, translate as one piece
        return translate_text.invoke({"text": file_content, "target_language": target_language, "source_language": source_language})
        
    except Exception as e:
        return f"Error translating file content: {str(e)}"
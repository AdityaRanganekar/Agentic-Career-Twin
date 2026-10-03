import os
import google.generativeai as genai
from src.utils.logger import get_custom_logger
from dotenv import load_dotenv

load_dotenv()

logger = get_custom_logger(__name__)

def get_gemini_client():
    """Configures and returns the Gemini model instance."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.error("GEMINI_API_KEY environment variable is missing.")
        raise ValueError("GEMINI_API_KEY not found in environment variables.")
    
    genai.configure(api_key=api_key)

    model = genai.GenerativeModel('gemini-3.5-flash-lite')
    return model
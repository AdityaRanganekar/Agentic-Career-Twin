import os
import yaml
import google.generativeai as genai
from src.utils.logger import get_custom_logger
from dotenv import load_dotenv

load_dotenv()

logger = get_custom_logger(__name__)

def _get_configured_model_name() -> str:
    # 1. Environment variable
    env_model = os.getenv("GEMINI_MODEL")
    if env_model:
        return env_model
    # 2. config.yaml
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config.yaml")
    if os.path.exists(config_path):
        try:
            with open(config_path, "r") as f:
                cfg = yaml.safe_load(f)
                if cfg and "llm" in cfg and "model_name" in cfg["llm"]:
                    return cfg["llm"]["model_name"]
        except Exception:
            pass
    return "gemini-3.5-flash-lite"

def get_gemini_client():
    """Configures and returns the Gemini model instance strictly standardized to gemini-3.5-flash-lite."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.error("GEMINI_API_KEY environment variable is missing.")
        raise ValueError("GEMINI_API_KEY not found in environment variables.")
    
    genai.configure(api_key=api_key)
    model_name = _get_configured_model_name()
    model = genai.GenerativeModel(model_name)
    return model
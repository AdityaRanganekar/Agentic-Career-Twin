import os
import time
import yaml
import concurrent.futures
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

class ResilientGenerativeModel:
    """
    Wraps GenerativeModel with strict gRPC timeouts, ThreadPoolExecutor timeout safeguards,
    automatic fast-failure on DNS/network/timeout errors, and automatic fallback to gemini-1.5-flash.
    """
    def __init__(self, model_name: str):
        self.model_name = model_name
        self._model = genai.GenerativeModel(model_name)
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)

    def _call_model(self, model_instance, *args, **kwargs):
        """Enforces request_options={'timeout': 20.0} and ThreadPoolExecutor future timeout of 22.0s."""
        call_kwargs = dict(kwargs)
        if "request_options" not in call_kwargs:
            call_kwargs["request_options"] = {"timeout": 20.0}
        elif isinstance(call_kwargs["request_options"], dict):
            req_opts = dict(call_kwargs["request_options"])
            req_opts.setdefault("timeout", 20.0)
            call_kwargs["request_options"] = req_opts

        future = self._executor.submit(model_instance.generate_content, *args, **call_kwargs)
        try:
            return future.result(timeout=22.0)
        except concurrent.futures.TimeoutError:
            raise TimeoutError("Gemini generate_content call exceeded strict 22s deadline.")

    def generate_content(self, *args, **kwargs):
        last_exc = None
        for attempt in range(2):
            try:
                return self._call_model(self._model, *args, **kwargs)
            except Exception as e:
                last_exc = e
                err_str = str(e).lower()
                is_dns_network_error = any(term in err_str for term in [
                    "name or service not known", "failed to resolve", "dns",
                    "nameresolutionerror", "getaddrinfo failed", "nodename nor servname provided",
                    "network is unreachable", "connection refused", "socket"
                ])
                is_timeout = isinstance(e, (concurrent.futures.TimeoutError, TimeoutError)) or "timeout" in err_str or "deadline" in err_str

                if is_dns_network_error or is_timeout:
                    logger.warning(
                        f"Gemini API network/DNS/timeout issue ({e}). "
                        f"Failing fast to trigger deterministic fallbacks."
                    )
                    raise e

                is_rate_limit = "429" in err_str or "resource exhausted" in err_str or "quota" in err_str
                is_transient = "503" in err_str or "unavailable" in err_str

                if (is_rate_limit or is_transient) and attempt == 0:
                    logger.warning(f"Gemini API transient issue (attempt 1/2): {e}. Quick retry with fallback...")
                    time.sleep(1.0)
                    if self.model_name != "gemini-1.5-flash":
                        try:
                            logger.info("Attempting fallback to gemini-1.5-flash...")
                            fallback = genai.GenerativeModel("gemini-1.5-flash")
                            return self._call_model(fallback, *args, **kwargs)
                        except Exception as fb_err:
                            logger.warning(f"Gemini fallback failed: {fb_err}")
                            raise fb_err
                else:
                    raise e
        if last_exc:
            raise last_exc
        return self._call_model(self._model, *args, **kwargs)

    def __getattr__(self, item):
        return getattr(self._model, item)

def get_gemini_client():
    """Configures and returns a resilient Gemini model instance with automatic backoff and fallback."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.error("GEMINI_API_KEY environment variable is missing.")
        raise ValueError("GEMINI_API_KEY not found in environment variables.")
    
    genai.configure(api_key=api_key)
    model_name = _get_configured_model_name()
    return ResilientGenerativeModel(model_name)
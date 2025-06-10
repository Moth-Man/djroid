from dotenv import load_dotenv
import os

load_dotenv()

OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY")
LANGSMITH_API_KEY: str = os.getenv("LANGSMITH_API_KEY")

# LangChain Settings
LANGSMITH_TRACING: bool = os.getenv("LANGSMITH_TRACING", "true").lower() == "true"
LANGSMITH_PROJECT: str = os.getenv("LANGSMITH_PROJECT", "djroid")

# Database
DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/djroid")

# Logging configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Application settings
APP_NAME = "DJroid"
APP_VERSION = "0.1.0"

# LLM specific settings
LLM_CONFIG = {
    "temperature": 0.7,
    "model_name": "gpt-4-turbo-preview",
    "max_tokens": 2000
}

# Application metadata
APP_NAME = "DJroid"
APP_VERSION = "0.1.0"

def validate_config():
    """Validate all required configuration"""
    required_vars = {
        "DATABASE_URL": DATABASE_URL,
        "LANGCHAIN_API_KEY": LANGSMITH_API_KEY,
        "OPENAI_API_KEY": OPENAI_API_KEY
    }
    
    missing = [key for key, value in required_vars.items() if not value]
    if missing:
        raise ValueError(f"Missing required environment variables: {', '.join(missing)}") 
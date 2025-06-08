from dotenv import load_dotenv
import os

load_dotenv()

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://localhost/djroid_dev")

# Logging configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# LangChain configuration
LANGCHAIN_TRACING_V2 = os.getenv("LANGCHAIN_TRACING_V2", "true").lower() == "true"
LANGCHAIN_API_KEY = os.getenv("LANGCHAIN_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

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
        "LANGCHAIN_API_KEY": LANGCHAIN_API_KEY,
        "OPENAI_API_KEY": OPENAI_API_KEY
    }
    
    missing = [key for key, value in required_vars.items() if not value]
    if missing:
        raise ValueError(f"Missing required environment variables: {', '.join(missing)}") 
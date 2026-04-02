import os

from dotenv import load_dotenv
load_dotenv()

# =========================
# API key environment variable names
# =========================
OPENAI_API_KEY_ENV = "OPENAI_API_KEY"
QIANWEN_API_KEY_ENV = "QIANWEN_API_KEY"
HUNYUAN_API_KEY_ENV = "HUNYUAN_API_KEY"

# =========================
# LLM PROVIDERS
# =========================
QIANWEN_LLM = "qianwen"
HUNYUAN_LLM = "hunyuan"
OPENAI_LLM = "openai"

# =========================
# KEYS
# =========================
QIANWEN_API_KEY = os.getenv("QIANWEN_API_KEY")
HUNYUAN_API_KEY = os.getenv("HUNYUAN_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# =========================
# API BASE URLS
# =========================
QIANWEN_BASE_URL = os.getenv("QIANWEN_BASE_URL")
HUNYUAN_BASE_URL = os.getenv("HUNYUAN_BASE_URL")

# =========================
# LLM MODELS
# =========================
QIANWEN_LLM_MODEL = os.getenv("QIANWEN_LLM_MODEL")
HUNYUAN_LLM_MODEL = os.getenv("HUNYUAN_LLM_MODEL")  
OPENAI_LLM_MODEL = os.getenv("OPENAI_LLM_MODEL")

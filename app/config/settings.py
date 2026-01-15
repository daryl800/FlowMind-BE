import os

from dotenv import load_dotenv
load_dotenv()

# =========================
# KEYS
# =========================
QIANWEN_API_KEY = os.getenv("QIANWEN_API_KEY")
TENCENT_SECRET_ID = os.getenv("TENCENT_SECRET_ID")
TENCENT_SECRET_KEY = os.getenv("TENCENT_SECRET_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# =========================
# Model selection
# =========================
# MODEL = "qwen-max"
# MODEL = "qwen-plus"
# MODEL = "qwen-flash"
QIANWEN_LLM_MODEL = 'qwen-plus'
HUNYUAN_LLM_MODEL = 'hunyuan-pro'
OPENAI_LLM_MODEL = 'gpt-4.1-mini'
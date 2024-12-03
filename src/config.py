import os

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
TAVILY_API_KEY = os.getenv('TAVILY_API_KEY')


# LLM Models
FAST_LLM_MODEL = "gpt-3.5-turbo-0125"
LONG_CONTEXT_MODEL = "gpt-4-turbo-preview"
EMBEDDINGS_MODEL = "text-embedding-3-small"

REPORTS_DIR = "reports" 
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.retrievers import WikipediaRetriever
from langchain_community.tools.tavily_search import TavilySearchResults
from ..config import FAST_LLM_MODEL, LONG_CONTEXT_MODEL, EMBEDDINGS_MODEL

class LLMService:
    def __init__(self):
        self.fast_llm = ChatOpenAI(model=FAST_LLM_MODEL)
        self.long_context_llm = ChatOpenAI(model=LONG_CONTEXT_MODEL)
        self.embeddings = OpenAIEmbeddings(model=EMBEDDINGS_MODEL)
        self.wikipedia_retriever = WikipediaRetriever(load_all_available_meta=True, top_k_results=3)
        self.tavily_search = TavilySearchResults(max_results=15) 
from langchain.agents import initialize_agent, AgentType
from langchain_openai import ChatOpenAI
from langchain_community.tools.tavily_search import TavilySearchResults
from .config import OPENAI_API_KEY, TAVILY_API_KEY, MODEL_NAME

def setup_agent():
    """
    Initialisiert den LangChain Agenten mit Tavily Search und OpenAI.
    """
    # 1. Das LLM (Gehirn)
    llm = ChatOpenAI(
        temperature=0,
        model=MODEL_NAME,
        openai_api_key=OPENAI_API_KEY
    )

    # 2. Die Tools (Werkzeuge)
    search = TavilySearchResults(
        tavily_api_key=TAVILY_API_KEY,
        max_results=3  # Etwas weniger Ergebnisse pro Suche, dafür gezielter
    )
    
    tools = [search]

    # 3. Der Agent (Manager)
    # Wir erhöhen max_iterations auf 10 (Standard ist oft 5 oder 15)
    # handle_parsing_errors=True hilft, wenn das JSON mal unsauber ist
    agent = initialize_agent(
        tools, 
        llm, 
        agent=AgentType.CHAT_ZERO_SHOT_REACT_DESCRIPTION, 
        verbose=True,
        handle_parsing_errors=True,
        max_iterations=12,           # Gib ihm etwas mehr Zeit für komplexe Tabellen
        early_stopping_method="generate" # Versuch am Ende noch was zu generieren
    )

    return agent
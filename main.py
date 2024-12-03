import asyncio
from src.services.document_service import DocumentService
from src.workflow.graph import ResearchWorkflow
from dotenv import load_dotenv
import os

load_dotenv()

async def generate_market_research(topic: str):
    try:
        print(f"Starting market research on topic: {topic}")
        
        workflow = ResearchWorkflow()
        initial_state = {
            "topic": topic,
            "search_terms": None,
            "companies": []
        }
        
        config = {"configurable": {"thread_id": "market-research-thread"}}
        final_state = await workflow.workflow.ainvoke(initial_state, config)
        
        print(f"\nFound {len(final_state['companies'])} companies")
        
        filename = await DocumentService.save_to_excel(final_state["companies"])
        print(f"\nMarket research saved to: {filename}")
        return filename
        
    except Exception as e:
        print(f"An error occurred during market research for '{topic}': {str(e)}")
        raise e

async def main():
    topic = "research on Cleaning services in BUffalo, NY and provide details on pricing, services, and contact information"
    await generate_market_research(topic)

if __name__ == "__main__":
    asyncio.run(main()) 
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from ..services.llm_service import LLMService
from ..models.research_models import SearchTerms, CompanyInfo
from typing import List
from pydantic import BaseModel
import json
import asyncio
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain_core.tools import tool
from functools import partial
import pandas as pd
import re
import traceback
import os

class CompaniesResponse(BaseModel):
    companies: List[CompanyInfo]

class SearchQuery(BaseModel):
    """Schema for search query input."""
    query: str

class WorkflowNodes:
    def __init__(self):
        self.llm_service = LLMService()
        self.search_company_info = self._create_search_tool()

    def _create_search_tool(self):
        """Create the search tool with proper instance binding."""
        @tool(args_schema=SearchQuery)
        async def search_company_info(query: str) -> str:
            """Search for company information using Tavily.
            Args:
                query: The search query string
            Returns:
                str: Search results from Tavily
            """
            try:
                result = await self.llm_service.tavily_search.ainvoke(query)
                return result
            except Exception as e:
                print(f"Search error: {str(e)}")
                return f"Error performing search: {str(e)}"
        
        return search_company_info

    def _normalize_service_name(self, service: str) -> str:
        """Normalize service names to prevent duplicates with different capitalizations."""
        return service.lower().strip()

    async def gather_company_data(self, state):
        """Gather comprehensive research data using an agent-based approach."""
        if isinstance(state["search_terms"], dict):
            state["search_terms"] = SearchTerms(**state["search_terms"])

        agent_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert research specialist agent focused on gathering comprehensive market information. 
            Your task is to collect detailed data about companies, products, services, and educational platforms related to the given topic. You MUST collect at least 200 unique companies data with services, pricing, rating, contact, and reviews.
            
            Follow these detailed guidelines:
            1. SEARCH COMPREHENSIVELY:
               - Use multiple search queries to find different types of providers
               - Look for both major and niche providers
               - Consider both national chains and local providers
               - Search specifically for companies with verified reviews on Yelp, Google, or other platforms
            
            2. GATHER DETAILED INFORMATION:
               - Company names and full descriptions
               - List ALL services offered by the company in a single entry
               - Include review scores from Yelp, Google, or other platforms
               - If ratings are not found initially, perform additional searches
               - Detailed pricing information when available
               - Contact information and locations
               - Official websites
            
            3. ENSURE DATA QUALITY:
               - Verify information from multiple sources
               - Consolidate all services into a single company entry
               - Always include review/rating information from Yelp or Google
               - Note when information is not available
            
            When using the search_company_info tool:
            - Search specifically for review information if not found initially
            - Use "company name + reviews" as additional search when needed
            - Look for Yelp and Google Business listings
            
            Format all information precisely into this structure:
            {{
                "companies": [
                    {{
                        "name": "Exact Company Name",
                        "description": "Detailed description including unique features",
                        "services": ["All services in a single list"],
                        "pricing": {{"Service Category": "Price range"}},
                        "rating": "Rating (Source: Yelp/Google)",
                        "contact": "All available contact methods",
                        "website": "Primary website URL"
                    }}
                ]
            }}"""),
            ("user", "{input}"),
            ("assistant", "I'll conduct thorough research on this topic."),
            ("human", "Required information structure: {format_instructions}"),
            ("assistant", "{agent_scratchpad}")
        ])

        tools = [self.search_company_info]
        agent = create_openai_functions_agent(
            llm=self.llm_service.long_context_llm,
            prompt=agent_prompt,
            tools=tools
        )

        agent_executor = AgentExecutor(
            agent=agent,
            tools=tools,
            verbose=True,
            handle_parsing_errors=True
        )

        search_queries = self._generate_search_queries(state["topic"], state["search_terms"])
        print(f"Generated search queries: {search_queries}")

        companies = []
        for query in search_queries:
            try:
                result = await agent_executor.ainvoke({
                    "topic": state["topic"],
                    "format_instructions": """Return a JSON object with a 'companies' array containing company information.
                    Each company should have: name, description, services (array), pricing (object), rating, contact, and website.""",
                    "input": f"Research {state['topic']}. Focus on the query: {query}"
                })
                
                print(f"Raw result for query '{query}': {result}")

      
                if isinstance(result, dict):
                    if "companies" in result:
                        companies.extend(result["companies"])
                    elif "output" in result:
                        output = result["output"]
                        if isinstance(output, str):
 
                            output = output.replace("```json", "").replace("```", "").strip()
                            try:

                                json_match = re.search(r'\{[\s\S]*\}', output)
                                if json_match:
                                    parsed_data = json.loads(json_match.group())
                                    if "companies" in parsed_data:
                                        companies.extend(parsed_data["companies"])
                            except json.JSONDecodeError as e:
                                print(f"JSON parsing error: {str(e)}")
                                continue
                
                await asyncio.sleep(10)  # 10sec delay between requests
                
            except Exception as e:
                print(f"Agent execution error for query '{query}': {str(e)}")
                await asyncio.sleep(20)
                continue

        if companies:
            try:

                unique_companies = {}

                for company in companies:
                    if isinstance(company, dict) and "name" in company:
                        name = company["name"].strip()
                        
                        company_data = {
                            "Company Name": name,
                            "Description": company.get("description", "Not available"),
                            "Services": ", ".join(company.get("services", [])) if company.get("services") else "Not available",
                            "Rating": company.get("rating", "Not available"),
                            "Contact": company.get("contact", "Not available"),
                            "Website": company.get("website", "Not available"),
                            "Pricing": str(company.get("pricing", {})) if company.get("pricing") else "Not available"
                        }
                        
 
                        if name not in unique_companies:
                            unique_companies[name] = company_data
                        else:

                            for key, value in company_data.items():
                                if value != "Not available" and unique_companies[name][key] == "Not available":
                                    unique_companies[name][key] = value
                

                processed_companies = list(unique_companies.values())
                
                if processed_companies:
     
                    df = pd.DataFrame(processed_companies)
                    
                    os.makedirs("reports", exist_ok=True)
                    
                    excel_path = "reports/market_research.xlsx"
                    df.to_excel(excel_path, index=False)
                    print(f"\nMarket research saved to: {excel_path}")
                    
                    return {**state, "companies": processed_companies}
                
            except Exception as e:
                print(f"Error processing companies: {str(e)}\n{traceback.format_exc()}")
        
        print("No valid data found")
        return {**state, "companies": []}

    def _generate_search_queries(self, topic: str, search_terms: SearchTerms) -> List[str]:
        queries = []
        base_terms = [topic] + search_terms.main_terms + search_terms.related_terms
        
        
        location_match = re.search(r'in (\w+)', topic, re.IGNORECASE)
        location = location_match.group(1) if location_match else ""

        general_modifiers = [
            "top rated", "best", "popular",
            "reviews", "comparison", "alternatives",
            "pricing", "cost", "fees"
        ]

        if location:
            location_modifiers = [f"in {location}", f"near {location}", f"{location} area"]
            general_modifiers.extend(location_modifiers)

        for term in base_terms:
            queries.append(f"{term} providers")
            queries.append(f"{term} companies")
            
            for mod in general_modifiers:
                queries.append(f"{term} {mod}")

        queries = list(set(queries))
        return queries[:20]  

    async def generate_search_terms(self, state):
        """Generate search terms for the given topic."""
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a market research specialist. Your task is to generate relevant search terms for researching companies and services in a given topic.
            Break down the topic into main search terms and related terms that will help find comprehensive information."""),
            ("user", """Generate search terms for the topic: {topic}
            
            Required format:
            {format_instructions}""")
        ])

        parser = JsonOutputParser(pydantic_object=SearchTerms)

        chain = prompt | self.llm_service.long_context_llm | parser

        search_terms = await chain.ainvoke({
            "topic": state["topic"],
            "format_instructions": parser.get_format_instructions()
        })

        return {**state, "search_terms": search_terms}


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

    async def gather_company_data(self, state):
        """Gather comprehensive research data using an agent-based approach."""
        if isinstance(state["search_terms"], dict):
            state["search_terms"] = SearchTerms(**state["search_terms"])

        agent_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a research specialist agent. Your task is to gather detailed information about companies, 
            products, or services based on the given topic. Use the search tool to find comprehensive information.
            
            Follow these guidelines:
            1. Search for specific company names, products, and pricing
            2. Gather detailed features and specifications
            3. Find customer reviews and ratings
            4. Look for market information and competitors
            
            When using the search_company_info tool, provide a search query string.
            Example: search_company_info("<topic> in <location>")
            
            Format all information into a list of companies with the following structure:
            {{
                "companies": [
                    {{
                        "name": "Company Name",
                        "description": "Brief description",
                        "products": ["Service 1", "Service 2"],
                        "pricing": {{"Service 1": "$X/hour", "Service 2": "$Y/visit"}},
                        "rating": "4.5/5",
                        "contact": "phone or email",
                        "website": "url"
                    }}
                ]
            }}"""),
            ("user", "{input}"),
            ("assistant", "I'll help you research that topic."),
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
                    Each company should have: name, description, products (array), pricing (object), rating, contact, and website.""",
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
                                parsed_data = json.loads(output)
                                if "companies" in parsed_data:
                                    companies.extend(parsed_data["companies"])
                            except Exception as e:
                                print(f"JSON parsing error for output: {str(e)}")
                elif isinstance(result, str):
                    try:
             
                        result = result.replace("```json", "").replace("```", "").strip()
                        json_match = re.search(r'\{[\s\S]*\}', result)
                        if json_match:
                            parsed_data = json.loads(json_match.group())
                            if "companies" in parsed_data:
                                companies.extend(parsed_data["companies"])
                    except Exception as e:
                        print(f"JSON parsing error for query '{query}': {str(e)}")
                
                await asyncio.sleep(5)  # Rate limiting
                
            except Exception as e:
                print(f"Agent execution error for query '{query}': {str(e)}")
                continue

        
        unique_companies = {}
        for company in companies:
            if company.get("name") and company["name"] not in unique_companies:
              
                products = ", ".join(company.get("products", []))
                pricing = "; ".join([f"{k}: {v}" for k, v in company.get("pricing", {}).items()])
                
             
                website = company.get("website", "")
                if isinstance(website, list):
                    website = " | ".join(website)
                
                unique_companies[company["name"]] = {
                    "name": company["name"],
                    "description": company.get("description", ""),
                    "products": products,
                    "pricing": pricing,
                    "rating": company.get("rating", ""),
                    "contact": company.get("contact", ""),
                    "website": website
                }
        
        # Log results
        print(f"\nTotal unique providers/platforms found: {len(unique_companies)}")

        if unique_companies:
            try:
                import pandas as pd
                from pathlib import Path
                
        
                Path("reports").mkdir(exist_ok=True)
                

                df = pd.DataFrame.from_dict(unique_companies, orient='index')
                
 
                excel_path = "reports/market_research.xlsx"
                df.to_excel(excel_path, index=False)
                print(f"\nMarket research saved to: {excel_path}")
                
   
                company_objects = []
                for data in unique_companies.values():
  
                    pricing_dict = {}
                    if data["pricing"]:
                        try:
                            pricing_dict = dict(item.split(": ", 1) for item in data["pricing"].split("; ") if ": " in item)
                        except Exception as e:
                            print(f"Error parsing pricing for company {data['name']}: {str(e)}")
                    
                    company_objects.append(CompanyInfo(
                        name=data["name"],
                        description=data["description"],
                        products=data["products"].split(", ") if data["products"] else [],
                        pricing=pricing_dict,
                        rating=data["rating"],
                        contact=data["contact"],
                        website=data["website"]
                    ))
                
                return {**state, "companies": company_objects}
                
            except Exception as e:
                print(f"Error exporting to Excel: {str(e)}")
                traceback.print_exc()  
                return {**state, "companies": []}
        else:
            print("Warning: No valid data to export")
            with open("reports/no_data.txt", "w") as f:
                f.write("No data was found for the given topic.")
            return {**state, "companies": []}

    def _generate_search_queries(self, topic: str, search_terms: SearchTerms) -> List[str]:
        """Helper method to generate search queries based on the topic."""
        queries = []
        if "cleaning" in topic.lower():
            for term in search_terms.main_terms[:2]:
                queries.extend([
                    f"{term} companies prices reviews",
                    f"{term} top rated services"
                ])
        else:
            for term in search_terms.main_terms:
                if "course" in topic.lower() or "training" in topic.lower():
                    queries.extend([
                        f"{term} course curriculum price",
                        f"{term} training reviews ratings",
                        f"{term} certification learning platform"
                    ])
                elif "product" in topic.lower():
                    queries.extend([
                        f"{term} product specifications features",
                        f"{term} price comparison reviews",
                        f"{term} availability retailers"
                    ])
                else:
                    queries.extend([
                        f"{term} provider details pricing",
                        f"{term} reviews ratings feedback",
                        f"{term} market analysis comparison"
                    ])
        return queries

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


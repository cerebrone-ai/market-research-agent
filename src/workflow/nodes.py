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
            ("system", """You are an expert research specialist agent focused on gathering comprehensive market information. 
            Your task is to collect detailed data about companies, products, services, and educational platforms related to the given topic. Collect atleast 50 data points.
            
            Follow these detailed guidelines:
            1. SEARCH COMPREHENSIVELY:
               - Use multiple search queries to find different types of providers
               - Look for both major and niche providers
               - Consider international and local options when required
               - Search for both established and emerging players
            
            2. GATHER DETAILED INFORMATION:
               - Company names and full descriptions
               - Complete product/service listings
               - Detailed pricing information when available
               - User ratings and reviews
               - Contact information and locations
               - Official websites and platforms
               - Certifications and accreditations
               - Market position and unique selling points
            
            3. ENSURE DATA QUALITY:
               - Verify information from multiple sources when possible
               - Include specific details rather than generic descriptions
               - Note when information is not available or requires direct contact
               - Provide context for pricing (e.g., subscription type, duration)
            
            When using the search_company_info tool:
            - Break down complex topics into specific search queries
            - Use different combinations of keywords
            - Include industry-specific terms
            - Search for reviews and comparisons
            
            Format all information precisely into this structure:
            {{
                "companies": [
                    {{
                        "name": "Exact Company Name",
                        "description": "Detailed description including unique features and market position",
                        "products": ["Specific Product/Service 1", "Specific Product/Service 2"],
                        "pricing": {{"Product 1": "Exact price or range", "Product 2": "Exact price or range"}},
                        "rating": "Numerical rating if available, or detailed reputation information",
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
                try:
                    # Handle products list
                    products = company.get("products", [])
                    if isinstance(products, list):
                        products = ", ".join(products)
                    elif isinstance(products, str):
                        products = products
                    else:
                        products = ""

                    pricing = company.get("pricing", {})
                    if isinstance(pricing, dict):
                        pricing = "; ".join([f"{k}: {v}" for k, v in pricing.items()])
                    elif isinstance(pricing, str):
                        pricing = pricing
                    else:
                        pricing = ""

             
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
                except Exception as e:
                    print(f"Error processing company {company.get('name', 'Unknown')}: {str(e)}")
                    continue
        
        # Log results
        print(f"\nTotal unique providers/platforms found: {len(unique_companies)}")
        
  
        if unique_companies:
            try:
                import pandas as pd
                from pathlib import Path

                Path("reports").mkdir(exist_ok=True)
                
       
                df = pd.DataFrame.from_dict(unique_companies, orient='index')
                
                # Save to Excel
                excel_path = "reports/market_research.xlsx"
                df.to_excel(excel_path, index=False)
                print(f"\nMarket research saved to: {excel_path}")
                
      
                company_objects = []
                for data in unique_companies.values():
                    try:
          
                        pricing_dict = {}
                        if data["pricing"]:
                            if ";" in data["pricing"]:
                              
                                pricing_items = data["pricing"].split(";")
                                for item in pricing_items:
                                    if ":" in item:
                                        key, value = item.split(":", 1)
                                        pricing_dict[key.strip()] = value.strip()
                            else:
                               
                                pricing_dict = {"Price": data["pricing"].strip()}
                        
                        company_objects.append(CompanyInfo(
                            name=data["name"],
                            description=data["description"],
                            products=data["products"].split(", ") if data["products"] else [],
                            pricing=pricing_dict,
                            rating=data["rating"],
                            contact=data["contact"],
                            website=data["website"]
                        ))
                    except Exception as e:
                        print(f"Error creating CompanyInfo object for {data['name']}: {str(e)}")
                        continue
                
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
        """Generate comprehensive search queries based on the topic."""
        queries = []
        

        base_terms = [topic] + search_terms.main_terms + search_terms.related_terms
        

        modifiers = [
            "top rated", "best", "popular",
            "reviews", "comparison", "alternatives",
            "pricing", "cost", "fees",
            "certification", "training", "courses",
            "features", "benefits", "advantages",
            "professional", "enterprise", "startup",
            "beginner", "advanced", "expert level"
        ]
        
   
        for term in base_terms:
 
            queries.append(f"{term} providers platforms")
            queries.append(f"{term} companies services")
            

            for mod in modifiers:
                queries.append(f"{term} {mod}")
                
            if "course" in topic.lower() or "training" in topic.lower():
                edu_modifiers = [
                    "online courses", "certification programs",
                    "training platforms", "learning resources",
                    "tutorials", "workshops", "bootcamps"
                ]
                for edu_mod in edu_modifiers:
                    queries.append(f"{term} {edu_mod}")
        
      
        queries = list(set(queries))
        return queries[:30] 

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


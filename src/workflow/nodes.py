from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from ..services.llm_service import LLMService
from ..models.research_models import SearchTerms, CompanyInfo
from typing import List
import json

class WorkflowNodes:
    def __init__(self):
        self.llm_service = LLMService()

    async def generate_search_terms(self, state):
        """Generate focused search terms for market research."""
        print("Generating search terms...")
        
        search_terms_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a market research specialist. Create focused search terms for finding companies and their services.
            
            Generate two types of search terms:
            1. Main terms: 3-5 primary search phrases to find companies and services
            2. Related terms: 3-5 secondary phrases for pricing and reviews
            
            Focus on terms that will help find:
            - Company listings
            - Service offerings
            - Pricing information
            - Reviews and ratings"""),
            ("user", "Create search terms to find companies and services for: {topic}")
        ])
        
        generate_terms = search_terms_prompt | self.llm_service.fast_llm.with_structured_output(SearchTerms)
        search_terms = await generate_terms.ainvoke({"topic": state["topic"]})
        
        return {**state, "search_terms": search_terms}

    async def gather_company_data(self, state):
        """Gather company information and pricing details."""
        print("Gathering company data...")
        search_terms = state["search_terms"]
        companies = []
        
        search_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a market research specialist. Extract detailed company information from the search results.
            Return the data as a list of companies with their details.
            
            For each company found, include:
            - Company name (required)
            - List of services offered (required)
            - Pricing details for each service (if available, otherwise use 'Contact for pricing')
            - Contact information (if available, otherwise use 'Not available')
            - Service area/location (required)
            - Website URL (if available, otherwise use 'Not available')
            - Rating (if available, use null if missing)
            
            Ensure to extract as much detail as possible from the search results."""),
            ("user", """Please analyze these search results and extract company information in the following JSON format:
            {{
                "companies": [
                    {{
                        "name": "Company Name",
                        "services": ["Service 1", "Service 2"],
                        "pricing": {{
                            "Service 1": "Price or 'Contact for pricing'",
                            "Service 2": "Price or 'Contact for pricing'"
                        }},
                        "contact": "Phone/email or 'Not available'",
                        "location": "Service area",
                        "website": "URL or 'Not available'",
                        "rating": null
                    }}
                ]
            }}
            
            Search Results: {results}""")
        ])
        
        for term in search_terms.main_terms + search_terms.related_terms:
            try:
                print(f"Searching for: {term}")
                results = await self.llm_service.tavily_search.ainvoke(
                    f"{term} companies services pricing reviews"
                )
                
                process_results = search_prompt | self.llm_service.long_context_llm | JsonOutputParser()
                result_json = await process_results.ainvoke({"results": results})
                

                if isinstance(result_json, str):
                    result_json = json.loads(result_json)
                
                for company_data in result_json.get("companies", []):
                    try:

                        company = CompanyInfo.create_with_defaults(company_data)
                        

                        if not company.pricing or all(value == "Contact for pricing" for value in company.pricing.values()):
                            print(f"Warning: Pricing details are missing for {company.name}.")
                        
                        if company.contact == "Not available":
                            print(f"Warning: Contact information is missing for {company.name}.")
                        
                        companies.append(company)
                        print(f"Found company: {company.name}")
                    except Exception as e:
                        print(f"Warning: Failed to parse company data: {str(e)}")
                        continue
                
            except Exception as e:
                print(f"Warning: Search error for '{term}': {str(e)}")
                continue
        

        unique_companies = {company.name: company for company in companies}.values()
        print(f"Total unique companies found: {len(unique_companies)}")
        return {**state, "companies": list(unique_companies)}


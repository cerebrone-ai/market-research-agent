from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from ..services.llm_service import LLMService
from ..models.research_models import SearchTerms, CompanyInfo
from typing import List
import json
import asyncio

class WorkflowNodes:
    def __init__(self):
        self.llm_service = LLMService()

    async def generate_search_terms(self, state):
        """Generate focused search terms for market research."""
        print("Generating search terms...")
        
        search_terms_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a market research specialist. Create focused search terms for finding companies and their services.
            
            Generate two types of search terms:
            1. Main terms: 5-7 primary search phrases to find companies and services in specific locations
            2. Related terms: 5-7 secondary phrases for detailed pricing and reviews
            
            Include location-specific terms and ensure coverage of:
            - Local company directories
            - Service comparison sites
            - Review platforms
            - Price comparison websites
            - Local business associations"""),
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
        
        # Define search_prompt with escaped curly braces in the JSON example
        search_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a data extraction specialist. Extract company information from search results and format it as JSON.
            
            The output should be a JSON object with a "companies" array containing objects with these fields:
            {{
                "companies": [
                    {{
                        "name": "Company Name",
                        "services": ["Service 1", "Service 2"],
                        "pricing": {{"Service 1": "Price 1", "Service 2": "Price 2"}},
                        "contact": "Contact info",
                        "location": "Company location",
                        "website": "Website URL",
                        "rating": 5.0,
                        "review_details": {{
                            "total_reviews": 0,
                            "highlights": ["Highlight 1", "Highlight 2"],
                            "concerns": ["Concern 1", "Concern 2"]
                        }}
                    }}
                ]
            }}
            
            Only include companies with clear, verifiable information. Skip entries with insufficient data. Ensure to extract ratings, reviews, and any highlights or concerns mentioned."""),
            ("user", "Extract structured company data from these search results: {results} in {location}")
        ])
        
        # Reduce the number of expanded terms
        location = state["topic"].split(":")[-1].strip()
        expanded_terms = [
            f"cleaning services {location}",
            f"house cleaning {location}",
            f"maid service {location}",
            f"top rated cleaning companies {location}",
            f"affordable cleaning service {location}"
        ]  # Reduced from 11 to 5 terms
        
        # Use a limited set of search terms to avoid too many API calls
        all_terms = list(set(search_terms.main_terms[:3] + search_terms.related_terms[:2] + expanded_terms[:3]))
        
        for term in all_terms:
            try:
                print(f"Searching for: {term}")
                # Reduce search queries per term
                search_queries = [
                    f"{term} hourly rate price cost reviews ratings",
                    f"{term} companies directory listings"
                ]  # Reduced from 4 to 2 queries
                
                # Add delay between searches to avoid rate limits
                for query in search_queries:
                    results = await self.llm_service.tavily_search.ainvoke(query)
                    await asyncio.sleep(1)  # Add small delay between searches
                    
                    # Process results to JSON
                    process_results = search_prompt | self.llm_service.long_context_llm | JsonOutputParser()
                    result_json = await process_results.ainvoke({
                        "results": results,
                        "location": location
                    })
                    
                    # Debug: Print raw JSON output
                    print("Raw JSON output:", result_json)
                    
                    if isinstance(result_json, str):
                        result_json = json.loads(result_json)
                    
                    for company_data in result_json.get("companies", []):
                        try:
                            # Check for meaningful data
                            if not company_data.get("rating") or company_data.get("rating") == 0:
                                print(f"Warning: No rating found for {company_data.get('name')}")
                            if not company_data.get("review_details", {}).get("total_reviews"):
                                print(f"Warning: No reviews found for {company_data.get('name')}")
                            
                            company = CompanyInfo.create_with_defaults(company_data)
                            companies.append(company)
                            print(f"Found company: {company.name}")
                            
                        except Exception as e:
                            print(f"Warning: Failed to parse company data: {str(e)}")
                            continue
                
            except Exception as e:
                print(f"Warning: Search error for '{term}': {str(e)}")
                continue
        
        # Remove duplicates based on company name
        unique_companies = {company.name: company for company in companies}.values()
        print(f"\nTotal unique companies found: {len(unique_companies)}")
        
        print("\nCompanies found:")
        for company in unique_companies:
            print(f"- {company.name}")
            if company.rating:
                print(f"  Rating: {company.rating} stars")
            if company.pricing:
                print(f"  Services: {len(company.pricing)} price points found")
        
        return {**state, "companies": list(unique_companies)}


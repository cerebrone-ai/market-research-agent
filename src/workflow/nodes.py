from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from ..services.llm_service import LLMService
from ..models.research_models import SearchTerms, CompanyInfo
from typing import List
from pydantic import BaseModel
import json
import asyncio

class CompaniesResponse(BaseModel):
    companies: List[CompanyInfo]

class WorkflowNodes:
    def __init__(self):
        self.llm_service = LLMService()

    async def generate_search_terms(self, state):
        """Generate focused search terms based on the research topic."""
        search_terms_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a research specialist. Analyze the given topic and generate relevant search terms.
            
            For any topic (products, courses, services, companies, etc.), create three categories of search terms:
            1. Primary Terms (4-5 terms):
               - Exact names/titles
               - Main keywords
               - Specific identifiers
               
            2. Provider/Platform Terms (4-5 terms):
               - Companies/Organizations offering the item
               - Platforms/Websites
               - Distribution channels
               
            3. Review/Analysis Terms (3-4 terms):
               - Reviews and ratings
               - Comparisons
               - User experiences/feedback"""),
            ("user", "Create focused search terms for researching: {topic}")
        ])
        
        generate_terms = search_terms_prompt | self.llm_service.fast_llm.with_structured_output(SearchTerms)
        search_terms = await generate_terms.ainvoke({"topic": state["topic"]})
        return {**state, "search_terms": search_terms}

    async def gather_company_data(self, state):
        """Gather comprehensive research data based on the topic."""
        search_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a research specialist. Extract structured information from search results into this exact format:

            {{
                "companies": [
                    {{
                        "name": "Provider Name",
                        "products": ["Product/Course Name 1", "Product/Course Name 2"],
                        "pricing": {{
                            "Product/Course Name 1": "Price 1",
                            "Product/Course Name 2": "Price 2"
                        }},
                        "website": "website URL",
                        "contact": "contact information",
                        "rating": "numerical rating or 'Not found'",
                        "product_details": {{
                            "features": {{
                                "Product/Course Name 1": ["Feature 1", "Feature 2"]
                            }},
                            "specifications": {{
                                "Product/Course Name 1": ["Spec 1", "Spec 2"]
                            }},
                            "availability": {{
                                "Product/Course Name 1": "Available/Not Available"
                            }}
                        }},
                        "review_analysis": {{
                            "total_reviews": "number or 'Not found'",
                            "average_rating": "numerical or 'Not found'",
                            "positive_points": ["Positive point 1", "Positive point 2"],
                            "negative_points": ["Negative point 1", "Negative point 2"],
                            "customer_sentiment": "Overall sentiment description"
                        }},
                        "market_details": {{
                            "market_share": "Percentage or description",
                            "target_segment": "Target audience description",
                            "key_competitors": ["Competitor 1", "Competitor 2"]
                        }}
                    }}
                ]
            }}"""),
            ("user", """Research topic: {topic}
            Extract detailed information from these search results: {results}
            
            Remember to:
            1. Include pricing for each product/course
            2. Provide all required fields
            3. Use 'Not available' or 'Not found' for missing information""")
        ])

        process_results = search_prompt | self.llm_service.long_context_llm.with_structured_output(CompaniesResponse)

        async def perform_search(term):
            results = await self.llm_service.tavily_search.ainvoke(term)
            await asyncio.sleep(1)
            return results

        search_queries = []
        for main_term in state["search_terms"].main_terms:
            if "course" in state["topic"].lower() or "training" in state["topic"].lower():
                search_queries.extend([
                    f"{main_term} course curriculum price",
                    f"{main_term} training reviews ratings",
                    f"{main_term} certification learning platform"
                ])
            elif "product" in state["topic"].lower():
                search_queries.extend([
                    f"{main_term} product specifications features",
                    f"{main_term} price comparison reviews",
                    f"{main_term} availability retailers"
                ])
            else:  
                search_queries.extend([
                    f"{main_term} provider details pricing",
                    f"{main_term} reviews ratings feedback",
                    f"{main_term} market analysis comparison"
                ])

        companies = []
        for query in search_queries:
            try:
                results = await perform_search(query)
                parsed_data = await process_results.ainvoke({
                    "topic": state["topic"],
                    "results": results
                })
                companies.extend(parsed_data.companies)
            except Exception as e:
                print(f"Search error for '{query}': {str(e)}")
                continue
            
        unique_companies = {company.name: company for company in companies}.values()
        
        print(f"\nTotal unique providers/platforms found: {len(unique_companies)}")
        
        print("\nRelevant results found:")
        for company in unique_companies:
            print(f"- {company.name}")
            if company.products:
                print(f"  Products: {', '.join(company.products)}")
            if company.rating:
                print(f"  Rating: {company.rating}")
            if company.pricing:
                for product, price in company.pricing.items():
                    print(f"  Price for {product}: {price}")
        
        return {**state, "companies": list(unique_companies)}


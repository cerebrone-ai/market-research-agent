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
            ("system", """You are a research specialist. Extract structured information from search results into this exact format.
            You MUST provide actual values for each field - do not return empty or placeholder values.
            If information is truly not available, use 'Not found' or 'Not available'.

            {{
                "companies": [
                    {{
                        "name": "REQUIRED: Actual company/provider name",
                        "products": ["REQUIRED: At least one actual product/course name"],
                        "pricing": {{
                            "REQUIRED: Product/Course Name": "REQUIRED: Actual price or price range"
                        }},
                        "website": "REQUIRED: Actual website URL or 'Not found'",
                        "contact": "Contact information or 'Not found'",
                        "rating": "Numerical rating or 'Not found'",
                        "product_details": {{
                            "features": {{
                                "REQUIRED: Product/Course Name": ["REQUIRED: At least 2-3 actual features"]
                            }},
                            "specifications": {{
                                "REQUIRED: Product/Course Name": ["At least 2 specifications"]
                            }},
                            "availability": {{
                                "REQUIRED: Product/Course Name": "Available/Not Available"
                            }}
                        }},
                        "review_analysis": {{
                            "total_reviews": "Number or 'Not found'",
                            "average_rating": "Numerical or 'Not found'",
                            "positive_points": ["REQUIRED: At least 2 actual positive points"],
                            "negative_points": ["At least 2 negative points or 'None reported'"],
                            "customer_sentiment": "REQUIRED: Actual sentiment description"
                        }},
                        "market_details": {{
                            "market_share": "Percentage/description or 'Not found'",
                            "target_segment": "REQUIRED: Actual target audience description",
                            "key_competitors": ["REQUIRED: At least 2 actual competitors"]
                        }}
                    }}
                ]
            }}"""),
            ("user", """Research topic: {topic}
            Extract detailed information from these search results: {results}
            
            Important instructions:
            1. You MUST provide actual, specific information for each required field
            2. Do not return empty arrays or placeholder text
            3. Include real pricing for each product/course
            4. If information is truly not available, use 'Not found' or 'Not available'
            5. Ensure company names are real and specific
            6. Each company entry must have at least one product/course with details""")
        ])

        process_results = search_prompt | self.llm_service.long_context_llm.with_structured_output(CompaniesResponse)

        async def perform_search(term, max_retries=3):
            for attempt in range(max_retries):
                try:
                    results = await self.llm_service.tavily_search.ainvoke(term)
                    print(f"Search results for '{term}': {results}")
                    await asyncio.sleep(5)
                    return results
                except Exception as e:
                    if "429" in str(e) and attempt < max_retries - 1:
                        wait_time = (attempt + 1) * 10
                        print(f"Rate limit hit, waiting {wait_time} seconds before retry...")
                        await asyncio.sleep(wait_time)
                    else:
                        print(f"Search error for '{term}': {str(e)}")
                        return []
            return []

        search_queries = []
        if "cleaning" in state["topic"].lower():
            for main_term in state["search_terms"].main_terms[:2]:
                search_queries.extend([
                    f"{main_term} companies prices reviews",
                    f"{main_term} top rated services"
                ])
        else:
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
        batch_size = 2
        for i in range(0, len(search_queries), batch_size):
            batch = search_queries[i:i + batch_size]
            batch_results = await asyncio.gather(
                *(perform_search(query) for query in batch)
            )
            
            for results in batch_results:
                if results:
                    try:
                        parsed_data = await process_results.ainvoke({
                            "topic": state["topic"],
                            "results": results
                        })
                        companies.extend(parsed_data.companies)
                    except Exception as e:
                        print(f"Parsing error: {str(e)}")
                        continue
            
            await asyncio.sleep(10)

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


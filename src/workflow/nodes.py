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
        """Generate focused search terms for AI course research."""
        print("Generating search terms...")
        
        search_terms_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an AI education research specialist. Create focused search terms for finding AI course providers and their offerings.
            
            Generate two types of search terms:
            1. Main terms (5-7 terms) focusing ONLY on:
               - Generative AI development courses
               - AI Agents frameworks (LangChain, LangGraph, CrewAI)
               - Large Language Models programming
               - Multi-agent systems development
               
            2. Related terms (3-5 terms) for course details about:
               - Course pricing and duration
               - Professional certifications
               - Reviews and ratings
               
            Focus exclusively on programming and development courses for GenAI and AI Agents.
            Do NOT include general AI or machine learning courses."""),
            ("user", "Create search terms to find AI courses and platforms for: {topic}")
        ])
        
        generate_terms = search_terms_prompt | self.llm_service.fast_llm.with_structured_output(SearchTerms)
        search_terms = await generate_terms.ainvoke({"topic": state["topic"]})
        
        return {**state, "search_terms": search_terms}

    async def gather_company_data(self, state):
        """Gather course provider information and details."""
        print("Gathering course provider data...")
        
        # Get search terms from state
        search_terms = state["search_terms"]
        if not search_terms:
            print("Warning: No search terms found in state")
            return state
        
        search_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a course data extraction specialist focusing on GenAI and AI Agents development courses.
            
            Extract ONLY courses related to:
            - Generative AI development
            - AI Agents frameworks (LangChain, AutoGPT, CrewAI)
            - LLM programming and integration
            - Multi-agent systems development
            
            DO NOT include courses about:
            - General AI or machine learning
            - Data science basics
            - Non-programming courses
            
            Format the output as JSON with these fields:
            {{
                "companies": [
                    {{
                        "name": "Platform/Institution Name",
                        "services": ["Course 1", "Course 2"],
                        "pricing": {{"Course 1": "Price 1", "Course 2": "Price 2"}},
                        "contact": "Contact info",
                        "website": "Website URL",
                        "rating": 5.0,
                        "course_details": {{
                            "durations": {{"Course 1": "Duration 1", "Course 2": "Duration 2"}},
                            "skill_level": {{"Course 1": "Level 1", "Course 2": "Level 2"}},
                            "certification": {{"Course 1": true, "Course 2": false}}
                        }},
                        "review_details": {{
                            "total_reviews": 0,
                            "highlights": ["Positive point 1", "Positive point 2"],
                            "concerns": ["Concern 1", "Concern 2"]
                        }}
                    }}
                ]
            }}"""),
            ("user", "Extract structured course data from these search results: {results}")
        ])
        
        # Modified search terms specifically for GenAI and AI Agents
        expanded_terms = [
            "LangChain development course certification",
            "AutoGPT programming tutorial professional",
            "CrewAI framework course training",
            "multi-agent systems development course",
            "generative AI programming certification",
            "AI agents LangChain AutoGPT course",
            "LLM integration programming tutorial",
            "autonomous AI agents development course"
        ]
        
        # Combine all search terms
        all_terms = list(set(
            search_terms.main_terms[:4] + 
            search_terms.related_terms[:2] +  # Added related terms
            expanded_terms[:4]
        ))
        
        print("\nUsing search terms:")
        for term in all_terms:
            print(f"- {term}")
        
        companies = []
        
        for term in all_terms:
            try:
                print(f"\nSearching for: {term}")
                search_queries = [
                    f"{term} course price reviews",
                    f"{term} training certification"
                ]
                
                for query in search_queries:
                    results = await self.llm_service.tavily_search.ainvoke(query)
                    await asyncio.sleep(1)  # Add small delay between searches
                    
                    # Process results to JSON
                    process_results = search_prompt | self.llm_service.long_context_llm | JsonOutputParser()
                    result_json = await process_results.ainvoke({
                        "results": results
                    })
                    
                    if isinstance(result_json, str):
                        result_json = json.loads(result_json)
                    
                    # Filter courses to ensure they're relevant
                    for company_data in result_json.get("companies", []):
                        try:
                            # Only include if services contain relevant keywords
                            relevant_keywords = [
                                "genai", "generative ai", "langchain", "autogpt", 
                                "crewai", "llm", "agent", "multi-agent", "autonomous"
                            ]
                            
                            services = [s.lower() for s in company_data.get("services", [])]
                            if any(keyword in " ".join(services) for keyword in relevant_keywords):
                                company = CompanyInfo.create_with_defaults(company_data)
                                companies.append(company)
                                print(f"Found relevant company: {company.name}")
                                print(f"  Courses: {', '.join(company.services)}")
                            else:
                                print(f"Skipping non-relevant courses from: {company_data.get('name', 'Unknown')}")
                                
                        except Exception as e:
                            print(f"Warning: Failed to parse company data: {str(e)}")
                            continue
                
            except Exception as e:
                print(f"Warning: Search error for '{term}': {str(e)}")
                continue
        
        # Remove duplicates based on company name
        unique_companies = {company.name: company for company in companies}.values()
        print(f"\nTotal unique companies found: {len(unique_companies)}")
        
        print("\nRelevant companies found:")
        for company in unique_companies:
            print(f"- {company.name}")
            if company.services:
                print(f"  Courses: {', '.join(company.services)}")
            if company.rating:
                print(f"  Rating: {company.rating}")
            if company.pricing:
                for course, price in company.pricing.items():
                    print(f"  Price for {course}: {price}")
        
        return {**state, "companies": list(unique_companies)}


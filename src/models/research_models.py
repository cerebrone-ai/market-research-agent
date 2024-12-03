from typing import List, TypedDict, Optional, Dict
from pydantic import BaseModel, Field

class CompanyInfo(BaseModel):
    name: str
    services: List[str]
    pricing: Dict[str, str]
    contact: Optional[str] = Field(default="Not available")
    location: str
    website: Optional[str] = Field(default="Not available")
    rating: Optional[float] = Field(default=None)

    @classmethod
    def create_with_defaults(cls, data: dict) -> 'CompanyInfo':
        cleaned_data = {
            "name": data.get("name", "Unknown Company"),
            "services": data.get("services", ["General Cleaning"]),
            "pricing": data.get("pricing", {"General Service": "Contact for pricing"}),
            "location": data.get("location", "Service area not specified"),
            "contact": data.get("contact", "Not available"),
            "website": data.get("website", "Not available"),
            "rating": None if data.get("rating") in [None, "Not available"] else float(data.get("rating", 0))
        }
        return cls(**cleaned_data)

class SearchTerms(BaseModel):
    main_terms: List[str]
    related_terms: List[str]

class MarketResearchState(TypedDict):
    topic: str
    search_terms: SearchTerms
    companies: List[CompanyInfo]
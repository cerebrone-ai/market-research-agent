from typing import List, TypedDict, Optional, Dict
from pydantic import BaseModel, Field

class CompanyInfo(BaseModel):
    name: str
    services: List[str]
    pricing: Dict[str, str]
    contact: Optional[str] = Field(default="Not available")
    location: str
    website: Optional[str] = Field(default="Not available")
    rating: Optional[str] = Field(default="Not found")
    review_details: Optional[Dict] = Field(default_factory=lambda: {
        "total_reviews": "Not found",
        "highlights": [],
        "concerns": []
    })

    @classmethod
    def create_with_defaults(cls, data: dict) -> 'CompanyInfo':
        raw_rating = data.get("rating")
        if raw_rating is None or raw_rating == "Not available":
            rating = "Not found"
        elif raw_rating == 0:
            rating = "0.0"
        else:
            try:
                rating = f"{float(raw_rating):.1f}"
            except (ValueError, TypeError):
                rating = "Not found"

        review_details = data.get("review_details", {})
        total_reviews = review_details.get("total_reviews")
        if total_reviews is None:
            total_reviews = "Not found"
        elif total_reviews == 0:
            total_reviews = "0"
        else:
            total_reviews = str(total_reviews)

        cleaned_data = {
            "name": data.get("name", "Unknown Company"),
            "services": data.get("services", ["General Cleaning"]),
            "pricing": data.get("pricing", {"General Service": "Contact for pricing"}),
            "location": data.get("location", "Service area not specified"),
            "contact": data.get("contact", "Not available"),
            "website": data.get("website", "Not available"),
            "rating": rating,
            "review_details": {
                "total_reviews": total_reviews,
                "highlights": review_details.get("highlights", []),
                "concerns": review_details.get("concerns", [])
            }
        }
        return cls(**cleaned_data)

class SearchTerms(BaseModel):
    main_terms: List[str]
    related_terms: List[str]

class MarketResearchState(TypedDict):
    topic: str
    search_terms: SearchTerms
    companies: List[CompanyInfo]
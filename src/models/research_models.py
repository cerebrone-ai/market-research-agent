from typing import List, TypedDict, Optional, Dict
from pydantic import BaseModel, Field

class CompanyInfo(BaseModel):
    name: str
    services: List[str]
    pricing: Dict[str, str]
    contact: Optional[str] = Field(default="Not available")
    website: Optional[str] = Field(default="Not available")
    rating: Optional[str] = Field(default="Not found")
    course_details: Dict[str, Dict] = Field(default_factory=lambda: {
        "durations": {},
        "skill_level": {},
        "certification": {}
    })
    review_details: Optional[Dict] = Field(default_factory=lambda: {
        "total_reviews": "Not found",
        "highlights": [],
        "concerns": []
    })

    @classmethod
    def create_with_defaults(cls, data: dict) -> 'CompanyInfo':
        course_details = data.get("course_details", {})
        if not course_details:
            course_details = {
                "durations": {},
                "skill_level": {},
                "certification": {}
            }

        cleaned_data = {
            "name": data.get("name", "Unknown Provider"),
            "services": data.get("services", ["No courses listed"]),
            "pricing": data.get("pricing", {}),
            "contact": data.get("contact", "Not available"),
            "website": data.get("website", "Not available"),
            "rating": cls._clean_rating(data.get("rating")),
            "course_details": course_details,
            "review_details": {
                "total_reviews": cls._clean_total_reviews(data.get("review_details", {}).get("total_reviews")),
                "highlights": data.get("review_details", {}).get("highlights", []),
                "concerns": data.get("review_details", {}).get("concerns", [])
            }
        }
        return cls(**cleaned_data)

    @staticmethod
    def _clean_rating(rating: Optional[str]) -> str:
        if rating is None or rating == "Not available":
            return "Not found"
        elif rating == 0:
            return "0.0"
        else:
            try:
                return f"{float(rating):.1f}"
            except (ValueError, TypeError):
                return "Not found"

    @staticmethod
    def _clean_total_reviews(total_reviews: Optional[str]) -> str:
        if total_reviews is None:
            return "Not found"
        elif total_reviews == 0:
            return "0"
        else:
            return str(total_reviews)

class SearchTerms(BaseModel):
    main_terms: List[str]
    related_terms: List[str]

class MarketResearchState(TypedDict):
    topic: str
    search_terms: SearchTerms
    companies: List[CompanyInfo]
    output_file: Optional[str]
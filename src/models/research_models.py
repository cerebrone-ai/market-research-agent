from typing import List, Dict, Optional, Any, TypedDict
from pydantic import BaseModel, Field

class CompanyInfo(BaseModel):
    name: str
    products: List[str] = Field(default_factory=list)
    pricing: Dict[str, str] = Field(default_factory=dict)
    contact: Optional[str] = Field(default="Not available")
    website: Optional[str] = Field(default="Not available")
    rating: Optional[str] = Field(default="Not found")
    product_details: Dict[str, Dict] = Field(default_factory=lambda: {
        "features": {},
        "specifications": {},
        "availability": {}
    })
    review_analysis: Dict[str, Any] = Field(default_factory=lambda: {
        "total_reviews": "Not found",
        "average_rating": "Not found",
        "positive_points": [],
        "negative_points": [],
        "customer_sentiment": "Not analyzed"
    })
    market_details: Dict[str, Any] = Field(default_factory=lambda: {
        "market_share": "Not available",
        "target_segment": "Not specified",
        "key_competitors": []
    })

class SearchTerms(BaseModel):
    main_terms: List[str]
    related_terms: List[str]

class MarketResearchState(TypedDict):
    topic: str
    search_terms: Optional[SearchTerms]
    companies: List[CompanyInfo]
    output_file: Optional[str]

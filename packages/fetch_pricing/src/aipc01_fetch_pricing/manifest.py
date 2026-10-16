from __future__ import annotations

from pydantic import BaseModel, Field


class Offer(BaseModel):
    id: str
    offer_code: str  # Price List offer code, e.g. AmazonBedrock
    title: str
    services: list[str] = Field(default_factory=list)
    exam_domains: list[int] = Field(default_factory=list)


class PricingManifest(BaseModel):
    base_url: str = "https://pricing.us-east-1.amazonaws.com"
    regions: list[str]
    offers: list[Offer]

"""Pydantic request/response schemas."""
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, EmailStr, Field, HttpUrl, field_validator


# ── Auth ──────────────────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: str
    email: str
    full_name: Optional[str] = None
    is_active: bool
    is_superuser: bool = False
    created_at: datetime

    model_config = {"from_attributes": True}


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ── Organization ──────────────────────────────────────────────────────────────

class OrganizationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    slug: Optional[str] = None


class OrganizationOut(BaseModel):
    id: str
    name: str
    slug: str
    plan: str
    max_websites: int
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Website ───────────────────────────────────────────────────────────────────

class WebsiteCreate(BaseModel):
    url: str = Field(..., min_length=4, max_length=2048)
    name: Optional[str] = None
    organization_id: Optional[str] = None  # if user has multiple orgs

    @field_validator("url")
    @classmethod
    def normalize_url(cls, v: str) -> str:
        v = v.strip()
        if not v.startswith(("http://", "https://")):
            v = "https://" + v
        return v


class WebsiteOut(BaseModel):
    id: str
    organization_id: str
    url: str
    domain: str
    name: Optional[str] = None
    is_valid: bool
    validation_error: Optional[str] = None
    technology_stack: Optional[dict] = None
    has_sitemap: bool
    has_robots: bool
    sitemap_url: Optional[str] = None
    robots_url: Optional[str] = None
    status: str
    last_crawled_at: Optional[datetime] = None
    last_score: Optional[int] = None
    max_pages: int
    crawl_depth: int
    auto_optimize: bool
    require_approval: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class WebsiteList(BaseModel):
    items: list[WebsiteOut]
    total: int


# ── Crawl ─────────────────────────────────────────────────────────────────────

class CrawlStart(BaseModel):
    max_pages: Optional[int] = Field(None, ge=1, le=500)
    max_depth: Optional[int] = Field(None, ge=1, le=10)


class CrawlRunOut(BaseModel):
    id: str
    website_id: str
    status: str
    progress: int
    current_step: Optional[str] = None
    message: Optional[str] = None
    pages_discovered: int
    pages_crawled: int
    pages_failed: int
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    error: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── SEO Score ─────────────────────────────────────────────────────────────────

class SEOScoreOut(BaseModel):
    id: str
    website_id: str
    overall: int
    technical: int
    on_page: int
    content: int
    performance: int
    indexability: int
    structured_data: int
    internal_linking: int
    mobile: int
    accessibility: int
    authority: int
    details: Optional[dict] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Issues ────────────────────────────────────────────────────────────────────

class SEOIssueOut(BaseModel):
    id: str
    website_id: str
    page_id: Optional[str] = None
    category: str
    code: str
    severity: str
    title: str
    description: str
    why_it_matters: Optional[str] = None
    recommended_fix: Optional[str] = None
    expected_impact: Optional[str] = None
    effort: Optional[str] = None
    priority_score: Optional[float] = None
    status: str
    data: Optional[dict] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Generic ───────────────────────────────────────────────────────────────────

class Message(BaseModel):
    message: str


class Health(BaseModel):
    status: str
    version: str
    environment: str


# ── Keywords / Recommendations ────────────────────────────────────────────────

class KeywordOut(BaseModel):
    id: str
    website_id: str
    page_id: Optional[str] = None
    keyword: str
    type: str
    search_intent: Optional[str] = None
    recommended_title: Optional[str] = None
    recommended_h1: Optional[str] = None
    recommended_meta: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class RecommendationOut(BaseModel):
    id: str
    website_id: str
    category: str
    title: str
    what: str
    why: str
    how: str
    impact: str
    effort: str
    priority: float
    auto_applicable: bool
    requires_approval: bool
    status: str
    suggested_change: Optional[dict] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ReportOut(BaseModel):
    id: str
    website_id: str
    title: str
    report_type: str
    status: str
    summary: Optional[str] = None
    content: Optional[dict] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ReportListItem(BaseModel):
    id: str
    website_id: str
    title: str
    report_type: str
    status: str
    summary: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}

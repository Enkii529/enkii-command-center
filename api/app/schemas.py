from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict


class VentureBase(BaseModel):
    name: str
    slug: str
    description: Optional[str] = None
    status: str = "active"


class VentureCreate(VentureBase):
    pass


class VentureRead(VentureBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProjectBase(BaseModel):
    venture_id: Optional[int] = None
    name: str
    description: Optional[str] = None
    status: str = "active"
    priority: str = "medium"


class ProjectCreate(ProjectBase):
    pass


class ProjectRead(ProjectBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TaskBase(BaseModel):
    venture_id: Optional[int] = None
    project_id: Optional[int] = None
    title: str
    description: Optional[str] = None
    status: str = "todo"
    priority: str = "medium"
    due_date: Optional[date] = None
    assigned_to: Optional[str] = None


class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    due_date: Optional[date] = None
    assigned_to: Optional[str] = None


class TaskRead(TaskBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ContentItemBase(BaseModel):
    venture_id: Optional[int] = None
    project_id: Optional[int] = None
    title: str
    platform: Optional[str] = None
    stage: str = "idea"
    content_type: Optional[str] = None
    hook: Optional[str] = None
    cta: Optional[str] = None


class ContentItemCreate(ContentItemBase):
    pass


class ContentItemRead(ContentItemBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentBase(BaseModel):
    title: str
    source_type: str = "manual"
    source_url: Optional[str] = None
    raw_text: Optional[str] = None
    status: str = "new"


class DocumentCreate(DocumentBase):
    pass


class DocumentRead(DocumentBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TradeBase(BaseModel):
    account_id: Optional[int] = None
    symbol: str
    side: str
    quantity: Decimal
    price: Decimal
    rationale: Optional[str] = None
    strategy_tag: Optional[str] = None


class TradeCreate(TradeBase):
    pass


class TradeRead(TradeBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SummaryResponse(BaseModel):
    ventures_total: int
    projects_active: int
    tasks_open: int
    tasks_due_today: int
    content_in_pipeline: int
    new_documents: int
    trades_total: int

from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class SecurityHeaders(BaseModel):
    strict_transport_security: bool
    content_security_policy: bool
    x_content_type_options: bool
    x_frame_options: bool


class AuditResponse(BaseModel):
    url: str
    final_url: str
    status_code: int
    reachable: bool
    response_time_ms: int
    redirected: bool
    redirect_chain: list[str]
    content_type: Optional[str] = None
    content_length_bytes: Optional[int] = None
    title: Optional[str] = None
    meta_description: Optional[str] = None
    h1_count: int
    security_headers: SecurityHeaders
    cached: bool = False
    audited_at: datetime
    request_id: str


class ErrorDetail(BaseModel):
    code: str
    message: str
    request_id: str
    details: dict = {}


class ErrorResponse(BaseModel):
    error: ErrorDetail

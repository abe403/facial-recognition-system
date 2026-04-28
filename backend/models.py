"""
Pydantic models — request/response schemas for the API.
"""
from pydantic import BaseModel, Field
from typing import Optional


class MemberCreate(BaseModel):
    """Request body for registering a new member — no ID needed, it's auto-assigned."""
    name: str = Field(..., min_length=1, examples=["Juan Pérez"])
    expiration_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$", examples=["2027-01-15"])


class MemberUpdate(BaseModel):
    """Request body for updating member data."""
    name: Optional[str] = Field(None, min_length=1)
    expiration_date: Optional[str] = Field(None, pattern=r"^\d{4}-\d{2}-\d{2}$")


class MemberResponse(BaseModel):
    """Response body for a member."""
    member_number: int
    membership_id: str
    name: str
    expiration_date: str
    has_face_sample: bool = False


class FaceImage(BaseModel):
    """Base64-encoded face image from the browser webcam."""
    image: str = Field(..., description="Base64-encoded JPEG/PNG image data")


class RecognitionResult(BaseModel):
    """Result of a face recognition attempt."""
    recognized: bool
    member_number: Optional[int] = None
    membership_id: Optional[str] = None
    name: Optional[str] = None
    confidence: Optional[float] = None
    access_granted: Optional[bool] = None
    expiration_date: Optional[str] = None
    message: str = ""


class AttendanceRecord(BaseModel):
    """A single attendance log entry."""
    id: Optional[int] = None
    member_number: int = 0
    membership_id: str
    name: str
    date: str
    time: str


class StatsResponse(BaseModel):
    """Dashboard statistics."""
    total_members: int
    active_members: int
    expired_members: int
    entries_today: int
    entries_this_week: int

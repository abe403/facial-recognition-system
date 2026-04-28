"""
FaceGym API — FastAPI backend for the facial recognition access control system.
"""
import logging
import os
from datetime import datetime, timedelta
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm

import database as db
import recognizer as rec
import security
from models import (
    MemberCreate,
    MemberUpdate,
    MemberResponse,
    FaceImage,
    RecognitionResult,
    AttendanceRecord,
    StatsResponse,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ── Lifespan ─────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize DB, create default admin, and train model on startup."""
    db.init_db()
    
    # Create default admin if none exists
    if not db.get_admin("admin"):
        hashed = security.get_password_hash("admin123")
        db.create_admin("admin", hashed)
        logger.info("Default admin user created (admin / admin123)")
    
    rec.train_model()
    logger.info("FaceGym API ready")
    yield


# ── App ──────────────────────────────────────────────────────────

app = FastAPI(
    title="FaceGym API",
    description="Facial Recognition Access Control System",
    version="2.1.0",
    lifespan=lifespan,
)


# ── Global Error Handler ──────────────────────────────────────────

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled error on %s: %s", request.url, exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal Server Error: {str(exc)}"},
    )


# ── CORS ──────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Helpers ───────────────────────────────────────────────────────

def _to_response(member: dict) -> MemberResponse:
    face_path = os.path.join(db.get_samples_dir(), f"{member['membership_id']}.png")
    return MemberResponse(**member, has_face_sample=os.path.exists(face_path))


# ── Authentication ────────────────────────────────────────────────

@app.post("/api/auth/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = db.get_admin(form_data.username)
    if not user or not security.verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = security.create_access_token(data={"sub": user["username"]})
    return {"access_token": access_token, "token_type": "bearer"}


# ── Members CRUD ──────────────────────────────────────────────────

@app.post("/api/members", response_model=MemberResponse, status_code=status.HTTP_201_CREATED)
def register_member(body: MemberCreate, current_admin: str = Depends(security.get_current_admin)):
    """Register a new gym member."""
    try:
        exp = datetime.strptime(body.expiration_date, "%Y-%m-%d").date()
        if exp < datetime.today().date():
            raise HTTPException(400, "Expiration date cannot be in the past")
    except ValueError:
        raise HTTPException(400, "Invalid date format (expected YYYY-MM-DD)")

    member = db.create_member(body.name, body.expiration_date)
    return _to_response(member)


@app.get("/api/members", response_model=list[MemberResponse])
def list_members(current_admin: str = Depends(security.get_current_admin)):
    return [_to_response(m) for m in db.get_all_members()]


@app.get("/api/members/{membership_id}", response_model=MemberResponse)
def get_member(membership_id: str, current_admin: str = Depends(security.get_current_admin)):
    member = db.get_member(membership_id)
    if not member:
        raise HTTPException(404, "Member not found")
    return _to_response(member)


@app.put("/api/members/{membership_id}", response_model=MemberResponse)
def update_member(membership_id: str, body: MemberUpdate, current_admin: str = Depends(security.get_current_admin)):
    existing = db.get_member(membership_id)
    if not existing:
        raise HTTPException(404, "Member not found")

    name = body.name or existing["name"]
    exp = body.expiration_date or existing["expiration_date"]
    updated = db.update_member(membership_id, name, exp)
    return _to_response(updated)


@app.delete("/api/members/{membership_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_member(membership_id: str, current_admin: str = Depends(security.get_current_admin)):
    if not db.delete_member(membership_id):
        raise HTTPException(404, "Member not found")
    rec.delete_face_sample(membership_id)
    rec.train_model()


# ── Face Sample Upload ────────────────────────────────────────────

@app.post("/api/members/{membership_id}/face", response_model=MemberResponse)
def upload_face(membership_id: str, body: FaceImage, current_admin: str = Depends(security.get_current_admin)):
    member = db.get_member(membership_id)
    if not member:
        raise HTTPException(404, "Member not found")

    try:
        img = rec.decode_base64_image(body.image)
    except Exception as e:
        logger.error("Image decode error: %s", e)
        raise HTTPException(400, "Invalid image data")

    face_roi = rec.detect_face(img)
    if face_roi is None:
        raise HTTPException(
            422, "Could not detect exactly one face. Ensure face is centered and well-lit."
        )

    rec.save_face_sample(membership_id, face_roi)
    rec.train_model()
    return _to_response(member)


# ── Face Recognition (PUBLIC) ─────────────────────────────────────

@app.post("/api/recognize", response_model=RecognitionResult)
def recognize(body: FaceImage):
    all_members = db.get_all_members()
    if not all_members:
        return RecognitionResult(
            recognized=False,
            message="No members registered yet. Please register a member first.",
        )

    try:
        img = rec.decode_base64_image(body.image)
    except Exception as e:
        logger.error("Image decode error: %s", e)
        raise HTTPException(400, "Invalid image data")

    face_roi = rec.detect_face(img)
    if face_roi is None:
        return RecognitionResult(
            recognized=False,
            message="No face detected. Please center your face and try again.",
        )

    membership_id, confidence = rec.recognize_face(face_roi)

    if membership_id is None:
        return RecognitionResult(
            recognized=False,
            confidence=round(confidence, 2),
            message="Face not recognized. Please try again or contact staff.",
        )

    member = db.get_member(membership_id)
    if not member:
        return RecognitionResult(recognized=False, message="Member record not found.")

    exp_date = datetime.strptime(member["expiration_date"], "%Y-%m-%d").date()
    today = datetime.today().date()
    access_granted = exp_date >= today

    if access_granted:
        db.log_attendance(membership_id, member["name"])

    days_left = (exp_date - today).days
    if access_granted and days_left <= 7:
        msg = f"Welcome, {member['name']}! ⚠️ Membership expires in {days_left} day{'s' if days_left != 1 else ''}."
    elif access_granted:
        msg = f"Welcome, {member['name']}! Access granted."
    else:
        msg = f"Access denied. Membership for {member['name']} expired on {member['expiration_date']}."

    return RecognitionResult(
        recognized=True,
        member_number=member["member_number"],
        membership_id=membership_id,
        name=member["name"],
        confidence=round(confidence, 2),
        access_granted=access_granted,
        expiration_date=member["expiration_date"],
        message=msg,
    )


# ── Attendance ────────────────────────────────────────────────────

@app.get("/api/attendance", response_model=list[AttendanceRecord])
def get_attendance(current_admin: str = Depends(security.get_current_admin)):
    return db.get_attendance(limit=50)


# ── Dashboard Stats ───────────────────────────────────────────────

@app.get("/api/stats", response_model=StatsResponse)
def get_stats(current_admin: str = Depends(security.get_current_admin)):
    members = db.get_all_members()
    today = datetime.today().date()
    week_ago = today - timedelta(days=7)

    active = sum(
        1 for m in members
        if datetime.strptime(m["expiration_date"], "%Y-%m-%d").date() >= today
    )

    attendance = db.get_attendance(limit=1000)
    entries_today = sum(1 for a in attendance if a["date"] == today.isoformat())
    entries_week = sum(
        1 for a in attendance
        if datetime.strptime(a["date"], "%Y-%m-%d").date() >= week_ago
    )

    return StatsResponse(
        total_members=len(members),
        active_members=active,
        expired_members=len(members) - active,
        entries_today=entries_today,
        entries_this_week=entries_week,
    )

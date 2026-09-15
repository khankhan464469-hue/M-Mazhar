from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from supabase import create_client
from dotenv import load_dotenv
import os
from pathlib import Path

load_dotenv()

app = FastAPI()
bearer_scheme = HTTPBearer(auto_error=False)
frontend_dir = Path(__file__).resolve().parent.parent / "frontend"

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
customer_db_role = os.getenv("CUSTOMER_DB_ROLE", "customer")

supabase = create_client(url, key)

if frontend_dir.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")

auth_responses = {
    401: {
        "description": "Unauthorized",
        "content": {
            "application/json": {
                "example": {
                    "detail": "Authorization header must be: Bearer <access_token>"
                }
            }
        },
    },
    403: {
        "description": "Forbidden",
        "content": {
            "application/json": {
                "example": {"detail": "Admin access required"}
            }
        },
    },
}


class EventCreate(BaseModel):
    title: str
    description: str
    event_date: str
    event_time: str
    location: str
    capacity: int
    status: str


class EventUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    event_date: str | None = None
    event_time: str | None = None
    location: str | None = None
    capacity: int | None = None
    status: str | None = None


class SignupRequest(BaseModel):
    email: str
    password: str
    full_name: str


class AdminSignupRequest(SignupRequest):
    admin_code: str


class LoginRequest(BaseModel):
    email: str
    password: str


class PasswordResetRequest(BaseModel):
    email: str


def create_profile(user, full_name: str, role: str):
    full_profile = {
        "id": user.id,
        "email": user.email,
        "full_name": full_name,
        "role": role,
    }

    try:
        result = supabase.table("profiles").upsert(full_profile).execute()
        return {"saved": True, "data": result.data}
    except Exception as full_error:
        try:
            result = supabase.table("profiles").upsert({
                "id": user.id,
                "full_name": full_name,
                "role": role,
            }).execute()
            return {"saved": True, "data": result.data}
        except Exception as fallback_error:
            return {
                "saved": False,
                "error": str(fallback_error),
                "schema_hint": str(full_error),
            }


def require_admin(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    if not credentials:
        raise HTTPException(
            status_code=401,
            detail="Authorization header must be: Bearer <access_token>",
        )

    try:
        user_result = supabase.auth.get_user(credentials.credentials)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    if not user_result.user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    profile = supabase.table("profiles") \
        .select("role") \
        .eq("id", user_result.user.id) \
        .single() \
        .execute()

    if not profile.data or profile.data["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    return user_result.user


def public_role(role: str | None):
    if role == customer_db_role:
        return "customer"

    return role or "customer"


@app.get("/")
def home():
    index_file = frontend_dir / "index.html"
    if index_file.exists():
        return FileResponse(index_file)

    return {"message": "API is running"}

@app.post("/signup")
def signup(data: SignupRequest):
    try:
        result = supabase.auth.sign_up({
            "email": data.email,
            "password": data.password,
            "options": {
                "data": {"full_name": data.full_name, "role": "customer"}
            }
        })

        if not result.user:
            raise HTTPException(status_code=400, detail="Signup failed")

        profile_result = create_profile(result.user, data.full_name, customer_db_role)

        return {
            "message": "Customer account created successfully",
            "user_id": result.user.id,
            "email": result.user.email,
            "role": "customer",
            "profile_saved": profile_result["saved"],
            "note": (
                None
                if profile_result["saved"]
                else "Account is saved in Supabase Auth. Run backend/supabase_schema.sql once to save customer rows in profiles."
            ),
        }

    except HTTPException:
        raise
    except Exception as e:
        return {"error": str(e)}

@app.post("/admin/signup")
def admin_signup(data: AdminSignupRequest):
    try:
        load_dotenv(override=True)
        admin_signup_code = os.getenv("ADMIN_SIGNUP_CODE")

        if not admin_signup_code:
            raise HTTPException(
                status_code=403,
                detail="Admin signup is disabled. Set ADMIN_SIGNUP_CODE in .env first.",
            )

        if data.admin_code != admin_signup_code:
            raise HTTPException(status_code=403, detail="Invalid admin signup code")

        result = supabase.auth.sign_up({
            "email": data.email,
            "password": data.password,
            "options": {
                "data": {"full_name": data.full_name, "role": "admin"}
            }
        })

        if not result.user:
            raise HTTPException(status_code=400, detail="Signup failed")

        profile_result = create_profile(result.user, data.full_name, "admin")

        return {
            "message": "Admin signup successful",
            "user_id": result.user.id,
            "email": result.user.email,
            "role": "admin",
            "profile_saved": profile_result["saved"],
        }

    except HTTPException:
        raise
    except Exception as e:
        return {"error": str(e)}

@app.post("/login")
def login(data: LoginRequest):
    try:
        result = supabase.auth.sign_in_with_password({
            "email": data.email,
            "password": data.password
        })

        profile = supabase.table("profiles") \
            .select("*") \
            .eq("id", result.user.id) \
            .single() \
            .execute()

        return {
            "message": "Login successful",
            "access_token": result.session.access_token,
            "user_id": result.user.id,
            "email": result.user.email,
            "role": public_role(profile.data["role"] if profile.data else None),
            "full_name": (
                profile.data.get("full_name")
                if profile.data
                else result.user.user_metadata.get("full_name")
            ),
        }

    except Exception as e:
        return {"error": str(e)}

@app.post("/forgot-password")
def forgot_password(data: PasswordResetRequest):
    try:
        supabase.auth.reset_password_email(data.email)

        return {
            "message": "Password reset email sent. Please check your inbox.",
            "email": data.email
        }

    except Exception as e:
        return {"error": str(e)}

@app.get("/profiles/customers", responses=auth_responses)
def get_customers(user=Depends(require_admin)):
    try:
        result = supabase.table("profiles") \
            .select("*") \
            .eq("role", customer_db_role) \
            .execute()

        return {
            "message": "Customers fetched successfully",
            "customers": result.data
        }

    except Exception as e:
        return {"error": str(e)}


@app.get("/profiles/admins", responses=auth_responses)
def get_admins(user=Depends(require_admin)):
    try:
        result = supabase.table("profiles") \
            .select("*") \
            .eq("role", "admin") \
            .execute()

        return {
            "message": "Admins fetched successfully",
            "admins": result.data
        }

    except Exception as e:
        return {"error": str(e)}

@app.get("/events")
def get_events():
    try:
        result = supabase.table("events").select("*").execute()

        return {
            "message": "Events fetched successfully",
            "events": result.data
        }

    except Exception as e:
        return {"error": str(e)}


@app.get("/events/{event_id}")
def get_event(event_id: int):
    try:
        result = supabase.table("events") \
            .select("*") \
            .eq("id", event_id) \
            .single() \
            .execute()

        if not result.data:
            raise HTTPException(status_code=404, detail="Event not found")

        return {
            "message": "Event fetched successfully",
            "event": result.data
        }

    except HTTPException:
        raise
    except Exception as e:
        return {"error": str(e)}


@app.post(
    "/events",
    responses=auth_responses,
)
def create_event(
    data: EventCreate,
    user=Depends(require_admin),
):
    try:
        result = supabase.table("events").insert(data.model_dump()).execute()

        return {
            "message": "Event created successfully",
            "event": result.data
        }

    except HTTPException:
        raise
    except Exception as e:
        return {"error": str(e)}


@app.put(
    "/events/{event_id}",
    responses={
        **auth_responses,
        404: {
            "description": "Not Found",
            "content": {
                "application/json": {
                    "example": {"detail": "Event not found"}
                }
            },
        },
    },
)
def update_event(
    event_id: int,
    data: EventUpdate,
    user=Depends(require_admin),
):
    try:
        update_data = data.model_dump(exclude_unset=True)

        if not update_data:
            raise HTTPException(status_code=400, detail="No update data provided")

        result = supabase.table("events") \
            .update(update_data) \
            .eq("id", event_id) \
            .execute()

        if not result.data:
            raise HTTPException(status_code=404, detail="Event not found")

        return {
            "message": "Event updated successfully",
            "event": result.data
        }

    except HTTPException:
        raise
    except Exception as e:
        return {"error": str(e)}


@app.delete(
    "/events/{event_id}",
    responses={
        **auth_responses,
        404: {
            "description": "Not Found",
            "content": {
                "application/json": {
                    "example": {"detail": "Event not found"}
                }
            },
        },
    },
)
def delete_event(
    event_id: int,
    user=Depends(require_admin),
):
    try:
        result = supabase.table("events") \
            .delete() \
            .eq("id", event_id) \
            .execute()

        if not result.data:
            raise HTTPException(status_code=404, detail="Event not found")

        return {
            "message": "Event deleted successfully",
            "event": result.data
        }

    except HTTPException:
        raise
    except Exception as e:
        return {"error": str(e)}

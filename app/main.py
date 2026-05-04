from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from app.database import database
from app.routes.auth_routes import router as auth_router
from app.routes.plant_routes import router as plant_router
from app.services.email_service import missing_smtp_fields, smtp_is_configured


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not smtp_is_configured():
        missing = ", ".join(missing_smtp_fields())
        print(
            "[Rayhana WARNING] SMTP email is not fully configured. "
            f"Missing: {missing}. Email verification will use development "
            "console codes until SMTP is configured."
        )

    yield

app = FastAPI(
    title="Rayhana Backend",
    description="Backend API for Rayhana Smart Basil Care System",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(auth_router)
app.include_router(plant_router)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"detail": _clean_validation_error(exc.errors())}
    )


def _clean_validation_error(errors):
    if not errors:
        return "Invalid request"

    error = errors[0]
    message = error.get("msg", "Invalid request")
    location = error.get("loc", [])
    field = location[-1] if location else None

    field_names = {
        "full_name": "Full name",
        "email": "Email",
        "password": "Password",
        "new_password": "Password",
        "phone": "Phone number",
        "phone_number": "Phone number",
        "garden_location": "Garden location",
        "code": "Verification code",
    }
    label = field_names.get(field, str(field).replace("_", " ").title() if field else "Field")

    if message.lower().startswith("field required"):
        return f"{label} is required"

    if message.startswith("Value error, "):
        return message.replace("Value error, ", "", 1)

    return message


@app.get("/")
async def root():
    try:
        collections = await database.list_collection_names()
        return {
            "message": "Rayhana Backend is running successfully",
            "database_status": "connected",
            "collections": collections
        }
    except Exception as e:
        return {
            "message": "Rayhana Backend is running",
            "database_status": "error",
            "error": str(e)
        }

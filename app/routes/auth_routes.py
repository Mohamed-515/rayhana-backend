import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Depends
from bson import ObjectId
from app.schemas.user_schema import (
    ForgotPasswordRequest,
    GoogleAuthRequest,
    ResendVerificationRequest,
    ResetPasswordRequest,
    TestEmailRequest,
    UserRegister,
    UserLogin,
    UserProfileUpdate,
    VerifyEmailRequest,
)
from app.config import settings
from app.database import database
from app.services.email_service import (
    print_dev_password_reset_code,
    print_dev_verification_code,
    send_password_reset_email,
    send_test_email,
    send_verification_email,
)
from app.utils.security import (
    hash_password,
    verify_password,
    create_access_token,
    verify_access_token
)

router = APIRouter()

users_collection = database["users"]
VERIFICATION_CODE_MINUTES = 15
PASSWORD_RESET_CODE_MINUTES = 15
PASSWORD_RESET_GENERIC_MESSAGE = (
    "If an account exists for this email, a reset code has been sent."
)


def generate_verification_code() -> str:
    return f"{secrets.randbelow(1000000):06d}"


def verification_expiry() -> datetime:
    return datetime.now(timezone.utc) + timedelta(minutes=VERIFICATION_CODE_MINUTES)


def password_reset_expiry() -> datetime:
    return datetime.now(timezone.utc) + timedelta(minutes=PASSWORD_RESET_CODE_MINUTES)


def normalize_expiry(value):
    if value is None:
        return None

    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)

    return value


def is_development() -> bool:
    return settings.ENVIRONMENT.lower() == "development"


async def send_and_store_verification_code(
    user_id,
    email: str,
    full_name: str,
    *,
    success_message: str,
    fallback_message: str,
    dev_failure_message: str = (
        "Verification email could not be sent. In development, use the "
        "backend console code."
    ),
    raise_on_delivery_failure: bool = False,
):
    verification_code = generate_verification_code()
    expires_at = verification_expiry()

    await users_collection.update_one(
        {"_id": user_id},
        {
            "$set": {
                "verification_code": verification_code,
                "verification_expires_at": expires_at,
            }
        },
    )

    try:
        email_sent = await send_verification_email(
            to_email=email,
            full_name=full_name,
            code=verification_code,
        )
    except Exception:
        if is_development():
            print_dev_verification_code(email=email, code=verification_code)
            return {
                "message": dev_failure_message,
                "email": email,
                "email_sent": False,
                "dev_code_available": True,
            }

        if raise_on_delivery_failure:
            raise HTTPException(
                status_code=503,
                detail="Could not send verification email. Please try again later.",
            )

        return {
            "message": fallback_message,
            "email": email,
            "email_sent": False,
            "dev_code_available": False,
        }

    if email_sent:
        return {
            "message": success_message,
            "email": email,
            "email_sent": True,
            "dev_code_available": False,
        }

    if is_development():
        return {
            "message": dev_failure_message,
            "email": email,
            "email_sent": False,
            "dev_code_available": True,
        }

    if raise_on_delivery_failure:
        raise HTTPException(
            status_code=503,
            detail="Could not send verification email. Please try again later.",
        )

    return {
        "message": fallback_message,
        "email": email,
        "email_sent": False,
        "dev_code_available": False,
    }


async def send_and_store_password_reset_code(user):
    reset_code = generate_verification_code()
    expires_at = password_reset_expiry()
    email = user["email"]

    await users_collection.update_one(
        {"_id": user["_id"]},
        {
            "$set": {
                "reset_password_code": reset_code,
                "reset_password_expires_at": expires_at,
            }
        },
    )

    try:
        email_sent = await send_password_reset_email(
            to_email=email,
            full_name=user.get("full_name", "Rayhana user"),
            code=reset_code,
        )
    except Exception:
        if is_development():
            print_dev_password_reset_code(email=email, code=reset_code)
            return {
                "message": (
                    "Could not send email. Use the latest backend console "
                    "code for development."
                ),
                "email": email,
                "email_sent": False,
                "dev_code_available": True,
            }

        raise HTTPException(
            status_code=503,
            detail="Could not send reset email. Please try again later.",
        )

    if email_sent:
        return {
            "message": PASSWORD_RESET_GENERIC_MESSAGE,
            "email": email,
            "email_sent": True,
            "dev_code_available": False,
        }

    if is_development():
        return {
            "message": (
                "Could not send email. Use the latest backend console code "
                "for development."
            ),
            "email": email,
            "email_sent": False,
            "dev_code_available": True,
        }

    raise HTTPException(
        status_code=503,
        detail="Could not send reset email. Please try again later.",
    )


def build_auth_response(user, message: str):
    access_token = create_access_token(
        data={
            "sub": str(user["_id"]),
            "email": user["email"]
        }
    )

    return {
        "message": message,
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": str(user["_id"]),
            "full_name": user.get("full_name"),
            "email": user["email"],
            "phone_number": user.get("phone_number"),
            "is_verified": user.get("is_verified", True),
            "auth_provider": user.get("auth_provider", "password"),
        }
    }


def build_user_profile(user):
    phone_number = user.get("phone_number")

    return {
        "id": str(user["_id"]),
        "full_name": user.get("full_name") or "Rayhana user",
        "email": user.get("email"),
        "phone": phone_number,
        "phone_number": phone_number,
        "garden_location": user.get("garden_location"),
        "is_verified": user.get("is_verified", False),
        "auth_provider": user.get("auth_provider", "password"),
    }


@router.post("/register")
async def register_user(user: UserRegister):
    existing_user = await users_collection.find_one({"email": user.email})

    if existing_user:
        if existing_user.get("is_verified") is True:
            raise HTTPException(
                status_code=400,
                detail="Email already registered. Please login.",
            )

        verification_response = await send_and_store_verification_code(
            existing_user["_id"],
            existing_user["email"],
            existing_user.get("full_name", user.full_name),
            success_message=(
                "Verification code sent again. Please check your email."
            ),
            fallback_message=(
                "Verification code was updated, but email could not be sent. "
                "Please use Resend Code."
            ),
        )

        return {
            **verification_response,
            "user_id": str(existing_user["_id"]),
        }

    hashed_password = hash_password(user.password)

    new_user = {
        "full_name": user.full_name,
        "email": user.email,
        "password": hashed_password,
        "phone_number": user.phone_number,
        "is_verified": False,
        "auth_provider": "password"
    }

    result = await users_collection.insert_one(new_user)
    verification_response = await send_and_store_verification_code(
        result.inserted_id,
        user.email,
        user.full_name,
        success_message="Verification code sent. Please check your email.",
        fallback_message=(
            "Account created, but verification email could not be sent. "
            "Please use Resend Code."
        ),
    )

    return {
        **verification_response,
        "user_id": str(result.inserted_id),
    }


@router.post("/verify-email")
async def verify_email(payload: VerifyEmailRequest):
    existing_user = await users_collection.find_one({"email": payload.email})

    if not existing_user:
        raise HTTPException(status_code=404, detail="User not found")

    if existing_user.get("is_verified") is True:
        return {"message": "Email already verified"}

    expires_at = normalize_expiry(existing_user.get("verification_expires_at"))
    if expires_at is None or expires_at < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=400,
            detail="Verification code expired. Please request a new one."
        )

    if existing_user.get("verification_code") != payload.code:
        raise HTTPException(status_code=400, detail="Invalid verification code.")

    await users_collection.update_one(
        {"_id": existing_user["_id"]},
        {
            "$set": {"is_verified": True},
            "$unset": {"verification_code": "", "verification_expires_at": ""}
        }
    )

    return {"message": "Email verified successfully"}


@router.post("/resend-verification")
async def resend_verification(payload: ResendVerificationRequest):
    existing_user = await users_collection.find_one({"email": payload.email})

    if not existing_user:
        raise HTTPException(status_code=404, detail="User not found")

    if existing_user.get("is_verified") is True:
        return {"message": "Email already verified"}

    verification_response = await send_and_store_verification_code(
        existing_user["_id"],
        existing_user["email"],
        existing_user.get("full_name", "Rayhana user"),
        success_message="Verification code sent. Please check your email.",
        fallback_message=(
            "Could not send verification email. Please try again later."
        ),
        dev_failure_message=(
            "Could not send email. Use the latest backend console code for "
            "development."
        ),
        raise_on_delivery_failure=True,
    )

    return verification_response


@router.post("/forgot-password")
async def forgot_password(payload: ForgotPasswordRequest):
    existing_user = await users_collection.find_one({"email": payload.email})

    if not existing_user:
        return {
            "message": PASSWORD_RESET_GENERIC_MESSAGE,
            "email": payload.email,
            "email_sent": True,
            "dev_code_available": False,
        }

    return await send_and_store_password_reset_code(existing_user)


@router.post("/reset-password")
async def reset_password(payload: ResetPasswordRequest):
    existing_user = await users_collection.find_one({"email": payload.email})

    if not existing_user or not existing_user.get("reset_password_code"):
        raise HTTPException(status_code=400, detail="Invalid reset code.")

    expires_at = normalize_expiry(existing_user.get("reset_password_expires_at"))
    if expires_at is None or expires_at < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=400,
            detail="Reset code expired. Please request a new one.",
        )

    if existing_user.get("reset_password_code") != payload.code:
        raise HTTPException(status_code=400, detail="Invalid reset code.")

    await users_collection.update_one(
        {"_id": existing_user["_id"]},
        {
            "$set": {"password": hash_password(payload.new_password)},
            "$unset": {
                "reset_password_code": "",
                "reset_password_expires_at": "",
            },
        },
    )

    return {"message": "Password reset successfully. Please login."}


@router.post("/test-email")
async def test_email(payload: TestEmailRequest):
    if not is_development():
        raise HTTPException(status_code=404, detail="Not found")

    try:
        email_sent = await send_test_email(to_email=payload.email)
    except Exception:
        raise HTTPException(
            status_code=503,
            detail="Could not send test email. Please check SMTP configuration and try again.",
        )

    if not email_sent:
        raise HTTPException(
            status_code=503,
            detail="SMTP is not configured. Add SMTP settings in .env first."
        )

    return {"message": "Test email sent successfully", "email_sent": True}


@router.post("/login")
async def login_user(user: UserLogin):
    existing_user = await users_collection.find_one({"email": user.email})

    if not existing_user:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    hashed_password = existing_user.get("password")
    if not hashed_password:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    password_is_valid = verify_password(user.password, hashed_password)

    if not password_is_valid:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if existing_user.get("is_verified") is False:
        raise HTTPException(
            status_code=403,
            detail="Please verify your email before logging in."
        )

    return build_auth_response(existing_user, "Login successful")


@router.post("/auth/google")
async def google_auth(payload: GoogleAuthRequest):
    # TODO: In production, verify payload.id_token server-side with Google
    # before trusting the email/profile data. Development keeps this permissive
    # so mobile integration is not blocked by OAuth client setup.
    existing_user = await users_collection.find_one({"email": payload.email})

    if existing_user:
        updates = {
            "is_verified": True,
            "auth_provider": existing_user.get("auth_provider", "google"),
        }
        if payload.google_id:
            updates["google_id"] = payload.google_id

        await users_collection.update_one(
            {"_id": existing_user["_id"]},
            {"$set": updates}
        )
        existing_user.update(updates)

        return build_auth_response(existing_user, "Google login successful")

    new_user = {
        "full_name": payload.full_name,
        "email": payload.email,
        "phone_number": None,
        "is_verified": True,
        "auth_provider": "google",
        "google_id": payload.google_id,
    }
    result = await users_collection.insert_one(new_user)
    new_user["_id"] = result.inserted_id

    return build_auth_response(new_user, "Google login successful")


@router.get("/me")
async def get_current_user(token_data: dict = Depends(verify_access_token)):
    user = await users_collection.find_one(
        {"_id": ObjectId(token_data["user_id"])}
    )

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return build_user_profile(user)


@router.put("/me")
async def update_current_user(
    payload: UserProfileUpdate,
    token_data: dict = Depends(verify_access_token),
):
    user = await users_collection.find_one(
        {"_id": ObjectId(token_data["user_id"])}
    )

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    updates = {}
    changed_fields = payload.model_fields_set

    if "full_name" in changed_fields:
        updates["full_name"] = payload.full_name
    if "phone_number" in changed_fields:
        updates["phone_number"] = payload.phone_number
    if "garden_location" in changed_fields:
        updates["garden_location"] = payload.garden_location

    if updates:
        await users_collection.update_one(
            {"_id": user["_id"]},
            {"$set": updates},
        )
        user.update(updates)

    return {
        "message": "Profile updated successfully",
        "user": build_user_profile(user),
    }

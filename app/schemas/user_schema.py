import re
from typing import Optional

from pydantic import BaseModel, EmailStr, field_validator, model_validator


class UserRegister(BaseModel):
    full_name: str
    email: EmailStr
    password: str
    phone_number: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def accept_phone_alias(cls, data):
        if isinstance(data, dict) and "phone_number" not in data and "phone" in data:
            data = data.copy()
            data["phone_number"] = data.get("phone")

        return data

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, value):
        value = value.strip()

        if len(value) < 3:
            raise ValueError("Full name must be at least 3 characters long")

        if not re.match(r"^[A-Za-z\s]+$", value):
            raise ValueError("Full name must contain letters and spaces only")

        return value

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value):
        return value.lower()

    @field_validator("password")
    @classmethod
    def validate_password(cls, value):
        if len(value) < 8:
            raise ValueError("Password must be at least 8 characters long")

        if not re.search(r"[A-Z]", value):
            raise ValueError("Password must contain at least one uppercase letter")

        if not re.search(r"[a-z]", value):
            raise ValueError("Password must contain at least one lowercase letter")

        if not re.search(r"\d", value):
            raise ValueError("Password must contain at least one number")

        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", value):
            raise ValueError("Password must contain at least one special character")

        return value

    @field_validator("phone_number")
    @classmethod
    def validate_phone_number(cls, value):
        if value is None or value == "":
            return None

        value = value.strip()

        if not re.match(r"^\+?[0-9\s-]{7,20}$", value):
            raise ValueError("Phone number must be valid")

        return value


class UserLogin(BaseModel):
    email: EmailStr
    password: str

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value):
        return value.lower()


class VerifyEmailRequest(BaseModel):
    email: EmailStr
    code: str

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value):
        return value.lower()

    @field_validator("code")
    @classmethod
    def validate_code(cls, value):
        value = value.strip()

        if not value:
            raise ValueError("Verification code is required")

        return value


class ForgotPasswordRequest(BaseModel):
    email: EmailStr

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value):
        return value.lower()


class ResetPasswordRequest(BaseModel):
    email: EmailStr
    code: str
    new_password: str

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value):
        return value.lower()

    @field_validator("code")
    @classmethod
    def validate_code(cls, value):
        value = value.strip()

        if not value:
            raise ValueError("Reset code is required")

        return value

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, value):
        if len(value) < 6:
            raise ValueError("Password must be at least 6 characters.")

        return value


class UserProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    garden_location: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def accept_phone_alias(cls, data):
        if isinstance(data, dict) and "phone_number" not in data and "phone" in data:
            data = data.copy()
            data["phone_number"] = data.get("phone")

        return data

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, value):
        if value is None:
            return None

        value = value.strip()

        if len(value) < 3:
            raise ValueError("Full name must be at least 3 characters long")

        if not re.match(r"^[A-Za-z\s]+$", value):
            raise ValueError("Full name must contain letters and spaces only")

        return value

    @field_validator("phone_number")
    @classmethod
    def validate_phone_number(cls, value):
        if value is None or value == "":
            return None

        value = value.strip()

        if not re.match(r"^\+?[0-9\s-]{7,20}$", value):
            raise ValueError("Phone number must be valid")

        return value

    @field_validator("garden_location")
    @classmethod
    def validate_garden_location(cls, value):
        if value is None:
            return None

        value = value.strip()
        return value or None


class ResendVerificationRequest(BaseModel):
    email: EmailStr

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value):
        return value.lower()


class TestEmailRequest(BaseModel):
    email: EmailStr

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value):
        return value.lower()


class GoogleAuthRequest(BaseModel):
    email: EmailStr
    full_name: str
    google_id: Optional[str] = None
    id_token: Optional[str] = None

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value):
        return value.lower()

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, value):
        value = value.strip()

        if not value:
            raise ValueError("Full name is required")

        return value

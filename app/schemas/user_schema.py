import re
from pydantic import BaseModel, EmailStr, field_validator


class UserRegister(BaseModel):
    full_name: str
    email: EmailStr
    password: str
    phone_number: str

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
        value = value.strip()

        if not re.match(r"^01[0-9]{9}$", value):
            raise ValueError("Phone number must be a valid Egyptian number with 11 digits")

        return value


class UserLogin(BaseModel):
    email: EmailStr
    password: str

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value):
        return value.lower()
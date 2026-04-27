from fastapi import APIRouter, HTTPException, Depends
from bson import ObjectId
from app.schemas.user_schema import UserRegister, UserLogin
from app.database import database
from app.utils.security import (
    hash_password,
    verify_password,
    create_access_token,
    verify_access_token
)

router = APIRouter()

users_collection = database["users"]


@router.post("/register")
async def register_user(user: UserRegister):
    existing_user = await users_collection.find_one({"email": user.email})

    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_password = hash_password(user.password)

    new_user = {
        "full_name": user.full_name,
        "email": user.email,
        "password": hashed_password,
        "phone_number": user.phone_number
    }

    result = await users_collection.insert_one(new_user)

    return {
        "message": "User registered successfully",
        "user_id": str(result.inserted_id)
    }


@router.post("/login")
async def login_user(user: UserLogin):
    existing_user = await users_collection.find_one({"email": user.email})

    if not existing_user:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    password_is_valid = verify_password(user.password, existing_user["password"])

    if not password_is_valid:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    access_token = create_access_token(
        data={
            "sub": str(existing_user["_id"]),
            "email": existing_user["email"]
        }
    )

    return {
        "message": "Login successful",
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": str(existing_user["_id"]),
            "full_name": existing_user["full_name"],
            "email": existing_user["email"],
            "phone_number": existing_user["phone_number"]
        }
    }


@router.get("/me")
async def get_current_user(token_data: dict = Depends(verify_access_token)):
    user = await users_collection.find_one(
        {"_id": ObjectId(token_data["user_id"])}
    )

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "id": str(user["_id"]),
        "full_name": user["full_name"],
        "email": user["email"],
        "phone_number": user["phone_number"]
    }
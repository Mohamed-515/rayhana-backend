import os
from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from app.services.ai_service import predict_plant_condition
from app.database import database
from app.schemas.plant_schema import PlantCreate, PlantUpdate
from app.services.recommendation_service import generate_recommendation
from app.utils.security import verify_access_token

router = APIRouter()

plants_collection = database["plants"]
analysis_collection = database["analysis_results"]

UPLOAD_FOLDER = "uploads"


def plant_serializer(plant):
    return {
        "id": str(plant["_id"]),
        "user_id": plant["user_id"],
        "plant_name": plant["plant_name"],
        "plant_type": plant["plant_type"],
        "current_status": plant["current_status"],
        "planting_date": plant.get("planting_date"),
        "notes": plant.get("notes"),
        "image_path": plant.get("image_path"),
        "ai_result": plant.get("ai_result"),
        "created_at": plant.get("created_at"),
        "updated_at": plant.get("updated_at")
    }


def analysis_serializer(analysis):
    return {
        "id": str(analysis["_id"]),
        "user_id": analysis["user_id"],
        "plant_id": analysis["plant_id"],
        "image_path": analysis["image_path"],
        "condition": analysis["condition"],
        "confidence": analysis["confidence"],
        "recommendation": analysis["recommendation"],
        "analysis_date": analysis["analysis_date"]
    }


@router.post("/plants")
async def create_plant(
    plant: PlantCreate,
    token_data: dict = Depends(verify_access_token)
):
    existing_plant = await plants_collection.find_one({
        "user_id": token_data["user_id"],
        "plant_name": plant.plant_name
    })

    if existing_plant:
        raise HTTPException(
            status_code=400,
            detail="You already have a plant with this name"
        )

    new_plant = {
        "user_id": token_data["user_id"],
        "plant_name": plant.plant_name,
        "plant_type": plant.plant_type,
        "current_status": plant.current_status,
        "planting_date": plant.planting_date,
        "notes": plant.notes,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }

    result = await plants_collection.insert_one(new_plant)
    created_plant = await plants_collection.find_one({"_id": result.inserted_id})

    return {
        "message": "Plant created successfully",
        "plant": plant_serializer(created_plant)
    }


@router.get("/plants")
async def get_my_plants(token_data: dict = Depends(verify_access_token)):
    plants_cursor = plants_collection.find({"user_id": token_data["user_id"]})
    plants = await plants_cursor.to_list(length=100)

    return {
        "count": len(plants),
        "plants": [plant_serializer(plant) for plant in plants]
    }


@router.get("/plants/{plant_id}")
async def get_plant(
    plant_id: str,
    token_data: dict = Depends(verify_access_token)
):
    if not ObjectId.is_valid(plant_id):
        raise HTTPException(status_code=400, detail="Invalid plant ID")

    plant = await plants_collection.find_one({
        "_id": ObjectId(plant_id),
        "user_id": token_data["user_id"]
    })

    if not plant:
        raise HTTPException(status_code=404, detail="Plant not found")

    return plant_serializer(plant)


@router.put("/plants/{plant_id}")
async def update_plant(
    plant_id: str,
    plant_update: PlantUpdate,
    token_data: dict = Depends(verify_access_token)
):
    if not ObjectId.is_valid(plant_id):
        raise HTTPException(status_code=400, detail="Invalid plant ID")

    existing_plant = await plants_collection.find_one({
        "_id": ObjectId(plant_id),
        "user_id": token_data["user_id"]
    })

    if not existing_plant:
        raise HTTPException(status_code=404, detail="Plant not found")

    update_data = plant_update.model_dump(exclude_unset=True)

    if not update_data:
        raise HTTPException(status_code=400, detail="No data provided for update")

    if "plant_name" in update_data:
        duplicate_plant = await plants_collection.find_one({
            "_id": {"$ne": ObjectId(plant_id)},
            "user_id": token_data["user_id"],
            "plant_name": update_data["plant_name"]
        })

        if duplicate_plant:
            raise HTTPException(
                status_code=400,
                detail="You already have a plant with this name"
            )

    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()

    await plants_collection.update_one(
        {"_id": ObjectId(plant_id), "user_id": token_data["user_id"]},
        {"$set": update_data}
    )

    updated_plant = await plants_collection.find_one({
        "_id": ObjectId(plant_id),
        "user_id": token_data["user_id"]
    })

    return {
        "message": "Plant updated successfully",
        "plant": plant_serializer(updated_plant)
    }


@router.delete("/plants/{plant_id}")
async def delete_plant(
    plant_id: str,
    token_data: dict = Depends(verify_access_token)
):
    if not ObjectId.is_valid(plant_id):
        raise HTTPException(status_code=400, detail="Invalid plant ID")

    result = await plants_collection.delete_one({
        "_id": ObjectId(plant_id),
        "user_id": token_data["user_id"]
    })

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Plant not found")

    await analysis_collection.delete_many({
        "plant_id": plant_id,
        "user_id": token_data["user_id"]
    })

    return {
        "message": "Plant deleted successfully"
    }


@router.post("/plants/{plant_id}/upload-image")
async def upload_image(
    plant_id: str,
    file: UploadFile = File(...),
    token_data: dict = Depends(verify_access_token)
):
    if not ObjectId.is_valid(plant_id):
        raise HTTPException(status_code=400, detail="Invalid plant ID")

    plant = await plants_collection.find_one({
        "_id": ObjectId(plant_id),
        "user_id": token_data["user_id"]
    })

    if not plant:
        raise HTTPException(status_code=404, detail="Plant not found")

    allowed_extensions = ["jpg", "jpeg", "png", "webp"]

    if not file.filename or "." not in file.filename:
        raise HTTPException(status_code=400, detail="Invalid image file")

    file_extension = file.filename.split(".")[-1].lower()

    if file_extension not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail="Only jpg, jpeg, png, and webp images are allowed"
        )

    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

    filename = f"{plant_id}_{int(datetime.now(timezone.utc).timestamp())}.{file_extension}"
    file_path = os.path.join(UPLOAD_FOLDER, filename)

    with open(file_path, "wb") as buffer:
        buffer.write(await file.read())

    # Temporary AI result until real model integration
    ai_prediction = predict_plant_condition(file_path)
    temporary_condition = ai_prediction["condition"]
    temporary_confidence = ai_prediction["confidence"]
    recommendation = generate_recommendation(temporary_condition)

    ai_result = {
        "condition": temporary_condition,
        "confidence": temporary_confidence,
        "recommendation": recommendation,
        "note": "Temporary AI result until the real model is integrated"
    }

    analysis_record = {
        "user_id": token_data["user_id"],
        "plant_id": plant_id,
        "image_path": file_path,
        "condition": temporary_condition,
        "confidence": temporary_confidence,
        "recommendation": recommendation,
        "analysis_date": datetime.now(timezone.utc).isoformat()
    }

    analysis_result = await analysis_collection.insert_one(analysis_record)

    await plants_collection.update_one(
        {"_id": ObjectId(plant_id), "user_id": token_data["user_id"]},
        {
            "$set": {
                "image_path": file_path,
                "ai_result": ai_result,
                "current_status": temporary_condition,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )

    updated_plant = await plants_collection.find_one({
        "_id": ObjectId(plant_id),
        "user_id": token_data["user_id"]
    })

    created_analysis = await analysis_collection.find_one({
        "_id": analysis_result.inserted_id
    })

    return {
        "message": "Image uploaded and analyzed successfully",
        "plant": plant_serializer(updated_plant),
        "analysis": analysis_serializer(created_analysis)
    }


@router.get("/plants/{plant_id}/analysis-history")
async def get_plant_analysis_history(
    plant_id: str,
    token_data: dict = Depends(verify_access_token)
):
    if not ObjectId.is_valid(plant_id):
        raise HTTPException(status_code=400, detail="Invalid plant ID")

    plant = await plants_collection.find_one({
        "_id": ObjectId(plant_id),
        "user_id": token_data["user_id"]
    })

    if not plant:
        raise HTTPException(status_code=404, detail="Plant not found")

    analysis_cursor = analysis_collection.find({
        "plant_id": plant_id,
        "user_id": token_data["user_id"]
    })

    analysis_list = await analysis_cursor.to_list(length=100)

    return {
        "count": len(analysis_list),
        "history": [analysis_serializer(analysis) for analysis in analysis_list]
    }
from typing import Optional
from pydantic import BaseModel, field_validator


class PlantCreate(BaseModel):
    plant_name: str
    plant_type: str = "Basil"
    current_status: Optional[str] = "Unknown"
    planting_date: Optional[str] = None
    notes: Optional[str] = None

    @field_validator("plant_name")
    @classmethod
    def validate_plant_name(cls, value):
        value = value.strip()

        if len(value) < 2:
            raise ValueError("Plant name must be at least 2 characters long")

        return value

    @field_validator("plant_type")
    @classmethod
    def validate_plant_type(cls, value):
        value = value.strip()

        if len(value) < 2:
            raise ValueError("Plant type must be at least 2 characters long")

        return value


class PlantUpdate(BaseModel):
    plant_name: Optional[str] = None
    plant_type: Optional[str] = None
    current_status: Optional[str] = None
    planting_date: Optional[str] = None
    notes: Optional[str] = None
from fastapi import FastAPI
from app.database import database
from app.routes.auth_routes import router as auth_router
from app.routes.plant_routes import router as plant_router

app = FastAPI(
    title="Rayhana Backend",
    description="Backend API for Rayhana Smart Basil Care System",
    version="1.0.0"
)

app.include_router(auth_router)
app.include_router(plant_router)


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
import certifi
from motor.motor_asyncio import AsyncIOMotorClient
from app.config import settings

client = AsyncIOMotorClient(
    settings.MONGO_URI,
    tls=True,
    tlsCAFile=certifi.where()
)

database = client[settings.DATABASE_NAME]
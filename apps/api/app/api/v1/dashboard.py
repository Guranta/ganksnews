from fastapi import APIRouter

from app.services import dashboard as service

router = APIRouter()


@router.get("/summary")
async def get_summary():
    return await service.get_summary()

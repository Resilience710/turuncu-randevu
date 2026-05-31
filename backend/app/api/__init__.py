"""API router'larını toplayan paket."""

from __future__ import annotations

from fastapi import APIRouter

from app.api import (
    appointments,
    auth_customer,
    auth_owner,
    auth_staff,
    availability,
    businesses,
    employees,
    me,
    sectors,
    stations,
)

api_router = APIRouter(prefix="/api")
api_router.include_router(sectors.router)
api_router.include_router(auth_customer.router)
api_router.include_router(auth_owner.router)
api_router.include_router(auth_staff.router)
api_router.include_router(me.router)
api_router.include_router(businesses.router)
api_router.include_router(employees.router)
api_router.include_router(stations.router)
api_router.include_router(availability.router)
api_router.include_router(appointments.router)


@api_router.get("/")
async def root():
    return {"message": "Turuncu Randevu API hazır", "version": "0.1.0"}

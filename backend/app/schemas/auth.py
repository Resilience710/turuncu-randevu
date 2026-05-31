"""Auth request schema'ları."""

from __future__ import annotations

import re
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

_LETTER = re.compile(r"[A-Za-zğüşıöçĞÜŞİÖÇ]")
_DIGIT = re.compile(r"\d")


def validate_strong_password(v: str) -> str:
    """Şifre kuralı: en az 8 karakter, en az bir harf ve bir rakam."""
    if len(v) < 8:
        raise ValueError("Şifre en az 8 karakter olmalı")
    if not _LETTER.search(v) or not _DIGIT.search(v):
        raise ValueError("Şifre en az bir harf ve bir rakam içermeli")
    return v


# --- Müşteri ---

class CustomerRegisterOtpRequest(BaseModel):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    phone: str
    gmail: EmailStr
    password: str = Field(min_length=8, max_length=128)
    kvkk_accepted: bool

    @field_validator("password")
    @classmethod
    def _pw(cls, v: str) -> str:
        return validate_strong_password(v)


class CustomerVerifyRegisterRequest(BaseModel):
    phone: str
    gmail: EmailStr
    otp_code: str = Field(min_length=4, max_length=8)


class CustomerLoginRequest(BaseModel):
    phone: str
    gmail: EmailStr
    password: str


# --- İşletme sahibi ---

class OwnerRegisterRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    phone: Optional[str] = None
    gmail: Optional[EmailStr] = None
    password: str = Field(min_length=8, max_length=128)
    business_name: str = Field(min_length=1, max_length=200)
    sector: str
    address: Optional[str] = None
    location: Optional[str] = None

    @field_validator("password")
    @classmethod
    def _pw(cls, v: str) -> str:
        return validate_strong_password(v)


class OwnerLoginRequest(BaseModel):
    identifier: str
    password: str


# --- Personel ---

class StaffLoginRequest(BaseModel):
    email: EmailStr
    password: str


class StaffJoinRequest(BaseModel):
    invite_code: str
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    phone: Optional[str] = None
    password: str = Field(min_length=8, max_length=128)
    title: Optional[str] = "Çalışan"

    @field_validator("password")
    @classmethod
    def _pw(cls, v: str) -> str:
        return validate_strong_password(v)

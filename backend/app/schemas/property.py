"""Pydantic schemas for property creation and representation."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class PropertyBase(BaseModel):
    """Base property attributes."""

    applicationNo: str = Field(..., validation_alias="applicationNo", serialization_alias="applicationNo")
    projectName: str = Field(..., validation_alias="projectName", serialization_alias="projectName")
    unitAddress: str = Field(..., validation_alias="unitAddress", serialization_alias="unitAddress")
    locality: str
    city: str
    pincode: str
    propertyType: str = Field(default="High-Rise Apartment", validation_alias="propertyType", serialization_alias="propertyType")

    carpetAreaSqFt: float = Field(..., validation_alias="carpetAreaSqFt", serialization_alias="carpetAreaSqFt")
    superBuiltUpAreaSqFt: float = Field(..., validation_alias="superBuiltUpAreaSqFt", serialization_alias="superBuiltUpAreaSqFt")
    floorNo: int = Field(default=1, validation_alias="floorNo", serialization_alias="floorNo")
    totalFloors: int = Field(default=1, validation_alias="totalFloors", serialization_alias="totalFloors")
    ageYears: int = Field(default=0, validation_alias="ageYears", serialization_alias="ageYears")
    roadWidthFt: float = Field(default=30.0, validation_alias="roadWidthFt", serialization_alias="roadWidthFt")

    circleRatePerSqFt: float = Field(default=0.0, validation_alias="circleRatePerSqFt", serialization_alias="circleRatePerSqFt")
    baseMarketRatePerSqFt: float = Field(default=0.0, validation_alias="baseMarketRatePerSqFt", serialization_alias="baseMarketRatePerSqFt")
    floorRiseFactor: float = Field(default=0.0, validation_alias="floorRiseFactor", serialization_alias="floorRiseFactor")
    roadWidthFactor: float = Field(default=0.0, validation_alias="roadWidthFactor", serialization_alias="roadWidthFactor")
    amenitiesPremium: float = Field(default=0.0, validation_alias="amenitiesPremium", serialization_alias="amenitiesPremium")
    structuralDepreciation: float = Field(default=0.0, validation_alias="structuralDepreciation", serialization_alias="structuralDepreciation")
    dataSource: str = Field(default="synthetic-demo", validation_alias="dataSource", serialization_alias="dataSource")

    model_config = ConfigDict(populate_by_name=True)


class PropertyCreate(PropertyBase):
    """Schema for creating a property record."""
    pass


class PropertyResponse(PropertyBase):
    """Schema for returning property details."""

    id: str
    createdAt: datetime = Field(..., validation_alias="createdAt", serialization_alias="createdAt")
    updatedAt: datetime = Field(..., validation_alias="updatedAt", serialization_alias="updatedAt")

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


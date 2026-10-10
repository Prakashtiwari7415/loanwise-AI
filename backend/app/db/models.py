"""Normalized, source-aware persistence models for LoanWise entities."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from .base import Base

JSONType = JSON().with_variant(JSONB, "postgresql")


def _id() -> str:
    return str(uuid4())


class TimestampedModel:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class User(TimestampedModel, Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    email: Mapped[str | None] = mapped_column(String(320), unique=True, index=True)
    profiles: Mapped[list[LoanProfile]] = relationship(back_populates="user")


class Lender(TimestampedModel, Base):
    __tablename__ = "lenders"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    name: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    website_url: Mapped[str | None] = mapped_column(String(2048))
    offers: Mapped[list[LoanOffer]] = relationship(back_populates="lender")


class LoanProfile(TimestampedModel, Base):
    __tablename__ = "loan_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    loan_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    vehicle_price: Mapped[float | None] = mapped_column(Numeric(14, 2))
    down_payment: Mapped[float | None] = mapped_column(Numeric(14, 2))
    monthly_income: Mapped[float | None] = mapped_column(Numeric(14, 2))
    existing_emis: Mapped[float | None] = mapped_column(Numeric(14, 2))
    user: Mapped[User | None] = relationship(back_populates="profiles")
    scenarios: Mapped[list[LoanScenario]] = relationship(back_populates="profile")
    calculations: Mapped[list[CalculationResult]] = relationship(back_populates="profile")
    documents: Mapped[list[Document]] = relationship(back_populates="profile")
    recommendations: Mapped[list[Recommendation]] = relationship(back_populates="profile")


class LoanOffer(TimestampedModel, Base):
    __tablename__ = "loan_offers"
    __table_args__ = (Index("ix_loan_offers_lender_verified", "lender_id", "verified_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    lender_id: Mapped[str] = mapped_column(ForeignKey("lenders.id", ondelete="RESTRICT"), nullable=False)
    loan_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    interest_rate: Mapped[float] = mapped_column(Numeric(7, 3), nullable=False)
    rate_type: Mapped[str] = mapped_column(String(20), nullable=False)
    tenure_months: Mapped[int] = mapped_column(Integer, nullable=False)
    processing_fee: Mapped[float | None] = mapped_column(Numeric(14, 2))
    other_charges: Mapped[float | None] = mapped_column(Numeric(14, 2))
    prepayment_terms: Mapped[str | None] = mapped_column(Text)
    foreclosure_terms: Mapped[str | None] = mapped_column(Text)
    apr: Mapped[float | None] = mapped_column(Numeric(7, 3))
    source_url: Mapped[str | None] = mapped_column(String(2048))
    source_type: Mapped[str | None] = mapped_column(String(50))
    retrieved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    lender: Mapped[Lender] = relationship(back_populates="offers")


class LoanScenario(TimestampedModel, Base):
    __tablename__ = "loan_scenarios"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    profile_id: Mapped[str | None] = mapped_column(ForeignKey("loan_profiles.id", ondelete="CASCADE"), index=True)
    name: Mapped[str | None] = mapped_column(String(120))
    inputs: Mapped[dict] = mapped_column(JSONType, nullable=False)
    profile: Mapped[LoanProfile | None] = relationship(back_populates="scenarios")


class CalculationResult(TimestampedModel, Base):
    __tablename__ = "calculation_results"
    __table_args__ = (Index("ix_calculation_results_profile_type", "profile_id", "calculation_type"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    profile_id: Mapped[str | None] = mapped_column(ForeignKey("loan_profiles.id", ondelete="SET NULL"), index=True)
    calculation_type: Mapped[str] = mapped_column(String(50), nullable=False)
    inputs: Mapped[dict] = mapped_column(JSONType, nullable=False)
    outputs: Mapped[dict] = mapped_column(JSONType, nullable=False)
    profile: Mapped[LoanProfile | None] = relationship(back_populates="calculations")


class Document(TimestampedModel, Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    profile_id: Mapped[str | None] = mapped_column(ForeignKey("loan_profiles.id", ondelete="SET NULL"), index=True)
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str | None] = mapped_column(String(64), index=True)
    processing_status: Mapped[str] = mapped_column(String(30), nullable=False, default="received")
    profile: Mapped[LoanProfile | None] = relationship(back_populates="documents")
    fields: Mapped[list[DocumentField]] = relationship(back_populates="document", cascade="all, delete-orphan")


class DocumentField(TimestampedModel, Base):
    __tablename__ = "document_fields"
    __table_args__ = (Index("ix_document_fields_document_name", "document_id", "field_name"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    field_name: Mapped[str] = mapped_column(String(100), nullable=False)
    value: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[str] = mapped_column(String(30), nullable=False)
    source_page: Mapped[int | None] = mapped_column(Integer)
    document: Mapped[Document] = relationship(back_populates="fields")


class Recommendation(TimestampedModel, Base):
    __tablename__ = "recommendations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    profile_id: Mapped[str | None] = mapped_column(ForeignKey("loan_profiles.id", ondelete="SET NULL"), index=True)
    objective: Mapped[str] = mapped_column(String(50), nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    payload: Mapped[dict] = mapped_column(JSONType, nullable=False)
    profile: Mapped[LoanProfile | None] = relationship(back_populates="recommendations")

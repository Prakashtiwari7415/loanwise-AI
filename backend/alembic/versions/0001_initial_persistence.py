"""Create initial LoanWise persistence entities.

Revision ID: 0001_initial_persistence
Revises:
Create Date: 2026-10-08
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0001_initial_persistence"
down_revision = None
branch_labels = None
depends_on = None

json_type = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_email", "users", ["email"])
    op.create_table(
        "lenders",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("website_url", sa.String(length=2048), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index("ix_lenders_name", "lenders", ["name"])
    op.create_table(
        "loan_profiles",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=True),
        sa.Column("loan_type", sa.String(length=20), nullable=False),
        sa.Column("vehicle_price", sa.Numeric(14, 2), nullable=True),
        sa.Column("down_payment", sa.Numeric(14, 2), nullable=True),
        sa.Column("monthly_income", sa.Numeric(14, 2), nullable=True),
        sa.Column("existing_emis", sa.Numeric(14, 2), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_loan_profiles_user_id", "loan_profiles", ["user_id"])
    op.create_index("ix_loan_profiles_loan_type", "loan_profiles", ["loan_type"])
    op.create_table(
        "loan_offers",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("lender_id", sa.String(length=36), nullable=False),
        sa.Column("loan_type", sa.String(length=20), nullable=False),
        sa.Column("interest_rate", sa.Numeric(7, 3), nullable=False),
        sa.Column("rate_type", sa.String(length=20), nullable=False),
        sa.Column("tenure_months", sa.Integer(), nullable=False),
        sa.Column("processing_fee", sa.Numeric(14, 2), nullable=True),
        sa.Column("other_charges", sa.Numeric(14, 2), nullable=True),
        sa.Column("prepayment_terms", sa.Text(), nullable=True),
        sa.Column("foreclosure_terms", sa.Text(), nullable=True),
        sa.Column("apr", sa.Numeric(7, 3), nullable=True),
        sa.Column("source_url", sa.String(length=2048), nullable=True),
        sa.Column("source_type", sa.String(length=50), nullable=True),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_demo", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["lender_id"], ["lenders.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_loan_offers_loan_type", "loan_offers", ["loan_type"])
    op.create_index("ix_loan_offers_lender_verified", "loan_offers", ["lender_id", "verified_at"])
    op.create_table(
        "loan_scenarios",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("profile_id", sa.String(length=36), nullable=True),
        sa.Column("name", sa.String(length=120), nullable=True),
        sa.Column("inputs", json_type, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["profile_id"], ["loan_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_loan_scenarios_profile_id", "loan_scenarios", ["profile_id"])
    op.create_table(
        "calculation_results",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("profile_id", sa.String(length=36), nullable=True),
        sa.Column("calculation_type", sa.String(length=50), nullable=False),
        sa.Column("inputs", json_type, nullable=False),
        sa.Column("outputs", json_type, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["profile_id"], ["loan_profiles.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_calculation_results_profile_id", "calculation_results", ["profile_id"])
    op.create_index("ix_calculation_results_profile_type", "calculation_results", ["profile_id", "calculation_type"])
    op.create_table(
        "documents",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("profile_id", sa.String(length=36), nullable=True),
        sa.Column("filename", sa.String(length=512), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=True),
        sa.Column("processing_status", sa.String(length=30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["profile_id"], ["loan_profiles.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_documents_profile_id", "documents", ["profile_id"])
    op.create_index("ix_documents_sha256", "documents", ["sha256"])
    op.create_table(
        "document_fields",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("document_id", sa.String(length=36), nullable=False),
        sa.Column("field_name", sa.String(length=100), nullable=False),
        sa.Column("value", sa.Text(), nullable=True),
        sa.Column("confidence", sa.String(length=30), nullable=False),
        sa.Column("source_page", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_document_fields_document_name", "document_fields", ["document_id", "field_name"])
    op.create_table(
        "recommendations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("profile_id", sa.String(length=36), nullable=True),
        sa.Column("objective", sa.String(length=50), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("payload", json_type, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["profile_id"], ["loan_profiles.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_recommendations_profile_id", "recommendations", ["profile_id"])


def downgrade() -> None:
    op.drop_index("ix_recommendations_profile_id", table_name="recommendations")
    op.drop_table("recommendations")
    op.drop_index("ix_document_fields_document_name", table_name="document_fields")
    op.drop_table("document_fields")
    op.drop_index("ix_documents_sha256", table_name="documents")
    op.drop_index("ix_documents_profile_id", table_name="documents")
    op.drop_table("documents")
    op.drop_index("ix_calculation_results_profile_type", table_name="calculation_results")
    op.drop_index("ix_calculation_results_profile_id", table_name="calculation_results")
    op.drop_table("calculation_results")
    op.drop_index("ix_loan_scenarios_profile_id", table_name="loan_scenarios")
    op.drop_table("loan_scenarios")
    op.drop_index("ix_loan_offers_lender_verified", table_name="loan_offers")
    op.drop_index("ix_loan_offers_loan_type", table_name="loan_offers")
    op.drop_table("loan_offers")
    op.drop_index("ix_loan_profiles_loan_type", table_name="loan_profiles")
    op.drop_index("ix_loan_profiles_user_id", table_name="loan_profiles")
    op.drop_table("loan_profiles")
    op.drop_index("ix_lenders_name", table_name="lenders")
    op.drop_table("lenders")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")

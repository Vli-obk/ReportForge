"""Add financial_reports and extraction_audit tables

Revision ID: d4e5f6a7b8c9
Revises: b2c3d4e5f6a7
Create Date: 2026-06-06

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "d4e5f6a7b8c9"
down_revision = "b2c3d4e5f6a7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "financial_reports",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("pdf_document_id", sa.Integer(), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("report_type", sa.String(50), nullable=True),
        sa.Column("company_name", sa.String(255), nullable=True),
        sa.Column("fiscal_year", sa.String(20), nullable=True),
        sa.Column("currency", sa.String(10), nullable=True),
        # Income Statement
        sa.Column("revenue", sa.Float(), nullable=True),
        sa.Column("gross_profit", sa.Float(), nullable=True),
        sa.Column("operating_income", sa.Float(), nullable=True),
        sa.Column("net_income", sa.Float(), nullable=True),
        sa.Column("ebitda", sa.Float(), nullable=True),
        # Balance Sheet
        sa.Column("total_assets", sa.Float(), nullable=True),
        sa.Column("total_liabilities", sa.Float(), nullable=True),
        sa.Column("shareholders_equity", sa.Float(), nullable=True),
        # Cash Flow
        sa.Column("operating_cash_flow", sa.Float(), nullable=True),
        sa.Column("investing_cash_flow", sa.Float(), nullable=True),
        sa.Column("financing_cash_flow", sa.Float(), nullable=True),
        # Metadata
        sa.Column("source_pages", postgresql.JSON(), nullable=True),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column("processing_status", sa.String(30), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "extraction_timestamp", sa.DateTime(timezone=True), nullable=True
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["pdf_document_id"], ["pdf_documents.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_financial_reports_id"), "financial_reports", ["id"], unique=False
    )
    op.create_index(
        "ix_financial_reports_user_id", "financial_reports", ["user_id"]
    )
    op.create_index(
        "ix_financial_reports_company_fy",
        "financial_reports",
        ["company_name", "fiscal_year"],
    )
    op.create_index(
        "ix_financial_reports_status",
        "financial_reports",
        ["processing_status"],
    )

    op.create_table(
        "extraction_audit",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("report_id", sa.Integer(), nullable=False),
        sa.Column("step", sa.String(50), nullable=False),
        sa.Column("model_used", sa.String(100), nullable=True),
        sa.Column("input_chars", sa.Integer(), nullable=True),
        sa.Column("chunks_processed", sa.Integer(), nullable=True),
        sa.Column("chunks_relevant", sa.Integer(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("anomalies", postgresql.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["report_id"], ["financial_reports.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_extraction_audit_id"), "extraction_audit", ["id"], unique=False
    )
    op.create_index(
        "ix_extraction_audit_report_id", "extraction_audit", ["report_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_extraction_audit_report_id", table_name="extraction_audit")
    op.drop_index(op.f("ix_extraction_audit_id"), table_name="extraction_audit")
    op.drop_table("extraction_audit")

    op.drop_index("ix_financial_reports_status", table_name="financial_reports")
    op.drop_index("ix_financial_reports_company_fy", table_name="financial_reports")
    op.drop_index("ix_financial_reports_user_id", table_name="financial_reports")
    op.drop_index(op.f("ix_financial_reports_id"), table_name="financial_reports")
    op.drop_table("financial_reports")

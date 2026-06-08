"""Add performance indexes on FK and status columns

Revision ID: b2c3d4e5f6a7
Revises: 978d81249ce9
Create Date: 2026-06-05

"""
from alembic import op

revision: str = "b2c3d4e5f6a7"
down_revision = "978d81249ce9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("ix_pdf_documents_user_id", "pdf_documents", ["user_id"])
    op.create_index("ix_pdf_documents_status", "pdf_documents", ["status"])
    op.create_index("ix_datasets_user_id", "datasets", ["user_id"])
    op.create_index("ix_datasets_pdf_document_id", "datasets", ["pdf_document_id"])
    op.create_index("ix_processing_jobs_user_id", "processing_jobs", ["user_id"])
    op.create_index("ix_processing_jobs_status", "processing_jobs", ["status"])
    op.create_index("ix_data_rows_dataset_id", "data_rows", ["dataset_id"])
    op.create_index("ix_ai_summaries_pdf_document_id", "ai_summaries", ["pdf_document_id"])
    op.create_index("ix_analytics_pdf_document_id", "analytics", ["pdf_document_id"])


def downgrade() -> None:
    op.drop_index("ix_pdf_documents_user_id", table_name="pdf_documents")
    op.drop_index("ix_pdf_documents_status", table_name="pdf_documents")
    op.drop_index("ix_datasets_user_id", table_name="datasets")
    op.drop_index("ix_datasets_pdf_document_id", table_name="datasets")
    op.drop_index("ix_processing_jobs_user_id", table_name="processing_jobs")
    op.drop_index("ix_processing_jobs_status", table_name="processing_jobs")
    op.drop_index("ix_data_rows_dataset_id", table_name="data_rows")
    op.drop_index("ix_ai_summaries_pdf_document_id", table_name="ai_summaries")
    op.drop_index("ix_analytics_pdf_document_id", table_name="analytics")

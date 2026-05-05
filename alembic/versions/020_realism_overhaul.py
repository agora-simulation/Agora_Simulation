"""Realism Overhaul: neue Persona- und Simulation-Felder.

Revision ID: 020
Revises: 019
Create Date: 2026-05-05
"""
from alembic import op
import sqlalchemy as sa

revision = "020"
down_revision = "019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- Persona: neue Realism-Felder ---
    op.add_column("personas", sa.Column("discussion_role", sa.String(30), nullable=True))
    op.add_column("personas", sa.Column("rogers_category", sa.String(20), nullable=True))
    op.add_column("personas", sa.Column("formality_level", sa.Integer(), nullable=True))
    op.add_column("personas", sa.Column("response_length_tendency", sa.String(20), nullable=True))
    op.add_column("personas", sa.Column("noise_propensity", sa.Float(), nullable=True, server_default="0.15"))
    op.add_column("personas", sa.Column("acquiescence_bias", sa.Float(), nullable=True, server_default="0.10"))
    op.add_column("personas", sa.Column("survey_fatigue_rate", sa.Float(), nullable=True, server_default="0.20"))
    op.add_column("personas", sa.Column("regional_dialect", sa.String(50), nullable=True, server_default="neutral"))
    op.add_column("personas", sa.Column("b2b_b2c_mode", sa.String(10), nullable=True, server_default="b2c"))

    # --- Simulation: neue Realism-Felder ---
    op.add_column("simulations", sa.Column("scenario_type", sa.String(30), nullable=True, server_default="b2c_product"))
    op.add_column("simulations", sa.Column("realism_config", sa.JSON(), nullable=True))

    # --- AnalysisReport: ESOMAR-Pflichtfelder ---
    op.add_column("analysis_reports", sa.Column("methodology_section", sa.Text(), nullable=True))
    op.add_column("analysis_reports", sa.Column("statistical_notes", sa.Text(), nullable=True))
    op.add_column("analysis_reports", sa.Column("nps_benchmark_comparison", sa.Text(), nullable=True))


def downgrade() -> None:
    # --- AnalysisReport ---
    op.drop_column("analysis_reports", "nps_benchmark_comparison")
    op.drop_column("analysis_reports", "statistical_notes")
    op.drop_column("analysis_reports", "methodology_section")

    # --- Simulation ---
    op.drop_column("simulations", "realism_config")
    op.drop_column("simulations", "scenario_type")

    # --- Persona ---
    op.drop_column("personas", "b2b_b2c_mode")
    op.drop_column("personas", "regional_dialect")
    op.drop_column("personas", "survey_fatigue_rate")
    op.drop_column("personas", "acquiescence_bias")
    op.drop_column("personas", "noise_propensity")
    op.drop_column("personas", "response_length_tendency")
    op.drop_column("personas", "formality_level")
    op.drop_column("personas", "rogers_category")
    op.drop_column("personas", "discussion_role")

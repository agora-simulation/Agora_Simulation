"""v1.1 Actor System Extension - 7 new tables, persona/simulation/report extensions

Revision ID: 018
Revises: 017
Create Date: 2026-05-04
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '018'
down_revision = '017'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- New tables ---

    op.create_table(
        'research_snapshots',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('owner_id', sa.String(255), nullable=True),
        sa.Column('llm_used', sa.String(100), nullable=True),
        sa.Column('passes', sa.JSON(), server_default='{}', nullable=True),
        sa.Column('status', sa.String(20), server_default='draft', nullable=True),
        sa.Column('suggested_triggers', sa.JSON(), server_default='[]', nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'platforms',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('simulation_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('character', sa.String(50), nullable=False),
        sa.Column('tonality_modifier', sa.Text(), nullable=True),
        sa.Column('reach_multiplier', sa.Float(), server_default='1.0', nullable=True),
        sa.Column('preferred_actor_types', sa.JSON(), server_default='[]', nullable=True),
        sa.Column('echo_chamber_strength', sa.Float(), server_default='0.5', nullable=True),
        sa.Column('default_engagement_rate', sa.Float(), server_default='0.3', nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['simulation_id'], ['simulations.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'templates',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('category', sa.String(50), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('owner_id', sa.String(255), nullable=True),
        sa.Column('is_default', sa.Boolean(), server_default='false', nullable=True),
        sa.Column('content', sa.JSON(), server_default='{}', nullable=True),
        sa.Column('version', sa.Integer(), server_default='1', nullable=True),
        sa.Column('parent_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['parent_id'], ['templates.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'trigger_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('simulation_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tick_day', sa.Integer(), nullable=False),
        sa.Column('event_type', sa.String(50), nullable=False),
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('affected_segments', sa.JSON(), server_default='[]', nullable=True),
        sa.Column('intensity', sa.String(20), server_default="'minor'", nullable=True),
        sa.Column('source_attribution', sa.String(500), nullable=True),
        sa.Column('was_auto_generated', sa.Boolean(), server_default='false', nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['simulation_id'], ['simulations.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'crowd_states',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('simulation_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('platform_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('tick', sa.Integer(), nullable=False),
        sa.Column('volume', sa.Integer(), server_default='0', nullable=True),
        sa.Column('sentiment', sa.Float(), server_default='0.0', nullable=True),
        sa.Column('polarization', sa.Float(), server_default='0.0', nullable=True),
        sa.Column('momentum', sa.Float(), server_default='0.0', nullable=True),
        sa.Column('representative_voices', sa.JSON(), server_default='[]', nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['simulation_id'], ['simulations.id']),
        sa.ForeignKeyConstraint(['platform_id'], ['platforms.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'actor_relationships',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('source_persona_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('target_persona_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('relation_type', sa.String(50), nullable=False),
        sa.Column('weight', sa.Float(), server_default='1.0', nullable=True),
        sa.Column('simulation_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['source_persona_id'], ['personas.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['target_persona_id'], ['personas.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['simulation_id'], ['simulations.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'validator_decisions',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('validator_persona_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('simulation_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tick_day', sa.Integer(), nullable=False),
        sa.Column('freigabe_status', sa.String(20), nullable=False),
        sa.Column('freigabe_begruendung', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['validator_persona_id'], ['personas.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['simulation_id'], ['simulations.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    # --- Alter personas table ---
    op.add_column('personas', sa.Column('actor_type', sa.String(50), nullable=False, server_default='private_person'))
    op.add_column('personas', sa.Column('subtype', sa.String(100), nullable=True))
    op.add_column('personas', sa.Column('context', sa.String(50), nullable=True))
    op.add_column('personas', sa.Column('traegerschaft', sa.String(50), nullable=True))
    op.add_column('personas', sa.Column('stance', sa.String(100), nullable=True))
    op.add_column('personas', sa.Column('activation_latency', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('personas', sa.Column('trigger_condition', sa.JSON(), nullable=True))
    op.add_column('personas', sa.Column('function_tags', sa.JSON(), server_default='[]'))
    op.add_column('personas', sa.Column('engagement_decay_rate', sa.Float(), server_default='0.05'))
    op.add_column('personas', sa.Column('profile_data', sa.JSON(), server_default='{}'))

    # --- Alter simulations table ---
    op.add_column('simulations', sa.Column('research_snapshot_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('simulations', sa.Column('stagnation_mode', sa.String(20), server_default='mild'))
    op.add_column('simulations', sa.Column('distribution_template', sa.JSON(), nullable=True))
    op.create_foreign_key('fk_simulations_research_snapshot', 'simulations', 'research_snapshots', ['research_snapshot_id'], ['id'])

    # --- Alter analysis_reports table ---
    op.add_column('analysis_reports', sa.Column('sentiment_by_actor_type', sa.Text(), nullable=True))
    op.add_column('analysis_reports', sa.Column('platform_comparison', sa.Text(), nullable=True))
    op.add_column('analysis_reports', sa.Column('validator_status', sa.Text(), nullable=True))
    op.add_column('analysis_reports', sa.Column('trigger_impact', sa.Text(), nullable=True))
    op.add_column('analysis_reports', sa.Column('stagnation_events', sa.Text(), nullable=True))
    op.add_column('analysis_reports', sa.Column('function_tag_overview', sa.Text(), nullable=True))
    op.add_column('analysis_reports', sa.Column('quota_estimates', sa.JSON(), nullable=True))

    # --- Alter posts table ---
    op.add_column('posts', sa.Column('platform_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key('fk_posts_platform', 'posts', 'platforms', ['platform_id'], ['id'])

    # --- Data migration: map old persona_type to actor_type ---
    op.execute("""
        UPDATE personas SET actor_type = CASE
            WHEN persona_type = 'organization' THEN 'company'
            WHEN persona_type = 'individual' THEN 'private_person'
            WHEN persona_type = 'institution' THEN 'collective'
            WHEN persona_type = 'politician' THEN 'private_person'
            ELSE 'private_person'
        END
        WHERE actor_type = 'private_person' AND persona_type IS NOT NULL AND persona_type != 'individual'
    """)

    # Set context for politicians
    op.execute("""
        UPDATE personas SET context = 'oeffentlich'
        WHERE persona_type = 'politician'
    """)

    # --- Seed default platforms ---
    op.execute("""
        INSERT INTO platforms (name, character, reach_multiplier, echo_chamber_strength, default_engagement_rate, is_active)
        VALUES
            ('Threadit', 'operativ', 1.0, 0.3, 0.4, true),
            ('Feedbook', 'institutionell', 1.2, 0.6, 0.25, true)
    """)


def downgrade() -> None:
    # Drop foreign keys first
    op.drop_constraint('fk_posts_platform', 'posts', type_='foreignkey')
    op.drop_constraint('fk_simulations_research_snapshot', 'simulations', type_='foreignkey')

    # Drop new columns from posts
    op.drop_column('posts', 'platform_id')

    # Drop new columns from analysis_reports
    op.drop_column('analysis_reports', 'quota_estimates')
    op.drop_column('analysis_reports', 'function_tag_overview')
    op.drop_column('analysis_reports', 'stagnation_events')
    op.drop_column('analysis_reports', 'trigger_impact')
    op.drop_column('analysis_reports', 'validator_status')
    op.drop_column('analysis_reports', 'platform_comparison')
    op.drop_column('analysis_reports', 'sentiment_by_actor_type')

    # Drop new columns from simulations
    op.drop_column('simulations', 'distribution_template')
    op.drop_column('simulations', 'stagnation_mode')
    op.drop_column('simulations', 'research_snapshot_id')

    # Drop new columns from personas
    op.drop_column('personas', 'profile_data')
    op.drop_column('personas', 'engagement_decay_rate')
    op.drop_column('personas', 'function_tags')
    op.drop_column('personas', 'trigger_condition')
    op.drop_column('personas', 'activation_latency')
    op.drop_column('personas', 'stance')
    op.drop_column('personas', 'traegerschaft')
    op.drop_column('personas', 'context')
    op.drop_column('personas', 'subtype')
    op.drop_column('personas', 'actor_type')

    # Drop new tables (reverse order of creation)
    op.drop_table('validator_decisions')
    op.drop_table('actor_relationships')
    op.drop_table('crowd_states')
    op.drop_table('trigger_events')
    op.drop_table('templates')
    op.drop_table('platforms')
    op.drop_table('research_snapshots')

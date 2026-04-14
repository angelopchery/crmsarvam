"""add transcription status fields

Revision ID: add_transcription_status
Revises: 48dc9469d5e4
Create Date: 2026-04-14 11:24:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_transcription_status'
down_revision = '48dc9469d5e4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add status column with default value
    op.add_column(
        'transcriptions',
        sa.Column(
            'status',
            sa.String(20),
            nullable=False,
            server_default='pending'
        )
    )

    # Add error_message column
    op.add_column(
        'transcriptions',
        sa.Column('error_message', sa.Text(), nullable=True)
    )

    # Add updated_at column
    op.add_column(
        'transcriptions',
        sa.Column(
            'updated_at',
            sa.DateTime(),
            nullable=False,
            server_default=sa.text('CURRENT_TIMESTAMP')
        )
    )

    # Create index on status
    op.create_index(
        'ix_transcriptions_status',
        'transcriptions',
        ['status']
    )


def downgrade() -> None:
    # Remove columns in reverse order
    op.drop_index('ix_transcriptions_status', table_name='transcriptions')
    op.drop_column('transcriptions', 'updated_at')
    op.drop_column('transcriptions', 'error_message')
    op.drop_column('transcriptions', 'status')

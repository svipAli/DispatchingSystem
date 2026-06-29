"""initial_all_tables

Revision ID: 08dbd2043e90
Revises:
Create Date: 2026-06-29 14:22:38.113009
"""
from typing import Sequence, Union
from alembic import op

revision: str = '08dbd2043e90'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    import app.modules.user.models
    import app.modules.role.models
    import app.modules.permission.models
    import app.modules.menu.models
    import app.modules.api_token.models
    import app.modules.mcp_node.models
    import app.modules.task.models
    import app.modules.billing.models
    import app.modules.recharge.models
    import app.modules.file_record.models
    import app.modules.system_config.models
    import app.modules.ai_admin.models
    from app.core.database import Base
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    from app.core.database import Base
    Base.metadata.drop_all(bind=op.get_bind())

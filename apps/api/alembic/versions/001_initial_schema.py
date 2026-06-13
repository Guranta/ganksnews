"""initial schema

Revision ID: 001_initial
Revises: None
Create Date: 2026-06-13

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "target_accounts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("platform", sa.String(50), server_default="twitter", nullable=False),
        sa.Column("username", sa.String(255), nullable=False),
        sa.Column("display_name", sa.String(255)),
        sa.Column("bio", sa.Text),
        sa.Column("avatar_url", sa.String(1024)),
        sa.Column("tags", JSONB),
        sa.Column("notes", sa.Text),
        sa.Column("status", sa.String(20), server_default="active", nullable=False),
        sa.Column("priority", sa.String(20), server_default="normal", nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("platform", "username"),
    )

    op.create_table(
        "target_account_import_batches",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("total_count", sa.Integer, server_default="0", nullable=False),
        sa.Column("created_count", sa.Integer, server_default="0", nullable=False),
        sa.Column("updated_count", sa.Integer, server_default="0", nullable=False),
        sa.Column("failed_count", sa.Integer, server_default="0", nullable=False),
        sa.Column("errors", JSONB),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "monitoring_accounts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("platform", sa.String(50), server_default="twitter", nullable=False),
        sa.Column("username", sa.String(255), nullable=False),
        sa.Column("display_name", sa.String(255)),
        sa.Column("status", sa.String(20), server_default="active", nullable=False),
        sa.Column("notes", sa.Text),
        sa.Column("last_login_check_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("platform", "username"),
    )

    op.create_table(
        "browser_profiles",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("profile_path", sa.String(1024), nullable=False),
        sa.Column("monitoring_account_id", UUID(as_uuid=True), sa.ForeignKey("monitoring_accounts.id")),
        sa.Column("status", sa.String(20), server_default="unregistered", nullable=False),
        sa.Column("provider", sa.String(50), server_default="cloakbrowser", nullable=False),
        sa.Column("last_health_check_at", sa.DateTime(timezone=True)),
        sa.Column("locked_by", sa.String(255)),
        sa.Column("locked_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("profile_path"),
    )

    op.create_table(
        "monitor_lists",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("list_type", sa.String(50), server_default="internal", nullable=False),
        sa.Column("external_id", sa.String(255)),
        sa.Column("notes", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "monitor_list_memberships",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("monitor_list_id", UUID(as_uuid=True), sa.ForeignKey("monitor_lists.id"), nullable=False),
        sa.Column("target_account_id", UUID(as_uuid=True), sa.ForeignKey("target_accounts.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("monitor_list_id", "target_account_id"),
    )

    op.create_table(
        "tweets",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("platform", sa.String(50), server_default="twitter", nullable=False),
        sa.Column("tweet_id", sa.String(255), nullable=False),
        sa.Column("author_username", sa.String(255), nullable=False),
        sa.Column("author_display_name", sa.String(255)),
        sa.Column("text", sa.Text),
        sa.Column("url", sa.String(1024)),
        sa.Column("posted_at", sa.DateTime(timezone=True)),
        sa.Column("like_count", sa.Integer),
        sa.Column("retweet_count", sa.Integer),
        sa.Column("reply_count", sa.Integer),
        sa.Column("quote_count", sa.Integer),
        sa.Column("view_count", sa.Integer),
        sa.Column("is_retweet", sa.Boolean, server_default="false", nullable=False),
        sa.Column("is_quote", sa.Boolean, server_default="false", nullable=False),
        sa.Column("raw_data", JSONB),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("platform", "tweet_id"),
    )

    op.create_index("ix_tweets_author_username", "tweets", ["author_username"])
    op.create_index("ix_tweets_posted_at", "tweets", ["posted_at"])

    op.create_table(
        "tweet_media",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tweet_id", UUID(as_uuid=True), sa.ForeignKey("tweets.id"), nullable=False),
        sa.Column("media_type", sa.String(50), nullable=False),
        sa.Column("url", sa.String(2048), nullable=False),
        sa.Column("alt_text", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "tweet_metric_snapshots",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tweet_id", UUID(as_uuid=True), sa.ForeignKey("tweets.id"), nullable=False),
        sa.Column("like_count", sa.Integer),
        sa.Column("retweet_count", sa.Integer),
        sa.Column("reply_count", sa.Integer),
        sa.Column("quote_count", sa.Integer),
        sa.Column("view_count", sa.Integer),
        sa.Column("snapshot_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "worker_heartbeats",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("worker_type", sa.String(50), nullable=False),
        sa.Column("worker_id", sa.String(255), nullable=False),
        sa.Column("status", sa.String(50), server_default="running", nullable=False),
        sa.Column("current_task", sa.Text),
        sa.Column("metadata", JSONB),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("worker_type", "worker_id"),
    )

    op.create_table(
        "crawl_jobs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("job_type", sa.String(50), nullable=False),
        sa.Column("status", sa.String(20), server_default="pending", nullable=False),
        sa.Column("target_account_id", UUID(as_uuid=True)),
        sa.Column("browser_profile_id", UUID(as_uuid=True)),
        sa.Column("monitoring_account_id", UUID(as_uuid=True)),
        sa.Column("scheduled_at", sa.DateTime(timezone=True)),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("error_message", sa.Text),
        sa.Column("retry_count", sa.Integer, server_default="0", nullable=False),
        sa.Column("metadata", JSONB),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "artifacts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("artifact_type", sa.String(50), nullable=False),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column("source_id", sa.String(255)),
        sa.Column("file_path", sa.String(1024)),
        sa.Column("content", sa.Text),
        sa.Column("error_trace", sa.Text),
        sa.Column("metadata", JSONB),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "web_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("payload", JSONB),
        sa.Column("stream_id", sa.String(255)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "notification_channels",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("channel_type", sa.String(50), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("config", JSONB),
        sa.Column("is_enabled", sa.Boolean, server_default="false", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "alert_rules",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("rule_type", sa.String(50), nullable=False),
        sa.Column("condition", JSONB),
        sa.Column("is_enabled", sa.Boolean, server_default="false", nullable=False),
        sa.Column("notification_channel_id", UUID(as_uuid=True), sa.ForeignKey("notification_channels.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "alert_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("alert_rule_id", UUID(as_uuid=True), sa.ForeignKey("alert_rules.id"), nullable=False),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("payload", JSONB),
        sa.Column("is_sent", sa.Boolean, server_default="false", nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("alert_events")
    op.drop_table("alert_rules")
    op.drop_table("notification_channels")
    op.drop_table("web_events")
    op.drop_table("artifacts")
    op.drop_table("crawl_jobs")
    op.drop_table("worker_heartbeats")
    op.drop_table("tweet_metric_snapshots")
    op.drop_table("tweet_media")
    op.drop_index("ix_tweets_posted_at")
    op.drop_index("ix_tweets_author_username")
    op.drop_table("tweets")
    op.drop_table("monitor_list_memberships")
    op.drop_table("monitor_lists")
    op.drop_table("browser_profiles")
    op.drop_table("monitoring_accounts")
    op.drop_table("target_account_import_batches")
    op.drop_table("target_accounts")

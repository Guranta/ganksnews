import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class TargetAccountStatus(str, enum.Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"


class TargetAccountPriority(str, enum.Enum):
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"


class MonitoringAccountStatus(str, enum.Enum):
    ACTIVE = "active"
    NEEDS_LOGIN = "needs_login"
    CHALLENGED = "challenged"
    SUSPENDED = "suspended"
    INACTIVE = "inactive"


class BrowserProfileStatus(str, enum.Enum):
    AVAILABLE = "available"
    IN_USE = "in_use"
    NEEDS_LOGIN = "needs_login"
    ERROR = "error"
    UNREGISTERED = "unregistered"


class CrawlJobStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ArtifactType(str, enum.Enum):
    SCREENSHOT = "screenshot"
    HTML = "html"
    RAW_PAYLOAD = "raw_payload"
    ERROR_TRACE = "error_trace"


class TargetAccount(TimestampMixin, Base):
    __tablename__ = "target_accounts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    platform: Mapped[str] = mapped_column(String(50), default="twitter")
    username: Mapped[str] = mapped_column(String(255))
    display_name: Mapped[str | None] = mapped_column(String(255))
    bio: Mapped[str | None] = mapped_column(Text)
    avatar_url: Mapped[str | None] = mapped_column(String(1024))
    tags: Mapped[list[str] | None] = mapped_column(JSONB)
    notes: Mapped[str | None] = mapped_column(Text)
    status: Mapped[TargetAccountStatus] = mapped_column(
        Enum(TargetAccountStatus, native_enum=False, length=20), default=TargetAccountStatus.ACTIVE
    )
    priority: Mapped[TargetAccountPriority] = mapped_column(
        Enum(TargetAccountPriority, native_enum=False, length=20), default=TargetAccountPriority.NORMAL
    )
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (UniqueConstraint("platform", "username"),)


class TargetAccountImportBatch(TimestampMixin, Base):
    __tablename__ = "target_account_import_batches"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    total_count: Mapped[int] = mapped_column(Integer, default=0)
    created_count: Mapped[int] = mapped_column(Integer, default=0)
    updated_count: Mapped[int] = mapped_column(Integer, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, default=0)
    errors: Mapped[list | None] = mapped_column(JSONB)


class MonitoringAccount(TimestampMixin, Base):
    __tablename__ = "monitoring_accounts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    platform: Mapped[str] = mapped_column(String(50), default="twitter")
    username: Mapped[str] = mapped_column(String(255))
    display_name: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[MonitoringAccountStatus] = mapped_column(
        Enum(MonitoringAccountStatus, native_enum=False, length=20), default=MonitoringAccountStatus.ACTIVE
    )
    notes: Mapped[str | None] = mapped_column(Text)
    last_login_check_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    browser_profiles: Mapped[list["BrowserProfile"]] = relationship(back_populates="monitoring_account")

    __table_args__ = (UniqueConstraint("platform", "username"),)


class BrowserProfile(TimestampMixin, Base):
    __tablename__ = "browser_profiles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255))
    profile_path: Mapped[str] = mapped_column(String(1024))
    monitoring_account_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("monitoring_accounts.id")
    )
    status: Mapped[BrowserProfileStatus] = mapped_column(
        Enum(BrowserProfileStatus, native_enum=False, length=20), default=BrowserProfileStatus.UNREGISTERED
    )
    provider: Mapped[str] = mapped_column(String(50), default="cloakbrowser")
    last_health_check_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    locked_by: Mapped[str | None] = mapped_column(String(255))
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    monitoring_account: Mapped["MonitoringAccount"] = relationship(back_populates="browser_profiles")

    __table_args__ = (UniqueConstraint("profile_path"),)


class MonitorList(TimestampMixin, Base):
    __tablename__ = "monitor_lists"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255))
    list_type: Mapped[str] = mapped_column(String(50), default="internal")
    external_id: Mapped[str | None] = mapped_column(String(255))
    notes: Mapped[str | None] = mapped_column(Text)

    memberships: Mapped[list["MonitorListMembership"]] = relationship(back_populates="monitor_list")


class MonitorListMembership(TimestampMixin, Base):
    __tablename__ = "monitor_list_memberships"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    monitor_list_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("monitor_lists.id"))
    target_account_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("target_accounts.id"))

    monitor_list: Mapped["MonitorList"] = relationship(back_populates="memberships")
    target_account: Mapped["TargetAccount"] = relationship()

    __table_args__ = (UniqueConstraint("monitor_list_id", "target_account_id"),)


class Tweet(TimestampMixin, Base):
    __tablename__ = "tweets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    platform: Mapped[str] = mapped_column(String(50), default="twitter")
    tweet_id: Mapped[str] = mapped_column(String(255))
    author_username: Mapped[str] = mapped_column(String(255))
    author_display_name: Mapped[str | None] = mapped_column(String(255))
    text: Mapped[str | None] = mapped_column(Text)
    url: Mapped[str | None] = mapped_column(String(1024))
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    like_count: Mapped[int | None] = mapped_column(Integer)
    retweet_count: Mapped[int | None] = mapped_column(Integer)
    reply_count: Mapped[int | None] = mapped_column(Integer)
    quote_count: Mapped[int | None] = mapped_column(Integer)
    view_count: Mapped[int | None] = mapped_column(Integer)
    is_retweet: Mapped[bool] = mapped_column(default=False)
    is_quote: Mapped[bool] = mapped_column(default=False)
    raw_data: Mapped[dict | None] = mapped_column(JSONB)

    media: Mapped[list["TweetMedia"]] = relationship(back_populates="tweet")
    metric_snapshots: Mapped[list["TweetMetricSnapshot"]] = relationship(back_populates="tweet")

    __table_args__ = (UniqueConstraint("platform", "tweet_id"),)


class TweetMedia(TimestampMixin, Base):
    __tablename__ = "tweet_media"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tweet_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tweets.id"))
    media_type: Mapped[str] = mapped_column(String(50))
    url: Mapped[str] = mapped_column(String(2048))
    alt_text: Mapped[str | None] = mapped_column(Text)

    tweet: Mapped["Tweet"] = relationship(back_populates="media")


class TweetMetricSnapshot(TimestampMixin, Base):
    __tablename__ = "tweet_metric_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tweet_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tweets.id"))
    like_count: Mapped[int | None] = mapped_column(Integer)
    retweet_count: Mapped[int | None] = mapped_column(Integer)
    reply_count: Mapped[int | None] = mapped_column(Integer)
    quote_count: Mapped[int | None] = mapped_column(Integer)
    view_count: Mapped[int | None] = mapped_column(Integer)
    snapshot_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    tweet: Mapped["Tweet"] = relationship(back_populates="metric_snapshots")


class WorkerHeartbeat(TimestampMixin, Base):
    __tablename__ = "worker_heartbeats"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    worker_type: Mapped[str] = mapped_column(String(50))
    worker_id: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(50), default="running")
    current_task: Mapped[str | None] = mapped_column(Text)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB)

    __table_args__ = (UniqueConstraint("worker_type", "worker_id"),)


class CrawlJob(TimestampMixin, Base):
    __tablename__ = "crawl_jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_type: Mapped[str] = mapped_column(String(50))
    status: Mapped[CrawlJobStatus] = mapped_column(Enum(CrawlJobStatus, native_enum=False, length=20), default=CrawlJobStatus.PENDING)
    target_account_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    browser_profile_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    monitoring_account_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_message: Mapped[str | None] = mapped_column(Text)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB)


class Artifact(TimestampMixin, Base):
    __tablename__ = "artifacts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    artifact_type: Mapped[ArtifactType] = mapped_column(Enum(ArtifactType, native_enum=False, length=20))
    source: Mapped[str] = mapped_column(String(50))
    source_id: Mapped[str | None] = mapped_column(String(255))
    file_path: Mapped[str | None] = mapped_column(String(1024))
    content: Mapped[str | None] = mapped_column(Text)
    error_trace: Mapped[str | None] = mapped_column(Text)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB)


class WebEvent(TimestampMixin, Base):
    __tablename__ = "web_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type: Mapped[str] = mapped_column(String(50))
    payload: Mapped[dict | None] = mapped_column(JSONB)
    stream_id: Mapped[str | None] = mapped_column(String(255))


class NotificationChannel(TimestampMixin, Base):
    __tablename__ = "notification_channels"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    channel_type: Mapped[str] = mapped_column(String(50))
    name: Mapped[str] = mapped_column(String(255))
    config: Mapped[dict | None] = mapped_column(JSONB)
    is_enabled: Mapped[bool] = mapped_column(default=False)


class AlertRule(TimestampMixin, Base):
    __tablename__ = "alert_rules"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255))
    rule_type: Mapped[str] = mapped_column(String(50))
    condition: Mapped[dict | None] = mapped_column(JSONB)
    is_enabled: Mapped[bool] = mapped_column(default=False)
    notification_channel_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("notification_channels.id")
    )


class AlertEvent(TimestampMixin, Base):
    __tablename__ = "alert_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    alert_rule_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("alert_rules.id"))
    event_type: Mapped[str] = mapped_column(String(50))
    payload: Mapped[dict | None] = mapped_column(JSONB)
    is_sent: Mapped[bool] = mapped_column(default=False)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

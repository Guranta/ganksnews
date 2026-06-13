from app.core.config import settings

WEB_EVENTS = "web_events"
WORKER_EVENTS = "worker_events"
ACCOUNT_EVENTS = "account_events"
CRAWL_JOBS = "crawl_jobs"
RAW_TWEETS = "raw_tweets"
DEAD_LETTER = "dead_letter"

ALL_STREAMS = [WEB_EVENTS, WORKER_EVENTS, ACCOUNT_EVENTS, CRAWL_JOBS, RAW_TWEETS, DEAD_LETTER]

CG_API = "cg-api"
CG_SCHEDULER = "cg-scheduler"
CG_LISTENER = "cg-listener"
CG_DETAIL = "cg-detail"
CG_HEALTH = "cg-health"

EVT_TEST = "test"
EVT_WORKER_STATUS = "worker.status"
EVT_ACCOUNT_STATUS = "account.status"
EVT_CRAWL_JOB = "crawl.job"
EVT_TWEET_NEW = "tweet.new"
EVT_HEARTBEAT = "heartbeat"
EVT_LOGIN_SESSION_CREATED = "login_session.created"
EVT_LOGIN_SESSION_RUNNING = "login_session.running"
EVT_LOGIN_SESSION_COMPLETED = "login_session.completed"
EVT_LOGIN_SESSION_CANCELLED = "login_session.cancelled"
EVT_PROFILE_HEALTH_CHECK_STARTED = "profile.health_check_started"
EVT_PROFILE_AVAILABLE = "profile.available"
EVT_PROFILE_NEEDS_LOGIN = "profile.needs_login"
EVT_PROFILE_CHALLENGED = "profile.challenged"
EVT_PROFILE_ERROR = "profile.error"


def stream_key(name: str) -> str:
    return f"{settings.STREAM_PREFIX}:{name}"

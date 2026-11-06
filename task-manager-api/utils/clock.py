from datetime import datetime, timezone


def utcnow():
    """Current UTC time as a naive datetime, compatible with the existing DateTime columns."""
    return datetime.now(timezone.utc).replace(tzinfo=None)

def completion_rate(completed, total):
    """Percentage of completed items, rounded to 2 decimals (0 when there are no items)."""
    return round((completed / total) * 100, 2) if total > 0 else 0

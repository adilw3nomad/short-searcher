from datetime import date


def engagement_rate(views: int, likes: int, comments: int) -> float:
    if views <= 0:
        return 0.0
    return (likes + comments) / views


def lifetime_velocity(views: int, published_at: date, now: date | None = None) -> float:
    now = now or date.today()
    age_days = (now - published_at).days
    if age_days <= 0:
        return 0.0
    return views / age_days


def recent_velocity(curr_views: int, prev_views: int | None, hours: float) -> float:
    if prev_views is None or hours <= 0:
        return 0.0
    return (curr_views - prev_views) / hours


def composite_scores(rows: list[tuple[float, float, float]]) -> list[float]:
    if not rows:
        return []
    weights = (0.5, 0.3, 0.2)  # recent_velocity, engagement, lifetime_velocity

    def normalize(values: list[float]) -> list[float]:
        lo, hi = min(values), max(values)
        span = hi - lo
        if span == 0:
            return [0.0] * len(values)
        return [(x - lo) / span for x in values]

    cols = [normalize([r[i] for r in rows]) for i in range(3)]
    return [
        sum(weights[i] * cols[i][j] for i in range(3))
        for j in range(len(rows))
    ]

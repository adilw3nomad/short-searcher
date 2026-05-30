from datetime import date
from short_searcher import metrics


def test_engagement_rate():
    assert metrics.engagement_rate(1000, 80, 20) == 0.1


def test_engagement_rate_zero_views_is_zero():
    assert metrics.engagement_rate(0, 5, 5) == 0.0


def test_lifetime_velocity():
    # 10000 views, published 10 days before `now` -> 1000 views/day
    v = metrics.lifetime_velocity(10000, date(2026, 5, 20), now=date(2026, 5, 30))
    assert v == 1000.0


def test_lifetime_velocity_same_day_is_zero():
    v = metrics.lifetime_velocity(10000, date(2026, 5, 30), now=date(2026, 5, 30))
    assert v == 0.0


def test_recent_velocity():
    # +1200 views over 24h -> 50 views/hour
    assert metrics.recent_velocity(5200, 4000, 24.0) == 50.0


def test_recent_velocity_no_prior_is_zero():
    assert metrics.recent_velocity(5200, None, 24.0) == 0.0


def test_recent_velocity_negative_clamped_to_zero():
    # a view-count dip should not produce negative growth
    assert metrics.recent_velocity(3000, 4000, 24.0) == 0.0


def test_composite_scores_normalizes_and_weights():
    rows = [
        (100.0, 0.10, 1000.0),   # best on every axis -> 1.0
        (0.0, 0.0, 0.0),         # worst on every axis -> 0.0
        (50.0, 0.05, 500.0),     # middle -> 0.5
    ]
    scores = metrics.composite_scores(rows)
    assert scores[0] == 1.0
    assert scores[1] == 0.0
    assert abs(scores[2] - 0.5) < 1e-9


def test_composite_scores_flat_dimension_contributes_zero():
    rows = [(0.0, 0.1, 10.0), (0.0, 0.1, 10.0)]
    assert metrics.composite_scores(rows) == [0.0, 0.0]

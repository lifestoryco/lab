"""Linter — buzzwords, kill-words, density, metric-truth, numeric normalizer."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from careerops.linter import (
    extract_metrics, MetricToken, metric_matches_outcomes,
    detect_kill_words, detect_soft_kills, density_flag_count,
    buzzword_density_pct, lint_bullet, lint_resume, reload_corpus,
)


# ── Numeric normalizer + metric extraction ─────────────────────────────

def test_extract_currency_with_suffix():
    metrics = extract_metrics("Closed $27M Series A.")
    assert any(m.unit == "USD" and m.value == 27_000_000 for m in metrics)


def test_extract_currency_with_million_word():
    metrics = extract_metrics("Closed $27 million Series A.")
    assert any(m.unit == "USD" and m.value == 27_000_000 for m in metrics)


def test_currency_with_million_word_does_not_double_count():
    """$27 million should NOT also yield a stray $27 token."""
    metrics = extract_metrics("Closed $27 million Series A.")
    usd_metrics = [m for m in metrics if m.unit == "USD"]
    assert len(usd_metrics) == 1
    assert usd_metrics[0].value == 27_000_000


def test_extract_currency_range_emits_both_endpoints():
    metrics = extract_metrics("Grew ARR from $6M to $13M.")
    usd_values = sorted(m.value for m in metrics if m.unit == "USD")
    assert usd_values == [6_000_000, 13_000_000]


def test_extract_percent():
    metrics = extract_metrics("Improved FCR by 40%.")
    assert any(m.unit == "pct" and m.value == 40 for m in metrics)


def test_extract_multiple():
    metrics = extract_metrics("Reduced latency 4.2x.")
    assert any(m.unit == "x" and m.value == 4.2 for m in metrics)


def test_extract_count_with_unit():
    metrics = extract_metrics("Spanning 187 countries and 1,000+ pages.")
    units = {m.unit for m in metrics}
    assert "countries" in units
    assert "pages" in units


def test_extract_time_delta_word_form():
    metrics = extract_metrics("six weeks ahead of schedule")
    assert any(m.unit == "weeks" and m.value == 6 for m in metrics)


def test_metric_matches_outcomes_currency():
    metric = MetricToken(unit="USD", value=1_000_000, display="$1M")
    outcomes = [{"value_numeric": 1_000_000, "unit": "USD"}]
    assert metric_matches_outcomes(metric, outcomes)


def test_metric_does_not_match_inflated():
    metric = MetricToken(unit="USD", value=5_000_000, display="$5M")
    outcomes = [{"value_numeric": 1_000_000, "unit": "USD"}]
    assert not metric_matches_outcomes(metric, outcomes)


def test_metric_singular_plural_unit_compatibility():
    metric = MetricToken(unit="months", value=12, display="12 months")
    outcomes = [{"value_numeric": 12, "unit": "month"}]  # singular
    assert metric_matches_outcomes(metric, outcomes)


# ── Buzzword + kill-word detection ─────────────────────────────────────

def test_kill_word_responsible_for():
    hits = detect_kill_words("Was responsible for the Cox program.")
    assert "responsible for" in hits


def test_kill_word_helped_with():
    hits = detect_kill_words("I helped with deployment.")
    assert "helped with" in hits


def test_kill_word_team_player():
    hits = detect_kill_words("Strong team player and self-starter.")
    assert "team player" in hits
    assert "self-starter" in hits


def test_no_kill_words_in_clean_bullet():
    hits = detect_kill_words("Drove Cox program to $1M Y1 revenue.")
    assert hits == []


def test_density_flag_counts_strong_verbs():
    n, hits = density_flag_count(
        "Drove transformation. Led innovation. Owned outcomes. Built solutions."
    )
    assert n >= 4
    assert "drove" in hits


def test_density_pct_calculation():
    pct = buzzword_density_pct("Drove led owned built drove led owned built drove led")
    # 9 hits / 10 tokens = 90%
    assert pct >= 80


def test_density_low_on_clean_bullet():
    pct = buzzword_density_pct("Coordinated cross-functional teams across multiple time zones.")
    assert pct < 5  # only "led" if any density-flag is hit; calmer prose


# ── lint_bullet integration ────────────────────────────────────────────

def test_lint_bullet_clean_passes():
    res = lint_bullet(
        "Drove Cox program to $1M Y1 revenue 12 months ahead of schedule.",
        outcome_rows=[
            {"value_numeric": 1_000_000, "unit": "USD"},
            {"value_numeric": 12, "unit": "months"},
        ],
    )
    assert res.passed
    assert not res.kill_word_hits
    assert not res.unverified_metrics


def test_lint_bullet_inflated_metric_fails():
    res = lint_bullet(
        "Drove Cox program to $5M Y1 revenue.",
        outcome_rows=[{"value_numeric": 1_000_000, "unit": "USD"}],
    )
    assert not res.passed
    assert any(m.value == 5_000_000 for m in res.unverified_metrics)


def test_lint_bullet_kill_word_fails():
    res = lint_bullet(
        "Was responsible for the Cox program.",
        outcome_rows=[],
    )
    assert not res.passed
    assert "responsible for" in res.kill_word_hits


def test_lint_bullet_linter_override_allows_soft_kill():
    # 'leveraged' is a soft-kill in the corpus.
    res_no_override = lint_bullet(
        "Leveraged cross-functional teams.",
        outcome_rows=[],
    )
    assert "leveraged" in res_no_override.soft_kill_hits

    res_with_override = lint_bullet(
        "Leveraged cross-functional teams.",
        outcome_rows=[],
        linter_override="leveraged",
    )
    assert "leveraged" not in res_with_override.soft_kill_hits


def test_lint_bullet_skips_metric_check_when_outcomes_none():
    res = lint_bullet("Drove Cox to $1M Y1.", outcome_rows=None)
    assert not res.unverified_metrics  # no check ran


# ── lint_resume aggregate ─────────────────────────────────────────────

def test_lint_resume_aggregates_density():
    bullets = ["Drove led owned built drove led owned built drove led"] * 2
    res = lint_resume(bullets)
    assert not res.passed
    assert res.density_pct > 6.0


def test_lint_resume_clean_passes():
    bullets = [
        "Drove Cox program to $1M Y1 revenue 12 months ahead of schedule.",
        "Coordinated 15+ network deployments serving as RF liaison.",
    ]
    outcomes = [
        [{"value_numeric": 1_000_000, "unit": "USD"}, {"value_numeric": 12, "unit": "months"}],
        [{"value_numeric": 15, "unit": "deployments"}],
    ]
    res = lint_resume(bullets, outcome_rows_per_bullet=outcomes)
    assert res.passed


def test_corpus_has_required_kill_words():
    corpus = reload_corpus()
    kill_words = [w.lower() for w in corpus["kill_words"]]
    for required in (
        "responsible for", "helped with", "team player",
        "results-driven", "self-starter", "world-class",
    ):
        assert required in kill_words, f"missing kill-word: {required}"


def test_corpus_thresholds_present():
    corpus = reload_corpus()
    assert "thresholds" in corpus
    assert corpus["thresholds"]["density_pct_max"] == 6.0

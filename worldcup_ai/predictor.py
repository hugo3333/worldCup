from __future__ import annotations

import math
from dataclasses import asdict
from typing import Any

from .fetchers import venue_profile
from .models import Prediction, Team, Venue


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def team_context(team: Team) -> dict[str, float]:
    return {
        "attack": team.attack / 100.0,
        "defense": team.defense / 100.0,
        "depth": team.depth / 100.0,
        "fitness": team.fitness / 100.0,
        "geo": team.geo / 100.0,
    }


def venue_penalty(team: Team, venue: Venue) -> float:
    altitude_fit = 0.96 if team.region == "北美" else 0.91
    heat_fit = 0.95 if team.region in {"南美", "非洲"} else 0.90
    long_travel = 1.0 if team.travel == "低" else 0.96 if team.travel == "中等" else 0.92
    venue_stress = 1 - ((venue.altitude * (1 - team.geo / 100)) + (venue.heat * 0.15) + (venue.travel * 0.2)) / 260
    return clamp(venue_stress * altitude_fit * heat_fit * long_travel, 0.82, 1.08)


def geo_pressure_parts(team: Team, venue: Venue) -> dict[str, float]:
    altitude_pressure = clamp(venue.altitude * (1 - team.geo / 100), 0, 100)
    heat_factor = 0.62 if team.region in {"南美", "非洲"} else 0.82 if team.region in {"欧洲", "北美"} else 0.74
    heat_pressure = clamp(venue.heat * heat_factor, 0, 100)
    travel_factor = 0.6 if team.travel == "低" else 0.85 if team.travel == "中等" else 1.05
    travel_pressure = clamp(venue.travel * travel_factor, 0, 100)
    total = (altitude_pressure + heat_pressure + travel_pressure) / 3
    return {
        "altitude": round(altitude_pressure, 1),
        "heat": round(heat_pressure, 1),
        "travel": round(travel_pressure, 1),
        "total": round(total, 1),
    }


def factorial(n: int) -> int:
    result = 1
    for i in range(2, n + 1):
        result *= i
    return result


def poisson(lmbda: float, k: int) -> float:
    return (math.exp(-lmbda) * (lmbda**k)) / factorial(k)


def top_score_lines(home_lambda: float, away_lambda: float) -> list[dict[str, Any]]:
    scores = []
    for home_goals in range(5):
        for away_goals in range(5):
            probability = poisson(home_lambda, home_goals) * poisson(away_lambda, away_goals)
            scores.append({"h": home_goals, "a": away_goals, "p": probability})
    scores.sort(key=lambda item: item["p"], reverse=True)
    return scores[:6]


def predict_match(home: Team, away: Team, venue_name: str, min_confidence: int = 62) -> Prediction:
    venue = venue_profile(venue_name)
    home_ctx = team_context(home)
    away_ctx = team_context(away)
    venue_factor_home = venue_penalty(home, venue)
    venue_factor_away = venue_penalty(away, venue)
    home_geo = geo_pressure_parts(home, venue)
    away_geo = geo_pressure_parts(away, venue)

    quality_gap = (
        home_ctx["attack"] + home_ctx["depth"] + home_ctx["fitness"] * 0.7 + home_ctx["geo"] * 0.35
        - (away_ctx["defense"] + away_ctx["depth"] * 0.55 + away_ctx["fitness"] * 0.5 + away_ctx["geo"] * 0.2)
    )
    counter_gap = (
        away_ctx["attack"] + away_ctx["depth"] + away_ctx["fitness"] * 0.7 + away_ctx["geo"] * 0.35
        - (home_ctx["defense"] + home_ctx["depth"] * 0.55 + home_ctx["fitness"] * 0.5 + home_ctx["geo"] * 0.2)
    )

    home_lambda = clamp(
        0.55 + home_ctx["attack"] * 1.35 + home_ctx["depth"] * 0.45 + home_ctx["fitness"] * 0.35 + home_ctx["geo"] * 0.3 + quality_gap * 0.012,
        0.35,
        2.95,
    ) * venue_factor_home
    away_lambda = clamp(
        0.5 + away_ctx["attack"] * 1.28 + away_ctx["depth"] * 0.42 + away_ctx["fitness"] * 0.34 + away_ctx["geo"] * 0.25 + counter_gap * 0.01,
        0.3,
        2.75,
    ) * venue_factor_away

    top_scores = top_score_lines(home_lambda, away_lambda)
    best = top_scores[0]
    confidence = clamp(
        51 + abs(home_lambda - away_lambda) * 12 + (home_ctx["depth"] - away_ctx["depth"]) * 8 + (home_ctx["fitness"] - away_ctx["fitness"]) * 6,
        48,
        79,
    )
    geo_pressure = clamp((home_geo["total"] + away_geo["total"]) / 2 + (venue.altitude > 50) * 3, 20, 92)
    risk_label = (
        "优势较清晰，适合谨慎试探"
        if confidence >= 70
        else "有轻微优势，仍需控制仓位"
        if confidence >= 62
        else "优势边缘，只适合观察或极小仓位"
        if confidence >= min_confidence
        else "不满足出手门槛，建议回避"
    )

    return Prediction(
        home_goals=home_lambda,
        away_goals=away_lambda,
        best_score=f"{best['h']} - {best['a']}",
        confidence=confidence,
        geo_pressure=geo_pressure,
        geo_breakdown={
            "home": home_geo,
            "away": away_geo,
            "venue": {"altitude": venue.altitude, "heat": venue.heat, "travel": venue.travel},
        },
        top_scores=top_scores,
        risk_label=risk_label,
    )


def prediction_to_context(prediction: Prediction) -> dict[str, Any]:
    return prediction.to_dict()

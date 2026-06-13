from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class Player:
    name: str
    position: str = ""
    age: int | None = None
    caps: int | None = None
    goals: int | None = None
    club: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Team:
    name: str
    region: str
    attack: int
    defense: int
    depth: int
    fitness: int
    geo: int
    climate: str
    travel: str
    style: str
    outlook: str
    players: list[Player] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["players"] = [player.to_dict() for player in self.players]
        return payload


@dataclass
class Venue:
    name: str
    altitude: int
    heat: int
    travel: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Fixture:
    home: str
    away: str
    group: str
    venue: str
    date: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Prediction:
    home_goals: float
    away_goals: float
    best_score: str
    confidence: float
    geo_pressure: float
    geo_breakdown: dict[str, Any]
    top_scores: list[dict[str, Any]]
    risk_label: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class LiveSnapshot:
    status: str
    message: str
    fetched_at: str
    sources: list[str]
    fixtures: list[Fixture] = field(default_factory=list)
    teams: list[Team] = field(default_factory=list)
    venues: list[Venue] = field(default_factory=list)
    selected_fixture: Fixture | None = None
    prediction: Prediction | None = None
    fixture_views: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "message": self.message,
            "fetched_at": self.fetched_at,
            "sources": self.sources,
            "fixtures": [fixture.to_dict() for fixture in self.fixtures],
            "teams": [team.to_dict() for team in self.teams],
            "venues": [venue.to_dict() for venue in self.venues],
            "selected_fixture": self.selected_fixture.to_dict() if self.selected_fixture else None,
            "prediction": self.prediction.to_dict() if self.prediction else None,
            "fixture_views": self.fixture_views,
        }

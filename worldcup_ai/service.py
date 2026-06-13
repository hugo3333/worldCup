from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timedelta
from typing import Any

from .fetchers import (
    html_text,
    hydrate_teams,
    live_data_sources,
    now_iso,
    fifa_official_page_html,
    parse_squads,
    parse_today_fixtures,
    schedule_article_html,
    select_fixture,
    venue_profile,
    translate_team_name,
    wikipedia_page_html,
)
from .models import Fixture, LiveSnapshot, Team, Venue
from .predictor import predict_match


class WorldCupService:
    def __init__(self, ttl_minutes: int = 120) -> None:
        self.ttl = timedelta(minutes=ttl_minutes)
        self._cache: LiveSnapshot | None = None
        self._cache_time: datetime | None = None

    def _stale(self) -> bool:
        return not self._cache_time or datetime.utcnow() - self._cache_time > self.ttl

    def refresh(self, force: bool = False) -> LiveSnapshot:
        if not force and self._cache and not self._stale():
            return self._cache

        try:
            tournament_html = wikipedia_page_html("2026_FIFA_World_Cup")
            squads_html = wikipedia_page_html("2026_FIFA_World_Cup_squads")
            official_html = fifa_official_page_html()
            fixtures = parse_today_fixtures(
                html_text(schedule_article_html()),
                html_text(official_html),
                html_text(tournament_html),
            )
            squads = parse_squads(squads_html)
            teams = hydrate_teams(squads)
            team_map = {team.name: team for team in teams}
            venues: list[Venue] = []
            selected_fixture = select_fixture(teams, fixtures)
            if selected_fixture:
                venues = [venue_profile(selected_fixture.venue)]
            prediction = None
            fixture_views: list[dict[str, Any]] = []
            for fixture in fixtures:
                home_name = translate_team_name(fixture.home)
                away_name = translate_team_name(fixture.away)
                home_team = team_map.get(home_name)
                away_team = team_map.get(away_name)
                venue_name = fixture.venue
                view_prediction = None
                if home_team and away_team:
                    view_prediction = predict_match(home_team, away_team, venue_name).to_dict()
                fixture_views.append(
                    {
                        "fixture": {
                            "home": home_name,
                            "away": away_name,
                            "group": fixture.group,
                            "venue": venue_name,
                            "date": fixture.date,
                        },
                        "home_team": home_team.to_dict() if home_team else None,
                        "away_team": away_team.to_dict() if away_team else None,
                        "prediction": view_prediction,
                    }
                )
                if selected_fixture and home_name == selected_fixture.home and away_name == selected_fixture.away:
                    prediction = predict_match(home_team, away_team, venue_name) if home_team and away_team else None

            snapshot = LiveSnapshot(
                status="live",
                message="实时公开数据已加载。",
                fetched_at=now_iso(),
                sources=live_data_sources(),
                fixtures=fixtures,
                teams=teams,
                venues=venues,
                selected_fixture=selected_fixture,
                prediction=prediction,
                fixture_views=fixture_views,
            )
            self._cache = snapshot
            self._cache_time = datetime.utcnow()
            return snapshot
        except Exception:
            if self._cache:
                cached = self._cache
                cached.status = "cached"
                cached.message = "实时公开源暂时不可用，返回最近一次成功缓存。"
                return cached
            snapshot = LiveSnapshot(
                status="unavailable",
                message="实时公开源暂时不可用。",
                fetched_at=now_iso(),
                sources=live_data_sources(),
            )
            self._cache = snapshot
            self._cache_time = datetime.utcnow()
            return snapshot

    def latest(self) -> LiveSnapshot:
        return self.refresh()

    def current_context(self) -> dict[str, Any]:
        return self.latest().to_dict()

    def ai_context(self) -> dict[str, Any]:
        snapshot = self.latest()
        payload = snapshot.to_dict()
        payload["prompt"] = self.prompt_bundle(snapshot)
        return payload

    def predict(self, home_name: str, away_name: str, venue_name: str) -> dict[str, Any]:
        snapshot = self.latest()
        team_map = {team.name: team for team in snapshot.teams}
        home = team_map.get(home_name)
        away = team_map.get(away_name)
        if not home or not away:
            return {"status": "unavailable", "message": "球队未在公开名单中找到。"}
        return {
            "status": snapshot.status,
            "fixture": {"home": home.name, "away": away.name, "venue": venue_name},
            "prediction": predict_match(home, away, venue_name).to_dict(),
            "sources": snapshot.sources,
            "fetched_at": now_iso(),
        }

    def prompt_bundle(self, snapshot: LiveSnapshot) -> str:
        data = snapshot.to_dict()
        return (
            "你是一个足球比分分析助手。"
            "只基于下面的公开数据输出概率分析，不要编造名单或赛程。"
            f"数据: {data}"
        )


service = WorldCupService()

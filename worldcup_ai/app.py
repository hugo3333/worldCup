from __future__ import annotations

import os
import json
from html import escape
from pathlib import Path

from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

from .service import service

STATIC_DIR = Path(__file__).resolve().parent / "static"

STATUS_LABELS = {
    "live": "已更新",
    "cached": "缓存中",
    "unavailable": "不可用",
}


def clamp_percent(value: int | float | None) -> int:
    if value is None:
        return 0
    return max(0, min(100, int(value)))


def metric_bar(label: str, value: int | float | None, tone: str = "accent") -> str:
    width = clamp_percent(value)
    return (
        f"<div class='metric-row'>"
        f"<div class='metric-head'><span>{escape(label)}</span><strong>{width}</strong></div>"
        f"<div class='metric-track'><span class='{tone}' style='width:{width}%'></span></div>"
        f"</div>"
    )


def render_team_card(team: dict[str, object] | None, tone: str, title: str) -> str:
    if not team:
        return (
            f"<article class='team-card {tone}'>"
            f"<div class='card-title'>{escape(title)}</div>"
            f"<div class='empty-card'>暂无球队数据</div>"
            f"</article>"
        )

    players = team.get("players") or []
    monogram = str(team.get("name", "--"))[:1]
    return (
        f"<article class='team-card {tone}'>"
        f"<div class='team-card-head'>"
        f"<div class='team-identity'>"
        f"<div class='team-monogram'>{escape(monogram)}</div>"
        f"<div>"
        f"<div class='card-title'>{escape(str(team.get('name', '')))}</div>"
        f"<div class='team-subtitle'>{escape(str(team.get('region', '')))}</div>"
        f"</div>"
        f"</div>"
        f"<div class='team-badge'>{escape(str(team.get('travel', '')))}</div>"
        f"</div>"
        f"<div class='metric-stack'>"
        f"{metric_bar('攻击', team.get('attack'))}"
        f"{metric_bar('防守', team.get('defense'))}"
        f"{metric_bar('深度', team.get('depth'))}"
        f"{metric_bar('体能', team.get('fitness'))}"
        f"</div>"
        f"<div class='team-mini'>"
        f"<span>地理 {escape(str(team.get('geo', '--')))}</span>"
        f"<span>气候 {escape(str(team.get('climate', '--')))}</span>"
        f"<span>风格 {escape(str(team.get('style', '--')))}</span>"
        f"</div>"
        f"<div class='team-outlook'>{escape(str(team.get('outlook', '')))}</div>"
        f"<div class='team-footer'>球员 {len(players)} 人</div>"
        f"</article>"
    )


def render_player_list(team: dict[str, object] | None, tone: str, title: str) -> str:
    if not team:
        empty = "<div class='empty-card'>暂无球员数据</div>"
        return (
            f"<article class='player-card {tone}'>"
            f"<div class='card-title'>{escape(title)}</div>"
            f"{empty}"
            f"</article>"
        )

    players = team.get("players") or []
    players = sorted(
        players,
        key=lambda item: ((item.get("goals") or 0), (item.get("caps") or 0), -(item.get("age") or 0)),
        reverse=True,
    )[:5]
    rows = []
    for player in players:
        rows.append(
            f"<div class='player-row'>"
            f"<div>"
            f"<strong>{escape(str(player.get('name', '')))}</strong>"
            f"<span>{escape(str(player.get('club', '')))}</span>"
            f"</div>"
            f"<div class='player-stats'>"
            f"<em>{escape(str(player.get('position', '--')))}</em>"
            f"<b>{player.get('caps') or 0} 场 · {player.get('goals') or 0} 球</b>"
            f"</div>"
            f"</div>"
        )
    empty = "<div class='empty-card'>暂无球员数据</div>"
    return (
        f"<article class='player-card {tone}'>"
        f"<div class='player-card-head'>"
        f"<div>"
        f"<div class='card-title'>{escape(str(team.get('name', '')))} 球员分析</div>"
        f"<div class='team-subtitle'>按进球、出场与经验排序</div>"
        f"</div>"
        f"</div>"
        f"<div class='player-list'>{''.join(rows) if rows else empty}</div>"
        f"</article>"
    )


def render_compare_card(prediction: dict[str, object], selected_fixture: dict[str, object] | None) -> str:
    top_scores = prediction.get("top_scores") or []
    geo = prediction.get("geo_breakdown") or {}
    home_geo = geo.get("home") or {}
    away_geo = geo.get("away") or {}
    score_rows = []
    for item in top_scores[:3]:
        score_rows.append(
            f"<li><span>{item.get('h')}-{item.get('a')}</span><b>{round((item.get('p') or 0) * 100, 1)}%</b></li>"
        )
    score_html = "".join(score_rows) or "<li><span>暂无</span><b>--</b></li>"
    fixture_title = "--"
    if selected_fixture:
        fixture_title = f"{selected_fixture.get('home')} 对 {selected_fixture.get('away')}"
    return (
        "<article class='compare-card'>"
        f"<div class='card-title'>对比结论</div>"
        f"<div class='compare-fixture'>{escape(fixture_title)}</div>"
        f"<div class='compare-grid'>"
        f"<div><span>最接近比分</span><strong>{escape(str(prediction.get('best_score', '--')))}</strong></div>"
        f"<div><span>置信度</span><strong>{escape(str(prediction.get('confidence', '--')))}%</strong></div>"
        f"<div><span>风险判断</span><strong>{escape(str(prediction.get('risk_label', '--')))}</strong></div>"
        f"<div><span>地理压力</span><strong>{escape(str(prediction.get('geo_pressure', '--')))}</strong></div>"
        f"</div>"
        f"<div class='geo-detail'>"
        f"<div><span>主队海拔 / 炎热 / 旅途</span><strong>{home_geo.get('altitude', '--')} / {home_geo.get('heat', '--')} / {home_geo.get('travel', '--')}</strong></div>"
        f"<div><span>客队海拔 / 炎热 / 旅途</span><strong>{away_geo.get('altitude', '--')} / {away_geo.get('heat', '--')} / {away_geo.get('travel', '--')}</strong></div>"
        f"</div>"
        f"<div class='compare-scores'>"
        f"<div class='label'>前三个最可能比分</div>"
        f"<ul>{''.join(score_rows) if score_rows else score_html}</ul>"
        f"</div>"
        f"</article>"
    )

app = FastAPI(title="WorldCup AI", version="0.1.0")
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


def render_index(snapshot: dict) -> str:
    fixture_text = "--"
    venue_text = "--"
    if snapshot.get("selected_fixture"):
        fixture_text = f"{snapshot['selected_fixture'].get('home')} 对 {snapshot['selected_fixture'].get('away')}"
        venue_text = snapshot["selected_fixture"].get("venue") or "--"

    prediction = snapshot.get("prediction") or {}
    best_score = prediction.get("best_score", "--")
    confidence = prediction.get("confidence")
    confidence_text = f"{round(confidence)}%" if confidence is not None else "--"
    status_value = STATUS_LABELS.get(snapshot.get("status", ""), snapshot.get("status", "--"))
    top_scores = prediction.get("top_scores") or []
    top_scores_html = "".join(
        f"<li>{item.get('h')}-{item.get('a')}：{round((item.get('p') or 0) * 100, 1)}%</li>"
        for item in top_scores[:3]
    ) or "<li>暂无可用概率分布</li>"

    context_rows = []
    for label, value in [
        ("数据状态", status_value),
        ("抓取时间", snapshot.get("fetched_at", "--")),
        ("今日比赛数", len(snapshot.get("fixtures") or [])),
        ("球队数量", len(snapshot.get("teams") or [])),
        ("场馆数量", len(snapshot.get("venues") or [])),
    ]:
        context_rows.append(f"<div class='context-row'><span>{label}</span><strong>{value}</strong></div>")
    context_html = "".join(context_rows)

    teams = snapshot.get("teams") or []
    selected_fixture = snapshot.get("selected_fixture") or {}
    selected_home = selected_fixture.get("home")
    selected_away = selected_fixture.get("away")
    home_team = next((team for team in teams if team.get("name") == selected_home), None)
    away_team = next((team for team in teams if team.get("name") == selected_away), None)
    compare_html = render_compare_card(prediction, selected_fixture)
    home_team_html = render_team_card(home_team, "home", "主队分析")
    away_team_html = render_team_card(away_team, "away", "客队分析")
    home_players_html = render_player_list(home_team, "home", "主队球员")
    away_players_html = render_player_list(away_team, "away", "客队球员")
    initial_data = json.dumps(snapshot, ensure_ascii=False).replace("</", "<\\/")

    return f"""<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>世界杯比分分析</title>
    <link rel="stylesheet" href="/static/style.css" />
  </head>
  <body>
    <main class="shell">
      <section class="hero">
        <div class="topbar">
          <div class="brand">
            <span class="brand-mark">26</span>
            <div>
              <strong>WORLD CUP INTELLIGENCE</strong>
              <small>赛事数据分析中心</small>
            </div>
          </div>
          <div class="live-pill"><i></i> LIVE DATA</div>
        </div>
        <div class="hero-main">
          <div class="hero-copy">
            <div class="eyebrow">MATCHDAY COMMAND CENTER</div>
            <h1>2026 世界杯<br />比赛情报中心</h1>
            <p class="lede">赛程、球队、球员与地理压力的实时比赛分析。</p>
          </div>
          <div class="fixture-control">
            <div class="control-label">今日比赛选择</div>
            <select id="fixtureSelect" aria-label="切换今日比赛"></select>
            <div class="control-meta">
              <span id="status">{snapshot.get('message', '')}</span>
              <b>{len(snapshot.get('fixtures') or [])} 场比赛</b>
            </div>
          </div>
        </div>
      </section>

      <section class="broadcast-strip">
        <div class="broadcast-item">
          <span>当前比赛</span>
          <strong id="broadcastFixture">{fixture_text}</strong>
        </div>
        <div class="broadcast-item">
          <span>今日场次</span>
          <strong>{len(snapshot.get('fixtures') or [])}</strong>
        </div>
        <div class="broadcast-item">
          <span>球队 / 场馆</span>
          <strong>{len(snapshot.get('teams') or [])} / {len(snapshot.get('venues') or [])}</strong>
        </div>
        <div class="broadcast-item">
          <span>更新状态</span>
          <strong>{status_value}</strong>
        </div>
      </section>

      <section class="grid hero-grid">
        <article class="card spotlight">
          <div class="card-kicker"><span>焦点比赛</span><b>GROUP STAGE</b></div>
          <div class="value match-title" id="fixture">{fixture_text}</div>
          <div class="meta" id="venue">{venue_text}</div>
          <div class="scoreline">
            <div>
              <span>模型比分</span>
              <strong id="bestScore">{best_score}</strong>
            </div>
            <div>
              <span>模型置信度</span>
              <strong id="confidence">置信度 {confidence_text}</strong>
            </div>
          </div>
        </article>
        <article class="card stat-card">
          <div class="stat-index">01</div>
          <div class="label">球队数据库</div>
          <div class="value">{len(snapshot.get('teams') or [])}</div>
          <div class="meta">已接入公开球队名单</div>
        </article>
        <article class="card stat-card">
          <div class="stat-index">02</div>
          <div class="label">数据更新</div>
          <div class="value" id="statusValue">{status_value}</div>
          <div class="meta" id="fetchedAt">{snapshot.get('fetched_at', '--')}</div>
        </article>
      </section>

      <section class="panel cluster dashboard-shell">
        <div class="panel-head">
          <div><span class="section-index">01</span><h2>球队对比</h2></div>
          <span class="note">主客队能力、状态与风格</span>
        </div>
        <div id="analysisPanel" class="team-board">
          {home_team_html}
          {compare_html}
          {away_team_html}
        </div>
      </section>

      <section class="panel cluster dashboard-shell">
        <div class="panel-head">
          <div><span class="section-index">02</span><h2>关键球员</h2></div>
          <span class="note">关键球员与出场数据</span>
        </div>
        <div id="playerPanel" class="player-board">
          {home_players_html}
          {away_players_html}
        </div>
      </section>

      <section class="panel cluster dashboard-shell">
        <div class="panel-head">
          <div><span class="section-index">03</span><h2>模型结论</h2></div>
        </div>
        <div id="summaryPanel" class="analysis-grid">
          <div class="analysis-block">
            <div class="analysis-label">风险判断</div>
            <div class="analysis-value">{prediction.get('risk_label', '--')}</div>
          </div>
          <div class="analysis-block">
            <div class="analysis-label">地理压力</div>
            <div class="analysis-value">{prediction.get('geo_pressure', '--')}</div>
            <div class="analysis-empty">
              海拔 {prediction.get('geo_breakdown', {}).get('home', {}).get('altitude', '--')} / {prediction.get('geo_breakdown', {}).get('away', {}).get('altitude', '--')}，炎热 {prediction.get('geo_breakdown', {}).get('home', {}).get('heat', '--')} / {prediction.get('geo_breakdown', {}).get('away', {}).get('heat', '--')}，旅途 {prediction.get('geo_breakdown', {}).get('home', {}).get('travel', '--')} / {prediction.get('geo_breakdown', {}).get('away', {}).get('travel', '--')}
            </div>
          </div>
          <div class="analysis-block wide">
            <div class="analysis-label">前三个最可能比分</div>
            <ul class="score-list">{top_scores_html}</ul>
          </div>
        </div>
      </section>

      <section class="panel cluster dashboard-shell">
        <div class="panel-head">
          <div><span class="section-index">04</span><h2>数据状态</h2></div>
        </div>
        <div id="aiContext" class="context-grid">{context_html}</div>
      </section>
    </main>
    <script>
      window.__INITIAL_DATA__ = {initial_data};
      let currentData = window.__INITIAL_DATA__ || null;
      let currentFixtureIndex = 0;
      let hasUserSelectedFixture = false;

      function clamp(value) {{
        return Math.max(0, Math.min(100, Number(value || 0)));
      }}

      function renderContext(data) {{
        const container = document.getElementById("aiContext");
        if (!container) return;
        container.innerHTML = `
          <div class="context-row"><span>数据状态</span><strong>${{data.status || "--"}}</strong></div>
          <div class="context-row"><span>抓取时间</span><strong>${{data.fetched_at || "--"}}</strong></div>
          <div class="context-row"><span>今日比赛数</span><strong>${{(data.fixtures || []).length}}</strong></div>
          <div class="context-row"><span>球队数量</span><strong>${{(data.teams || []).length}}</strong></div>
          <div class="context-row"><span>场馆数量</span><strong>${{(data.venues || []).length}}</strong></div>
        `;
      }}

      function renderTeamCard(team, tone, title) {{
        if (!team) {{
          return `<article class="team-card ${{tone}}"><div class="card-title">${{title}}</div><div class="empty-card">暂无球队数据</div></article>`;
        }}
        const metricBar = (label, value) => `
          <div class="metric-row">
            <div class="metric-head"><span>${{label}}</span><strong>${{value ?? 0}}</strong></div>
            <div class="metric-track"><span class="${{tone}}" style="width:${{clamp(value)}}%"></span></div>
          </div>`;
        return `
          <article class="team-card ${{tone}}">
            <div class="team-card-head">
              <div class="team-identity">
                <div class="team-monogram">${{team.name?.slice(0, 1) || "--"}}</div>
                <div>
                  <div class="card-title">${{team.name}}</div>
                  <div class="team-subtitle">${{team.region}}</div>
                </div>
              </div>
              <div class="team-badge">${{team.travel || ""}}</div>
            </div>
            <div class="metric-stack">
              ${{metricBar("攻击", team.attack)}}
              ${{metricBar("防守", team.defense)}}
              ${{metricBar("深度", team.depth)}}
              ${{metricBar("体能", team.fitness)}}
            </div>
            <div class="team-mini">
              <span>地理 ${{team.geo ?? "--"}}</span>
              <span>气候 ${{team.climate || "--"}}</span>
              <span>风格 ${{team.style || "--"}}</span>
            </div>
            <div class="team-outlook">${{team.outlook || ""}}</div>
            <div class="team-footer">球员 ${{(team.players || []).length}} 人</div>
          </article>`;
      }}

      function renderPlayers(team, tone, title) {{
        if (!team) {{
          return `<article class="player-card ${{tone}}"><div class="card-title">${{title}}</div><div class="empty-card">暂无球员数据</div></article>`;
        }}
        const players = [...(team.players || [])]
          .sort((a, b) => ((b.goals || 0) - (a.goals || 0)) || ((b.caps || 0) - (a.caps || 0)))
          .slice(0, 5);
        return `
          <article class="player-card ${{tone}}">
            <div class="player-card-head">
              <div>
                <div class="card-title">${{team.name}} 球员分析</div>
                <div class="team-subtitle">按进球、出场与经验排序</div>
              </div>
            </div>
            <div class="player-list">
              ${{players.length ? players.map((player) => `
                <div class="player-row">
                  <div>
                    <strong>${{player.name}}</strong>
                    <span>${{player.club || ""}}</span>
                  </div>
                  <div class="player-stats">
                    <em>${{player.position || "--"}}</em>
                    <b>${{player.caps || 0}} 场 · ${{player.goals || 0}} 球</b>
                  </div>
                </div>`).join("") : '<div class="empty-card">暂无球员数据</div>'}}
            </div>
          </article>`;
      }}

      function renderGeoDetail(geo) {{
        const home = geo?.home || {{}};
        const away = geo?.away || {{}};
        return `
          <div class="geo-detail">
            <div><span>主队海拔 / 炎热 / 旅途</span><strong>${{home.altitude ?? "--"}} / ${{home.heat ?? "--"}} / ${{home.travel ?? "--"}}</strong></div>
            <div><span>客队海拔 / 炎热 / 旅途</span><strong>${{away.altitude ?? "--"}} / ${{away.heat ?? "--"}} / ${{away.travel ?? "--"}}</strong></div>
          </div>`;
      }}

      function renderCompareCard(prediction, selected) {{
        const topScores = (prediction.top_scores || []).slice(0, 3);
        const scoreList = topScores.length
          ? topScores.map((item) => `<li><span>${{item.h}}-${{item.a}}</span><b>${{((item.p || 0) * 100).toFixed(1)}}%</b></li>`).join("")
          : "<li><span>暂无</span><b>--</b></li>";
        return `
          <article class="compare-card">
            <div class="card-title">对比结论</div>
            <div class="compare-fixture">${{selected.home && selected.away ? `${{selected.home}} 对 ${{selected.away}}` : "--"}}</div>
            <div class="compare-grid">
              <div><span>最接近比分</span><strong>${{prediction.best_score || "--"}}</strong></div>
              <div><span>置信度</span><strong>${{prediction.confidence ?? "--"}}%</strong></div>
              <div><span>风险判断</span><strong>${{prediction.risk_label || "--"}}</strong></div>
              <div><span>地理压力</span><strong>${{prediction.geo_pressure ?? "--"}}</strong></div>
            </div>
            ${{renderGeoDetail(prediction.geo_breakdown)}}
            <div class="compare-scores">
              <div class="label">前三个最可能比分</div>
              <ul>${{scoreList}}</ul>
            </div>
          </article>`;
      }}

      function renderSummary(prediction) {{
        const container = document.getElementById("summaryPanel");
        if (!container) return;
        const topScores = (prediction.top_scores || []).slice(0, 3);
        container.innerHTML = `
          <div class="analysis-block">
            <div class="analysis-label">风险判断</div>
            <div class="analysis-value">${{prediction.risk_label || "--"}}</div>
          </div>
          <div class="analysis-block">
            <div class="analysis-label">地理压力</div>
            <div class="analysis-value">${{prediction.geo_pressure ?? "--"}}</div>
            ${{renderGeoDetail(prediction.geo_breakdown)}}
          </div>
          <div class="analysis-block wide">
            <div class="analysis-label">前三个最可能比分</div>
            <ul class="score-list">
              ${{topScores.length ? topScores.map((item) => `<li>${{item.h}}-${{item.a}}：${{((item.p || 0) * 100).toFixed(1)}}%</li>`).join("") : "<li>暂无可用概率分布</li>"}}
            </ul>
          </div>
        `;
      }}

      function resolveFixtureView(data, index) {{
        const views = data.fixture_views || [];
        return views[index] || views[0] || {{
          fixture: data.selected_fixture || {{}},
          home_team: (data.teams || []).find((team) => team.name === data.selected_fixture?.home) || null,
          away_team: (data.teams || []).find((team) => team.name === data.selected_fixture?.away) || null,
          prediction: data.prediction || null,
        }};
      }}

      function renderFixtureSelect(data, selectedIndex) {{
        const select = document.getElementById("fixtureSelect");
        if (!select) return;
        const fixtures = (data.fixture_views && data.fixture_views.length)
          ? data.fixture_views.map((view) => view.fixture)
          : (data.fixtures || []);
        select.innerHTML = fixtures.map((fixture, index) => `
          <option value="${{index}}">${{fixture.home}} 对 ${{fixture.away}} · 小组 ${{fixture.group}}</option>
        `).join("");
        select.value = String(selectedIndex);
      }}

      function renderDashboard(data, index) {{
        const view = resolveFixtureView(data, index);
        const fixture = view.fixture || {{}};
        const prediction = view.prediction || data.prediction || {{}};
        const home = view.home_team || null;
        const away = view.away_team || null;
        const statusLabels = {{ live: "已更新", cached: "缓存中", unavailable: "不可用" }};
        document.getElementById("fixture").textContent = fixture.home && fixture.away ? `${{fixture.home}} 对 ${{fixture.away}}` : "--";
        document.getElementById("broadcastFixture").textContent = fixture.home && fixture.away ? `${{fixture.home}} 对 ${{fixture.away}}` : "--";
        document.getElementById("venue").textContent = fixture.venue || "--";
        document.getElementById("bestScore").textContent = prediction.best_score || "--";
        document.getElementById("confidence").textContent = prediction.confidence ? `置信度 ${{Math.round(prediction.confidence)}}%` : "--";
        document.getElementById("statusValue").textContent = statusLabels[data.status] || data.status || "--";
        document.getElementById("fetchedAt").textContent = data.fetched_at || "--";
        const analysisPanel = document.getElementById("analysisPanel");
        if (analysisPanel) {{
          analysisPanel.innerHTML = `
            ${{renderTeamCard(home, "home", "主队分析")}}
            ${{renderCompareCard(prediction, fixture)}}
            ${{renderTeamCard(away, "away", "客队分析")}}
          `;
        }}
        const playerPanel = document.getElementById("playerPanel");
        if (playerPanel) {{
          playerPanel.innerHTML = `
            ${{renderPlayers(home, "home", "主队球员")}}
            ${{renderPlayers(away, "away", "客队球员")}}
          `;
        }}
        renderSummary(prediction);
        renderContext(data);
      }}

      async function refresh() {{
        const previousView = currentData ? resolveFixtureView(currentData, currentFixtureIndex) : null;
        const previousFixture = previousView?.fixture || null;
        const res = await fetch("/api/ai-context");
        const data = await res.json();
        currentData = data;
        const fixtures = (data.fixture_views && data.fixture_views.length)
          ? data.fixture_views.map((view) => view.fixture)
          : (data.fixtures || []);
        const selected = data.selected_fixture || {{}};
        const target = hasUserSelectedFixture && previousFixture ? previousFixture : selected;
        const matchedIndex = fixtures.findIndex(
          (fixture) => fixture.home === target.home
            && fixture.away === target.away
            && fixture.group === target.group
        );
        currentFixtureIndex = matchedIndex >= 0 ? matchedIndex : 0;
        renderFixtureSelect(data, currentFixtureIndex);
        renderDashboard(data, currentFixtureIndex);
        document.getElementById("status").textContent = data.message || "";
        const statusLabels = {{ live: "已更新", cached: "缓存中", unavailable: "不可用" }};
        document.getElementById("statusValue").textContent = statusLabels[data.status] || data.status || "--";
      }}

      const fixtureSelect = document.getElementById("fixtureSelect");
      if (fixtureSelect) {{
        fixtureSelect.addEventListener("change", (event) => {{
          hasUserSelectedFixture = true;
          currentFixtureIndex = Number(event.target.value || 0);
          if (currentData) {{
            renderDashboard(currentData, currentFixtureIndex);
          }}
        }});
      }}

      if (currentData) {{
        const initialFixtures = (currentData.fixture_views && currentData.fixture_views.length)
          ? currentData.fixture_views.map((view) => view.fixture)
          : (currentData.fixtures || []);
        const selected = currentData.selected_fixture || {{}};
        currentFixtureIndex = Math.max(0, initialFixtures.findIndex((fixture) => fixture.home === selected.home && fixture.away === selected.away && fixture.group === selected.group));
        renderFixtureSelect(currentData, currentFixtureIndex);
        renderDashboard(currentData, currentFixtureIndex);
      }}

      refresh().catch(() => {{}});
    </script>
  </body>
</html>"""


@app.get("/", response_class=HTMLResponse)
def index():
    snapshot = service.latest()
    return HTMLResponse(render_index(snapshot.to_dict()))


@app.get("/api/status")
def api_status():
    return service.latest().to_dict()


@app.get("/api/today")
def api_today():
    return service.current_context()


@app.get("/api/ai-context")
def api_ai_context():
    return service.ai_context()


@app.get("/api/predict")
def api_predict(
    home: str = Query(..., description="Home team name"),
    away: str = Query(..., description="Away team name"),
    venue: str = Query(..., description="Venue name"),
):
    return service.predict(home, away, venue)


def main() -> None:
    port = int(os.getenv("PORT", "8001"))
    uvicorn.run("worldcup_ai.app:app", host="0.0.0.0", port=port, reload=False)

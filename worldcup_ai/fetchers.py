from __future__ import annotations

import re
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup

from .models import Fixture, Player, Team, Venue

TIME_ZONE = ZoneInfo("America/Los_Angeles")
SOURCE_URLS = [
    "https://en.wikipedia.org/wiki/2026_FIFA_World_Cup",
    "https://en.wikipedia.org/wiki/2026_FIFA_World_Cup_squads",
    "https://www.sbnation.com/soccer/1117513/world-cup-schedule-2026-how-to-watch-every-match-scores-and-more",
    "https://www.fifa.com/fifaplus/en/tournaments/mens/worldcup/canadamexicousa2026",
]

TEAM_ALIASES = {
    "Argentina": "阿根廷",
    "France": "法国",
    "Brazil": "巴西",
    "England": "英格兰",
    "Spain": "西班牙",
    "Germany": "德国",
    "Portugal": "葡萄牙",
    "Netherlands": "荷兰",
    "United States": "美国",
    "Mexico": "墨西哥",
    "Japan": "日本",
    "Korea Republic": "韩国",
    "South Korea": "韩国",
    "Morocco": "摩洛哥",
    "Canada": "加拿大",
    "Uruguay": "乌拉圭",
    "Australia": "澳大利亚",
    "Turkey": "土耳其",
    "Türkiye": "土耳其",
    "Qatar": "卡塔尔",
    "Switzerland": "瑞士",
    "Scotland": "苏格兰",
    "Haiti": "海地",
    "South Africa": "南非",
    "Paraguay": "巴拉圭",
    "Bosnia and Herzegovina": "波黑",
    "Czechia": "捷克",
    "Côte d'Ivoire": "科特迪瓦",
    "Ecuador": "厄瓜多尔",
    "New Zealand": "新西兰",
    "Senegal": "塞内加尔",
    "Norway": "挪威",
    "Algeria": "阿尔及利亚",
    "Saudi Arabia": "沙特阿拉伯",
    "Cabo Verde": "佛得角",
    "United Arab Emirates": "阿联酋",
    "DR Congo": "刚果民主共和国",
    "IR Iran": "伊朗",
    "Costa Rica": "哥斯达黎加",
    "Croatia": "克罗地亚",
    "Ghana": "加纳",
    "Panama": "巴拿马",
    "Colombia": "哥伦比亚",
    "Austria": "奥地利",
    "Jordan": "约旦",
    "Uzbekistan": "乌兹别克斯坦",
}

VENUE_PROFILES = {
    "墨西哥城": Venue("墨西哥城", 95, 80, 72),
    "洛杉矶": Venue("洛杉矶", 38, 61, 60),
    "达拉斯": Venue("达拉斯", 45, 83, 65),
    "休斯顿": Venue("休斯顿", 40, 86, 67),
    "迈阿密": Venue("迈阿密", 35, 88, 58),
    "纽约/新泽西": Venue("纽约/新泽西", 30, 55, 55),
    "波士顿": Venue("波士顿", 32, 54, 54),
    "亚特兰大": Venue("亚特兰大", 42, 78, 59),
    "西雅图": Venue("西雅图", 28, 46, 64),
    "温哥华": Venue("温哥华", 34, 52, 63),
    "多伦多": Venue("多伦多", 31, 49, 62),
    "堪萨斯城": Venue("堪萨斯城", 44, 72, 61),
    "Boston Stadium": Venue("Boston Stadium", 32, 54, 54),
    "New York New Jersey Stadium": Venue("New York New Jersey Stadium", 30, 55, 55),
    "San Francisco Bay Area Stadium": Venue("San Francisco Bay Area Stadium", 29, 58, 56),
    "BC Place Vancouver": Venue("BC Place Vancouver", 34, 52, 63),
}


def now_iso() -> str:
    return datetime.now(TIME_ZONE).isoformat(timespec="seconds")


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("\xa0", " ")).strip()


def translate_team_name(name: str) -> str:
    clean = normalize_text(name)
    return TEAM_ALIASES.get(clean, clean)


def team_region(name: str) -> str:
    clean = translate_team_name(name)
    mapping = {
        "阿根廷": "南美",
        "巴西": "南美",
        "乌拉圭": "南美",
        "巴拉圭": "南美",
        "厄瓜多尔": "南美",
        "哥伦比亚": "南美",
        "法国": "欧洲",
        "英格兰": "欧洲",
        "西班牙": "欧洲",
        "德国": "欧洲",
        "葡萄牙": "欧洲",
        "荷兰": "欧洲",
        "克罗地亚": "欧洲",
        "瑞士": "欧洲",
        "挪威": "欧洲",
        "捷克": "欧洲",
        "波黑": "欧洲",
        "奥地利": "欧洲",
        "苏格兰": "欧洲",
        "土耳其": "欧洲/亚洲",
        "摩洛哥": "非洲",
        "南非": "非洲",
        "塞内加尔": "非洲",
        "阿尔及利亚": "非洲",
        "科特迪瓦": "非洲",
        "加纳": "非洲",
        "海地": "北美",
        "加拿大": "北美",
        "美国": "北美",
        "墨西哥": "北美",
        "日本": "亚洲",
        "韩国": "亚洲",
        "卡塔尔": "亚洲",
        "沙特阿拉伯": "亚洲",
        "伊朗": "亚洲",
        "新西兰": "大洋洲",
        "澳大利亚": "亚洲/大洋洲",
        "乌兹别克斯坦": "亚洲",
        "约旦": "亚洲",
        "巴拿马": "北美",
        "哥斯达黎加": "北美",
    }
    return mapping.get(clean, "国际")


def venue_profile(name: str) -> Venue:
    return VENUE_PROFILES.get(name, Venue(name, 40, 60, 60))


def wikipedia_page_html(page: str) -> str:
    response = requests.get(
        f"https://en.wikipedia.org/wiki/{page}",
        timeout=20,
        headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
        },
    )
    response.raise_for_status()
    return response.text


def html_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    return soup.get_text("\n", strip=True)


def today_heading() -> str:
    label = datetime.now(TIME_ZONE).strftime("%A, %d %B %Y")
    return label.replace(" 0", " ")


def today_schedule_heading() -> str:
    label = datetime.now(TIME_ZONE).strftime("%A, %B %d")
    return label.replace(" 0", " ")


def schedule_article_html() -> str:
    response = requests.get(
        SOURCE_URLS[2],
        timeout=20,
        headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
        },
    )
    response.raise_for_status()
    return response.text


def fifa_official_page_html() -> str:
    response = requests.get(
        SOURCE_URLS[-1],
        timeout=20,
        headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
        },
    )
    response.raise_for_status()
    return response.text


def parse_fixture_candidates(text: str) -> list[Fixture]:
    lines = [normalize_text(line) for line in text.splitlines()]
    fixtures: list[Fixture] = []
    line_re = re.compile(r"(.+?)\s+v\s+(.+?)\s+[–-]\s+Group\s+([A-L])\s+[–-]\s+(.+)")
    for line in lines:
        match = line_re.match(line)
        if not match:
            continue
        fixtures.append(
            Fixture(
                home=normalize_text(match.group(1)),
                away=normalize_text(match.group(2)),
                group=match.group(3),
                venue=normalize_text(match.group(4)),
                date=today_heading(),
            )
        )
    return fixtures


def parse_schedule_fixtures(text: str) -> list[Fixture]:
    date_re = re.compile(r"^(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),\s+[A-Za-z]+\s+\d{1,2}$")
    fixture_re = re.compile(r"Group\s+([A-L]):\s+(.+?)\s+vs\.?\s+(.+?),\s+([0-9:.apmAPM\s]+),?$")
    target_date = today_schedule_heading()
    current_date = ""
    venue_map = {
        ("Qatar", "Switzerland"): "San Francisco Bay Area Stadium",
        ("Brazil", "Morocco"): "New York New Jersey Stadium",
        ("Haiti", "Scotland"): "Boston Stadium",
        ("Australia", "Türkiye"): "BC Place Vancouver",
    }
    fixtures: list[Fixture] = []
    for raw_line in text.splitlines():
        line = normalize_text(raw_line)
        if not line:
            continue
        if date_re.match(line):
            current_date = line
            continue
        match = fixture_re.match(line)
        if not match or current_date != target_date:
            continue
        fixtures.append(
            Fixture(
                home=normalize_text(match.group(2)),
                away=normalize_text(match.group(3)),
                group=match.group(1),
                venue=venue_map.get((normalize_text(match.group(2)), normalize_text(match.group(3))), ""),
                date=today_heading(),
            )
        )
    return fixtures


def parse_today_fixtures(*texts: str) -> list[Fixture]:
    date_re = re.compile(r"^(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),\s+\d{1,2}\s+[A-Za-z]+\s+\d{4}$")
    fixture_re = re.compile(r"(.+?)\s+v\s+(.+?)\s+[–-]\s+Group\s+([A-L])\s+[–-]\s+(.+)")
    seen: set[tuple[str, str, str, str]] = set()
    fixtures: list[Fixture] = []
    for text in texts:
        for fixture in parse_schedule_fixtures(text):
            key = (fixture.home, fixture.away, fixture.group, fixture.venue)
            if key in seen:
                continue
            seen.add(key)
            fixtures.append(fixture)

        current_date = ""
        for raw_line in text.splitlines():
            line = normalize_text(raw_line)
            if not line:
                continue
            if date_re.match(line):
                current_date = line
                continue
            match = fixture_re.match(line)
            if not match:
                continue
            fixture_date = current_date or today_heading()
            if fixture_date != today_heading():
                continue
            fixture = Fixture(
                home=normalize_text(match.group(1)),
                away=normalize_text(match.group(2)),
                group=match.group(3),
                venue=normalize_text(match.group(4)),
                date=fixture_date,
            )
            key = (fixture.home, fixture.away, fixture.group, fixture.venue)
            if key in seen:
                continue
            seen.add(key)
            fixtures.append(fixture)
    return fixtures


def parse_squads(html: str) -> dict[str, list[Player]]:
    soup = BeautifulSoup(html, "html.parser")
    nodes = soup.find_all(["h2", "h3", "h4", "h5", "table"])
    squads: dict[str, list[Player]] = {}
    current_team = ""

    for node in nodes:
        if node.name in {"h2", "h3", "h4", "h5"}:
            headline = node.find(class_="mw-headline")
            raw = normalize_text(headline.get_text(" ", strip=True) if headline else node.get_text(" ", strip=True))
            if raw and not re.search(r"squads|statistics|notes|references|external links", raw, re.I):
                current_team = translate_team_name(raw)
            continue

        if not current_team:
            continue

        rows = node.find_all("tr")
        if len(rows) < 2:
            continue
        header_text = normalize_text(rows[0].get_text(" ", strip=True))
        if not re.search(r"player|name|position|caps|goals", header_text, re.I):
            continue

        players: list[Player] = []
        for row in rows[1:]:
            cells = [normalize_text(cell.get_text(" ", strip=True)) for cell in row.find_all(["td", "th"])]
            cells = [cell for cell in cells if cell]
            if not cells:
                continue

            links = [normalize_text(a.get_text(" ", strip=True)) for a in row.find_all("a")]
            name = next((text for text in links if not re.match(r"^(GK|DF|MF|FW)$", text, re.I) and "image" not in text.lower()), "")
            if not name:
                name = cells[2] if len(cells) > 2 else cells[1] if len(cells) > 1 else cells[0]
            if not name or re.search(r"coach|head coach|manager", name, re.I):
                continue

            position = ""
            match = re.search(r"\b(GK|DF|MF|FW)\b", row.get_text(" ", strip=True), re.I)
            if match:
                position = match.group(1).upper()
            elif len(cells) > 1:
                position = cells[1]

            age_match = re.search(r"aged\s+(\d+)", row.get_text(" ", strip=True), re.I)
            caps = None
            goals = None
            try:
                caps = int(cells[4])
            except Exception:
                pass
            try:
                goals = int(cells[5])
            except Exception:
                pass
            club = cells[6] if len(cells) > 6 else ""
            players.append(Player(name=name, position=position, age=int(age_match.group(1)) if age_match else None, caps=caps, goals=goals, club=club))
            if len(players) >= 8:
                break

        if players:
            squads[current_team] = players

    return squads


def create_live_team(name: str, players: list[Player]) -> Team:
    region = team_region(name)
    forwards = [player for player in players if re.search(r"FW|FWD|Forward|前锋", player.position, re.I)]
    defenders = [player for player in players if re.search(r"DF|DEF|Defender|后卫", player.position, re.I)]
    caps_total = sum(player.caps or 0 for player in players)
    goals_total = sum(player.goals or 0 for player in players)
    age_values = [player.age for player in players if player.age is not None]
    age_avg = sum(age_values) / len(age_values) if age_values else 28
    return Team(
        name=name,
        region=region,
        attack=max(60, min(92, int(58 + goals_total * 0.8 + len(forwards) * 2.1))),
        defense=max(58, min(92, int(56 + len(defenders) * 2.5 + caps_total * 0.05))),
        depth=max(58, min(88, int(56 + min(len(players), 26) * 1.2))),
        fitness=max(60, min(90, int(82 - age_avg * 0.35))),
        geo=82 if region == "北美" else 76 if region == "非洲" else 71,
        climate="公开名单",
        travel="低" if region == "北美" else "中等",
        style="实时名单接入",
        outlook="已接入公开名单数据，模型评分为保守默认值。",
        players=players,
    )


def hydrate_teams(squads: dict[str, list[Player]]) -> list[Team]:
    return [create_live_team(name, players) for name, players in sorted(squads.items())]


def select_fixture(teams: list[Team], fixtures: list[Fixture]) -> Fixture | None:
    team_names = {team.name for team in teams}
    for fixture in fixtures:
        if translate_team_name(fixture.home) in team_names and translate_team_name(fixture.away) in team_names:
            venue = fixture.venue
            if not venue:
                venue = {
                    ("Qatar", "Switzerland"): "San Francisco Bay Area Stadium",
                    ("Brazil", "Morocco"): "New York New Jersey Stadium",
                    ("Haiti", "Scotland"): "Boston Stadium",
                    ("Australia", "Türkiye"): "BC Place Vancouver",
                }.get((fixture.home, fixture.away), "")
            return Fixture(
                home=translate_team_name(fixture.home),
                away=translate_team_name(fixture.away),
                group=fixture.group,
                venue=venue if venue in VENUE_PROFILES or venue else fixture.venue,
                date=fixture.date,
            )
    return fixtures[0] if fixtures else None


def live_data_sources() -> list[str]:
    return SOURCE_URLS.copy()

"""Render Lucas Camy's public GitHub contribution calendar as a self-contained SVG."""

from datetime import date
from html import escape
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import Request, urlopen
import re


SOURCE = "https://github.com/users/LucasCamy/contributions"
OUTPUT = Path(__file__).resolve().parents[1] / "assets" / "contributions.svg"
PALETTE = ("#1e293b", "#164e63", "#0e7490", "#14b8a6", "#5eead4")


class CalendarParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.days = {}

    def handle_starttag(self, tag, attrs):
        if tag != "td":
            return
        data = dict(attrs)
        day = data.get("data-date", "")
        level = data.get("data-level", "")
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", day) and level in ("0", "1", "2", "3", "4"):
            self.days[day] = int(level)


def fetch_calendar():
    request = Request(SOURCE, headers={"User-Agent": "LucasCamy-profile/1.0"})
    with urlopen(request, timeout=15) as response:
        if response.status != 200:
            raise RuntimeError(f"GitHub returned HTTP {response.status}")
        html = response.read(1_000_001)
    if len(html) > 1_000_000:
        raise RuntimeError("GitHub response exceeded size limit")
    parser = CalendarParser()
    parser.feed(html.decode("utf-8"))
    if len(parser.days) < 350:
        raise RuntimeError(f"Expected a full calendar, found {len(parser.days)} days")
    heading = re.search(rb"<h2[^>]*id=\"js-contribution-activity-description\"[^>]*>(.*?)</h2>", html, re.S)
    if heading:
        text = re.sub(rb"<[^>]+>", b" ", heading.group(1))
        count = re.search(rb"([\d,]+)\s+contributions?", text)
        total = count.group(1).decode("ascii") if count else "—"
    else:
        total = "—"
    return parser.days, total


def render(days, total):
    dates = sorted(date.fromisoformat(value) for value in days)
    first_sunday = dates[0].toordinal() - ((dates[0].weekday() + 1) % 7)
    squares = []
    months = []
    month_names = ("jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez")
    previous_month = None
    for day in dates:
        week = (day.toordinal() - first_sunday) // 7
        weekday = (day.weekday() + 1) % 7
        x, y = 52 + week * 14.5, 72 + weekday * 14.5
        if day.month != previous_month:
            months.append(f'<text x="{x:.1f}" y="63">{month_names[day.month - 1]}</text>')
            previous_month = day.month
        level = days[day.isoformat()]
        delay = week * 0.012 + weekday * 0.015
        squares.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="10" height="10" rx="2" '
            f'fill="{PALETTE[level]}" opacity="0">'
            f'<title>{escape(day.isoformat())}: nível {level} de atividade pública</title>'
            f'<animate attributeName="opacity" from="0" to="1" begin="{delay:.3f}s" dur="0.2s" fill="freeze"/>'
            '</rect>'
        )
    grid = "\n    ".join(squares)
    month_labels = "\n    ".join(months)
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="860" height="205" viewBox="0 0 860 205" role="img" aria-labelledby="title desc">
  <title id="title">Atividade pública de Lucas Camy</title>
  <desc id="desc">Calendário de contribuições públicas dos últimos 12 meses, atualizado automaticamente.</desc>
  <rect width="860" height="205" rx="16" fill="#0b1220"/>
  <rect x="1" y="1" width="858" height="203" rx="15" fill="none" stroke="#273449" stroke-width="2"/>
  <text x="24" y="31" fill="#5eead4" font-family="Consolas,monospace" font-size="14" font-weight="700">atividade pública</text>
  <text x="836" y="31" text-anchor="end" fill="#92a4bf" font-family="Consolas,monospace" font-size="12">{escape(total)} contribuições / 12 meses</text>
  <path d="M24 43H836" stroke="#273449"/>
  <g fill="#92a4bf" font-family="Consolas,monospace" font-size="10">
    {month_labels}
  </g>
  <g fill="#92a4bf" font-family="Consolas,monospace" font-size="10">
    <text x="24" y="81">dom</text><text x="24" y="124">qua</text><text x="24" y="167">sáb</text>
  </g>
  <g>
    {grid}
  </g>
  <text x="24" y="191" fill="#92a4bf" font-family="Consolas,monospace" font-size="10">Fonte: GitHub · apenas atividade visível publicamente</text>
</svg>
'''


if __name__ == "__main__":
    calendar, total_contributions = fetch_calendar()
    OUTPUT.write_text(render(calendar, total_contributions), encoding="utf-8")
    print(f"Updated {OUTPUT.name}: {len(calendar)} days, {total_contributions} public contributions")

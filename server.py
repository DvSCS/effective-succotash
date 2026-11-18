"""
FUTBora - Stremio / Nuvio Football Matches Addon
Protocol: Stremio Addon v3
Leagues: Brasileirao (Serie A / B), La Liga, Champions League, Premier League, Libertadores, etc.
Zero external dependencies required (Pure Python 3.8+ standard library).
"""

import json
import urllib.request
import urllib.parse
from datetime import datetime, timezone, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler
import socketserver
import time
import re
import os

PORT = int(os.environ.get("PORT", 7000))
CACHE_TTL = 60  # Cache scoreboard for 60 seconds

# League identifiers for ESPN Public API
LEAGUES = {
    "brasileirao": {
        "slug": "bra.1",
        "name": "Brasileirão Série A",
        "country": "Brasil"
    },
    "brasileirao_b": {
        "slug": "bra.2",
        "name": "Brasileirão Série B",
        "country": "Brasil"
    },
    "copa_brasil": {
        "slug": "bra.copa_do_brasil",
        "name": "Copa do Brasil",
        "country": "Brasil"
    },
    "libertadores": {
        "slug": "conmebol.libertadores",
        "name": "Copa Libertadores",
        "country": "América do Sul"
    },
    "sulamericana": {
        "slug": "conmebol.sudamericana",
        "name": "Copa Sul-Americana",
        "country": "América do Sul"
    },
    "laliga": {
        "slug": "esp.1",
        "name": "La Liga",
        "country": "Espanha"
    },
    "premier_league": {
        "slug": "eng.1",
        "name": "Premier League",
        "country": "Inglaterra"
    },
    "champions_league": {
        "slug": "uefa.champions",
        "name": "Champions League",
        "country": "Europa"
    },
    "europa_league": {
        "slug": "uefa.europa",
        "name": "Europa League",
        "country": "Europa"
    },
    "serie_a": {
        "slug": "ita.1",
        "name": "Serie A",
        "country": "Itália"
    },
    "bundesliga": {
        "slug": "ger.1",
        "name": "Bundesliga",
        "country": "Alemanha"
    },
    "ligue_1": {
        "slug": "fra.1",
        "name": "Ligue 1",
        "country": "França"
    }
}

GENRE_MAP = {
    "Todos": None,
    "Brasileirão Série A": "bra.1",
    "Brasileirão Série B": "bra.2",
    "Copa do Brasil": "bra.copa_do_brasil",
    "Copa Libertadores": "conmebol.libertadores",
    "La Liga": "esp.1",
    "Premier League": "eng.1",
    "Champions League": "uefa.champions",
    "Serie A": "ita.1",
    "Bundesliga": "ger.1"
}

_cache = {
    "timestamp": 0,
    "matches": []
}

def format_brazil_time(iso_date_str):
    try:
        dt = datetime.fromisoformat(iso_date_str.replace("Z", "+00:00"))
        # UTC-3 (Horário de Brasília)
        br_tz = timezone(timedelta(hours=-3))
        dt_br = dt.astimezone(br_tz)
        today = datetime.now(br_tz).date()
        match_date = dt_br.date()
        
        time_part = dt_br.strftime("%H:%M")
        if match_date == today:
            return f"Hoje às {time_part}"
        elif match_date == today + timedelta(days=1):
            return f"Amanhã às {time_part}"
        elif match_date == today - timedelta(days=1):
            return f"Ontem às {time_part}"
        else:
            return dt_br.strftime("%d/%m às %H:%M")
    except Exception:
        return iso_date_str

def fetch_league_events(league_slug, league_name):
    url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{league_slug}/scoreboard"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) FUTBora/1.0"}
    )
    matches = []
    try:
        with urllib.request.urlopen(req, timeout=4) as response:
            if response.status == 200:
                data = json.loads(response.read().decode("utf-8"))
                events = data.get("events", [])
                for ev in events:
                    match_id = ev.get("id")
                    name = ev.get("name", "Jogo")
                    short_name = ev.get("shortName", name)
                    date_iso = ev.get("date", "")
                    status_obj = ev.get("status", {}).get("type", {})
                    status_state = status_obj.get("state", "pre")  # pre, in, post
                    status_detail = status_obj.get("detail", "")
                    
                    competitions = ev.get("competitions", [{}])[0]
                    competitors = competitions.get("competitors", [])
                    
                    home_team = {"name": "Mandante", "score": "0", "logo": ""}
                    away_team = {"name": "Visitante", "score": "0", "logo": ""}
                    
                    for comp in competitors:
                        is_home = comp.get("homeAway") == "home"
                        team_data = comp.get("team", {})
                        t_obj = {
                            "name": team_data.get("displayName", team_data.get("name", "")),
                            "shortName": team_data.get("shortDisplayName", team_data.get("abbreviation", "")),
                            "score": comp.get("score", "0"),
                            "logo": team_data.get("logo", "")
                        }
                        if is_home:
                            home_team = t_obj
                        else:
                            away_team = t_obj
                    
                    # Broadcast channels
                    broadcasts = []
                    for b in competitions.get("broadcasts", []):
                        for n in b.get("names", []):
                            if n not in broadcasts:
                                broadcasts.append(n)
                    
                    venue = competitions.get("venue", {}).get("fullName", "")
                    
                    matches.append({
                        "id": f"futbora_{match_id}",
                        "raw_id": match_id,
                        "league_slug": league_slug,
                        "league_name": league_name,
                        "name": f"{home_team['name']} x {away_team['name']}",
                        "short_name": f"{home_team['shortName']} x {away_team['shortName']}",
                        "home": home_team,
                        "away": away_team,
                        "date_iso": date_iso,
                        "time_str": format_brazil_time(date_iso),
                        "state": status_state,
                        "status_detail": status_detail,
                        "broadcasts": broadcasts,
                        "venue": venue
                    })
    except Exception as e:
        # Silently continue on individual league failures
        pass
    return matches

def get_all_matches():
    now = time.time()
    if now - _cache["timestamp"] < CACHE_TTL and _cache["matches"]:
        return _cache["matches"]
    
    all_matches = []
    for key, info in LEAGUES.items():
        league_matches = fetch_league_events(info["slug"], info["name"])
        all_matches.extend(league_matches)
    
    # If network is down or no matches currently in season, provide realistic preview fallback
    if not all_matches:
        all_matches = [
            {
                "id": "futbora_demo_fla_pal",
                "raw_id": "demo_fla_pal",
                "league_slug": "bra.1",
                "league_name": "Brasileirão Série A",
                "name": "Flamengo x Palmeiras",
                "short_name": "FLA x PAL",
                "home": {
                    "name": "Flamengo",
                    "shortName": "FLA",
                    "score": "2",
                    "logo": "https://a.espncdn.com/i/teamlogos/soccer/500/819.png"
                },
                "away": {
                    "name": "Palmeiras",
                    "shortName": "PAL",
                    "score": "1",
                    "logo": "https://a.espncdn.com/i/teamlogos/soccer/500/2029.png"
                },
                "date_iso": datetime.now(timezone.utc).isoformat(),
                "time_str": "Hoje às 21:30",
                "state": "in",
                "status_detail": "2º Tempo - 72'",
                "broadcasts": ["Globo", "Premiere"],
                "venue": "Maracanã, Rio de Janeiro"
            },
            {
                "id": "futbora_demo_rma_bar",
                "raw_id": "demo_rma_bar",
                "league_slug": "esp.1",
                "league_name": "La Liga",
                "name": "Real Madrid x Barcelona",
                "short_name": "RMA x BAR",
                "home": {
                    "name": "Real Madrid",
                    "shortName": "RMA",
                    "score": "0",
                    "logo": "https://a.espncdn.com/i/teamlogos/soccer/500/86.png"
                },
                "away": {
                    "name": "Barcelona",
                    "shortName": "BAR",
                    "score": "0",
                    "logo": "https://a.espncdn.com/i/teamlogos/soccer/500/83.png"
                },
                "date_iso": datetime.now(timezone.utc).isoformat(),
                "time_str": "Hoje às 17:00",
                "state": "pre",
                "status_detail": "Agendado",
                "broadcasts": ["ESPN", "Disney+"],
                "venue": "Santiago Bernabéu, Madrid"
            },
            {
                "id": "futbora_demo_liv_mci",
                "raw_id": "demo_liv_mci",
                "league_slug": "eng.1",
                "league_name": "Premier League",
                "name": "Liverpool x Manchester City",
                "short_name": "LIV x MCI",
                "home": {
                    "name": "Liverpool",
                    "shortName": "LIV",
                    "score": "1",
                    "logo": "https://a.espncdn.com/i/teamlogos/soccer/500/364.png"
                },
                "away": {
                    "name": "Manchester City",
                    "shortName": "MCI",
                    "score": "1",
                    "logo": "https://a.espncdn.com/i/teamlogos/soccer/500/382.png"
                },
                "date_iso": datetime.now(timezone.utc).isoformat(),
                "time_str": "Hoje às 13:30",
                "state": "post",
                "status_detail": "Finalizado",
                "broadcasts": ["ESPN", "Star+"],
                "venue": "Anfield, Liverpool"
            }
        ]
    
    _cache["timestamp"] = now
    _cache["matches"] = all_matches
    return all_matches

def match_to_meta(m, host="localhost:7000"):
    is_live = m["state"] == "in"
    is_post = m["state"] == "post"
    
    status_label = "🔴 AO VIVO" if is_live else ("🏁 FINALIZADO" if is_post else f"⏰ {m['time_str']}")
    score_label = f"({m['home']['score']} x {m['away']['score']})" if (is_live or is_post) else "vs"
    
    title = f"{m['name']} {score_label}"
    
    genres = [m["league_name"], "Futebol"]
    if is_live:
        genres.insert(0, "🔴 Ao Vivo")
        
    desc_lines = [
        f"🏆 Competição: {m['league_name']}",
        f"📊 Status: {status_label} ({m['status_detail']})",
        f"🕒 Horário: {m['time_str']}",
        f"🏟️ Local: {m['venue'] or 'Estádio a definir'}",
    ]
    if m["broadcasts"]:
        desc_lines.append(f"📺 Transmissão: {', '.join(m['broadcasts'])}")
    else:
        desc_lines.append("📺 Transmissão: Consultar guia de TV local")
        
    desc_lines.append("\n⚽ FUTBora - Jogos de Futebol no seu Stremio & Nuvio.")
    
    poster_url = f"http://{host}/poster/{m['raw_id']}.svg"
    banner_url = "https://images.unsplash.com/photo-1508098682722-e99c43a406b2?q=80&w=1200&auto=format&fit=crop"
    
    return {
        "id": m["id"],
        "type": "tv",
        "name": title,
        "poster": poster_url,
        "posterShape": "poster",
        "background": banner_url,
        "logo": m["home"]["logo"] or m["away"]["logo"],
        "description": "\n".join(desc_lines),
        "releaseInfo": status_label,
        "genres": genres
    }

def generate_svg_poster(match):
    home = match["home"]
    away = match["away"]
    is_live = match["state"] == "in"
    is_post = match["state"] == "post"
    
    badge_bg = "#E50914" if is_live else ("#333333" if is_post else "#1E88E5")
    badge_text = "AO VIVO" if is_live else ("FINALIZADO" if is_post else match["time_str"].upper())
    
    score_display = f"{home['score']} - {away['score']}" if (is_live or is_post) else "VS"
    
    home_logo = f'<image href="{home["logo"]}" x="40" y="240" width="130" height="130" preserveAspectRatio="xMidYMid meet"/>' if home["logo"] else f'<circle cx="105" cy="305" r="50" fill="#222"/><text x="105" y="315" font-size="28" font-weight="bold" fill="#fff" text-anchor="middle">{home["shortName"]}</text>'
    away_logo = f'<image href="{away["logo"]}" x="250" y="240" width="130" height="130" preserveAspectRatio="xMidYMid meet"/>' if away["logo"] else f'<circle cx="315" cy="305" r="50" fill="#222"/><text x="315" y="315" font-size="28" font-weight="bold" fill="#fff" text-anchor="middle">{away["shortName"]}</text>'
    
    venue_text = (match["venue"][:26] + "...") if len(match.get("venue", "")) > 28 else match.get("venue", "")

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="420" height="630" viewBox="0 0 420 630">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#0a0f1d"/>
      <stop offset="50%" stop-color="#101827"/>
      <stop offset="100%" stop-color="#060911"/>
    </linearGradient>
    <linearGradient id="cardGrad" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#1f293d" stop-opacity="0.8"/>
      <stop offset="100%" stop-color="#111827" stop-opacity="0.9"/>
    </linearGradient>
    <filter id="shadow" x="-10%" y="-10%" width="120%" height="120%">
      <feDropShadow dx="0" dy="4" stdDeviation="6" flood-color="#000" flood-opacity="0.6"/>
    </filter>
  </defs>

  <!-- Background -->
  <rect width="420" height="630" fill="url(#bg)"/>
  
  <!-- Subtle pitch lines -->
  <circle cx="210" cy="315" r="160" fill="none" stroke="#ffffff" stroke-opacity="0.04" stroke-width="2"/>
  <line x1="210" y1="50" x2="210" y2="580" stroke="#ffffff" stroke-opacity="0.04" stroke-width="2"/>

  <!-- League Header Banner -->
  <rect x="25" y="35" width="370" height="42" rx="8" fill="#1e293b" stroke="#334155" stroke-width="1"/>
  <text x="210" y="62" font-family="Segoe UI, Roboto, Helvetica, Arial, sans-serif" font-size="15" font-weight="700" fill="#38bdf8" text-anchor="middle" letter-spacing="1">
    ⚽ {match['league_name'].upper()}
  </text>

  <!-- Status Badge -->
  <rect x="130" y="100" width="160" height="32" rx="16" fill="{badge_bg}" filter="url(#shadow)"/>
  <text x="210" y="121" font-family="Segoe UI, Roboto, Helvetica, Arial, sans-serif" font-size="13" font-weight="800" fill="#ffffff" text-anchor="middle" letter-spacing="0.5">
    {badge_text}
  </text>

  <!-- Matchup Card -->
  <rect x="25" y="155" width="370" height="340" rx="16" fill="url(#cardGrad)" stroke="#334155" stroke-width="1.5" filter="url(#shadow)"/>

  <!-- Home & Away Logos -->
  {home_logo}
  {away_logo}

  <!-- Versus / Score in Center -->
  <rect x="170" y="280" width="80" height="50" rx="10" fill="#0b1120" stroke="#475569" stroke-width="1"/>
  <text x="210" y="314" font-family="Segoe UI, Roboto, Helvetica, Arial, sans-serif" font-size="20" font-weight="900" fill="#f8fafc" text-anchor="middle">
    {score_display}
  </text>

  <!-- Team Names -->
  <text x="105" y="410" font-family="Segoe UI, Roboto, Helvetica, Arial, sans-serif" font-size="16" font-weight="700" fill="#ffffff" text-anchor="middle">
    {home['shortName']}
  </text>
  <text x="315" y="410" font-family="Segoe UI, Roboto, Helvetica, Arial, sans-serif" font-size="16" font-weight="700" fill="#ffffff" text-anchor="middle">
    {away['shortName']}
  </text>

  <!-- Detail / Clock -->
  <text x="210" y="455" font-family="Segoe UI, Roboto, Helvetica, Arial, sans-serif" font-size="13" font-weight="600" fill="#94a3b8" text-anchor="middle">
    {match['status_detail']}
  </text>

  <!-- Bottom Footer Info -->
  <rect x="25" y="520" width="370" height="75" rx="12" fill="#0f172a" stroke="#1e293b" stroke-width="1"/>
  
  <text x="210" y="546" font-family="Segoe UI, Roboto, Helvetica, Arial, sans-serif" font-size="12" font-weight="500" fill="#64748b" text-anchor="middle">
    📍 {venue_text or 'Estádio Oficial'}
  </text>
  <text x="210" y="572" font-family="Segoe UI, Roboto, Helvetica, Arial, sans-serif" font-size="12" font-weight="700" fill="#22c55e" text-anchor="middle">
    📺 {', '.join(match['broadcasts']) if match['broadcasts'] else 'Transmissão Esportiva'}
  </text>
</svg>"""
    return svg

class StremioAddonHandler(BaseHTTPRequestHandler):
    def send_cors_headers(self, content_type="application/json"):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Content-Type", content_type)
        self.end_headers()

    def do_OPTIONS(self):
        self.send_cors_headers()

    def do_GET(self):
        host = self.headers.get("Host", f"localhost:{PORT}")
        path = self.path

        # 1. Manifest
        if path == "/manifest.json" or path == "/":
            manifest = {
                "id": "community.futbora.jogosdodia",
                "version": "1.0.0",
                "name": "⚽ FUTBora - Jogos de Hoje",
                "description": "Jogos de futebol do dia ao vivo e agendados: Brasileirão, La Liga, Champions, Premier League e mais, estilo Cinemeta.",
                "logo": f"http://{host}/poster/demo_fla_pal.svg",
                "background": "https://images.unsplash.com/photo-1508098682722-e99c43a406b2?q=80&w=1200&auto=format&fit=crop",
                "types": ["tv", "movie"],
                "resources": [
                    "catalog",
                    "meta",
                    "stream"
                ],
                "catalogs": [
                    {
                        "type": "tv",
                        "id": "jogos_do_dia",
                        "name": "⚽ Jogos de Hoje (Futebol)",
                        "extra": [
                            {
                                "name": "genre",
                                "options": list(GENRE_MAP.keys()),
                                "isRequired": False
                            },
                            {
                                "name": "search",
                                "isRequired": False
                            }
                        ]
                    }
                ],
                "idPrefixes": ["futbora_"]
            }
            self.send_cors_headers("application/json; charset=utf-8")
            self.wfile.write(json.dumps(manifest, ensure_ascii=False).encode("utf-8"))
            return

        # 2. Dynamic SVG Poster: /poster/{match_id}.svg
        if path.startswith("/poster/"):
            match_raw_id = path.replace("/poster/", "").replace(".svg", "")
            matches = get_all_matches()
            target = next((m for m in matches if m["raw_id"] == match_raw_id), matches[0] if matches else None)
            if target:
                svg_data = generate_svg_poster(target)
                self.send_cors_headers("image/svg+xml; charset=utf-8")
                self.wfile.write(svg_data.encode("utf-8"))
                return
            else:
                self.send_error(404, "Poster Not Found")
                return

        # 3. Catalog: /catalog/{type}/{id}.json or with extra params
        # Format: /catalog/tv/jogos_do_dia.json or /catalog/tv/jogos_do_dia/genre=La%20Liga.json
        if path.startswith("/catalog/"):
            clean_path = path.split("?")[0]
            parts = clean_path.strip("/").split("/")
            
            # Extract genre or search from path or query string
            genre_filter = None
            search_query = None
            
            if len(parts) >= 4:
                extra_param = urllib.parse.unquote(parts[3]).replace(".json", "")
                if extra_param.startswith("genre="):
                    genre_filter = extra_param.split("genre=")[1]
                elif extra_param.startswith("search="):
                    search_query = extra_param.split("search=")[1].lower()
            
            matches = get_all_matches()
            
            # Apply genre filtering
            if genre_filter and genre_filter in GENRE_MAP:
                slug_target = GENRE_MAP[genre_filter]
                if slug_target:
                    matches = [m for m in matches if m["league_slug"] == slug_target]
            
            # Apply search filtering
            if search_query:
                matches = [m for m in matches if search_query in m["name"].lower() or search_query in m["league_name"].lower()]

            metas = [match_to_meta(m, host=host) for m in matches]
            response_data = {"metas": metas}
            
            self.send_cors_headers("application/json; charset=utf-8")
            self.wfile.write(json.dumps(response_data, ensure_ascii=False).encode("utf-8"))
            return

        # 4. Meta Details: /meta/{type}/{id}.json
        if path.startswith("/meta/"):
            clean_path = path.split("?")[0].replace(".json", "")
            parts = clean_path.strip("/").split("/")
            if len(parts) >= 3:
                target_id = parts[2]
                matches = get_all_matches()
                match = next((m for m in matches if m["id"] == target_id), None)
                if match:
                    meta_obj = match_to_meta(match, host=host)
                    self.send_cors_headers("application/json; charset=utf-8")
                    self.wfile.write(json.dumps({"meta": meta_obj}, ensure_ascii=False).encode("utf-8"))
                    return

            self.send_error(404, "Meta Not Found")
            return

        # 5. Stream: /stream/{type}/{id}.json
        if path.startswith("/stream/"):
            clean_path = path.split("?")[0].replace(".json", "")
            parts = clean_path.strip("/").split("/")
            target_id = parts[2] if len(parts) >= 3 else ""
            matches = get_all_matches()
            match = next((m for m in matches if m["id"] == target_id), None)
            
            streams = []
            if match:
                # Provide informational search & transmission stream entry
                broadcast_txt = ", ".join(match["broadcasts"]) if match["broadcasts"] else "Canais Oficiais / Premiere / ESPN"
                streams.append({
                    "title": f"📺 {match['name']} - Transmissão: {broadcast_txt}",
                    "name": "FUTBora Info",
                    "externalUrl": f"https://www.google.com/search?q={urllib.parse.quote(match['name'] + ' onde assistir ao vivo')}"
                })
                # Add YouTube live search redirect for official club broadcasts (e.g. CazéTV, GE, FlaTV)
                streams.append({
                    "title": "🔴 Buscar Transmissão / Melhores Momentos no YouTube",
                    "name": "YouTube Esportes",
                    "externalUrl": f"https://www.youtube.com/results?search_query={urllib.parse.quote(match['name'] + ' ao vivo')}"
                })
            
            self.send_cors_headers("application/json; charset=utf-8")
            self.wfile.write(json.dumps({"streams": streams}, ensure_ascii=False).encode("utf-8"))
            return

        # Default fallback
        self.send_error(404, "Not Found")

class ThreadingSimpleServer(socketserver.ThreadingMixIn, HTTPServer):
    daemon_threads = True

def run():
    server_address = ("", PORT)
    httpd = ThreadingSimpleServer(server_address, StremioAddonHandler)
    print("=" * 60)
    print(f"🚀 FUTBora - Addon de Futebol para Stremio & Nuvio rodando!")
    print(f"📍 Endereço local: http://localhost:{PORT}")
    print(f"🔗 URL do Manifest: http://localhost:{PORT}/manifest.json")
    print(f"👉 No Stremio ou Nuvio, vá em 'Addons' -> 'Instalar Addon' e cole:")
    print(f"   http://localhost:{PORT}/manifest.json")
    print("=" * 60)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor encerrado.")
        httpd.server_close()

if __name__ == "__main__":
    run()

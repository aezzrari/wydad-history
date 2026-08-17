from flask import Flask, render_template, request, redirect, url_for, flash, session, Response
import pandas as pd
import os
import csv
import hashlib
import json
import unicodedata
from functools import wraps
from collections import Counter
from datetime import datetime, date
from werkzeug.security import check_password_hash

try:
    import psycopg2
except ImportError:
    psycopg2 = None

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")
DATABASE_URL = os.environ.get("DATABASE_URL")
SITE_URL = "https://www.wydad-history.com"
GOOGLE_VERIFICATION_FILE = "googleab9fc45267cc3e75.html"
VISIT_LOG_PATH = os.path.join(app.root_path, "data", "visit_log.csv")
VISIT_LOG_FIELDS = ["timestamp", "visitor_id", "path", "method"]
BOTOLA_SEASONS_PATH = os.path.join(app.root_path, "data", "botola_seasons.json")
WAC_CUP_TITLES = [
    "1969/70",
    "1977/78",
    "1978/79",
    "1980/81",
    "1988/89",
    "1993/94",
    "1996/97",
    "1997/98",
    "2000/01"
]
WAC_AFRICAN_TROPHIES = [
    {"season": "1992", "competition": "Ligue des Champions CAF"},
    {"season": "2017", "competition": "Ligue des Champions CAF"},
    {"season": "2021/22", "competition": "Ligue des Champions CAF"},
    {"season": "2002", "competition": "Coupe d'Afrique des vainqueurs de coupe"},
    {"season": "2018", "competition": "Super Coupe Africaine"}
]
WAC_ARAB_TROPHIES = [
    {"season": "1989", "competition": "Coupe Arabe des Clubs Champions"},
    {"season": "1992", "competition": "Super Coupe Arabe"}
]
WAC_INTERCONTINENTAL_TROPHIES = [
    {"season": "1994", "competition": "Coupe Afro-Asiatique"}
]
WAC_LEGENDS = [
    {
        "name": "Badou Ezzaki",
        "period": "1977-1986",
        "role": "Gardien",
        "highlight": "Ballon d'Or Africain",
        "image": "https://cdn.al-ain.com/lg/images/2023/11/11/100-180914-badou-zaki-wydad-bounou-2.jpeg",
        "image_source": "Al Ain"
    },
    {
        "name": "Fakhreddine Rajhy",
        "period": "1982-1995",
        "role": "Ailier",
        "highlight": "Joueur le plus cape",
        "image": "https://pbs.twimg.com/media/DsYi3nQWsAAssxE.jpg",
        "image_source": "Archive relayee en ligne"
    },
    {
        "name": "Rachid Daoudi",
        "period": "1987-2003",
        "role": "Milieu",
        "highlight": "Canonnier du Wydad",
        "image": "https://www.bladi.net/img/cache-vignettes/L800xH500/arton14136-fc9ce.webp",
        "image_source": "Bladi"
    },
    {
        "name": "Larbi Ahardane",
        "period": "1970-1983",
        "role": "Defenseur",
        "highlight": "Champion d'Afrique avec le Maroc",
        "image": "",
        "local_image": "larbi-ahardane-correct.jpg",
        "image_source": "Archive locale"
    },
    {
        "name": "Moussa N'daw",
        "period": "1988-1992",
        "role": "Attaquant",
        "highlight": "Meilleur joueur etranger au Maroc",
        "image": "https://assets.kooora.com/images/v3/kooora_1238505_1/koo_454013.jpg",
        "image_source": "Kooora"
    },
    {
        "name": "Mohamed Benchrifa",
        "period": "1996-2006",
        "role": "Attaquant",
        "highlight": "Deuxieme canonnier du WAC",
        "image": "",
        "local_image": "benchrifa.jpg",
        "photo_fit": "contain",
        "image_source": "Archive locale"
    },
    {
        "name": "Noureddine Naybet",
        "period": "1989-1993",
        "role": "Defenseur",
        "highlight": "Le plus cape de la selection marocaine",
        "image": "https://al3omk.com/wp-content/uploads/2020/05/100814491_172527897513703_5194869335146889216_n.jpg",
        "image_source": "Al3omk"
    }
]
CLUB_DISPLAY_ALIASES = {
    "wydad athletic club": "Wydad Athletic Club",
    "wac casablanca": "Wydad Athletic Club",
    "wydad athletic club casablanca": "Wydad Athletic Club",
    "raja club athletic": "Raja Club Athletic",
    "raja casablanca": "Raja Club Athletic",
    "forces armees royales": "AS FAR",
    "as forces armees royales": "AS FAR",
    "as forces armees royales rabat": "AS FAR",
    "as forces armees royales": "AS FAR",
    "far rabat": "AS FAR",
    "far": "AS FAR",
    "maghreb association sportive": "MAS de Fès",
    "maghreb association sportive fes": "MAS de Fès",
    "mas fes": "MAS de Fès",
    "mas": "MAS de Fès",
    "kenitra athletic club": "Kenitra Athletic Club",
    "kenitra athletic club": "Kenitra Athletic Club",
    "kac kenitra": "Kenitra Athletic Club",
    "moghreb athletic de tetouan": "Moghreb Athletic de Tetouan",
    "maghreb athletic tetouan": "Moghreb Athletic de Tetouan",
    "ma tetouan": "Moghreb Athletic de Tetouan",
    "sporting club chabab de mohammedia": "SCC Mohammedia",
    "scc mohammedia": "SCC Mohammedia",
    "sccm": "SCC Mohammedia",
    "fath union sport": "Fath Union Sport",
    "fus rabat": "Fath Union Sport",
    "club omnisport de meknes": "COD Meknes",
    "club omnisports de meknes": "COD Meknes",
    "cod meknes": "COD Meknes",
    "mouloudia club oujda": "Mouloudia Club Oujda",
    "mco oujda": "Mouloudia Club Oujda",
    "renaissance sportive berkane": "RS Berkane",
    "renaissance sportive de berkane": "RS Berkane",
    "rs berkane": "RS Berkane",
    "hassania union sport agadir": "HUS Agadir",
    "hus agadir": "HUS Agadir",
    "olympique club de khouribga": "OC Khouribga",
    "oc khouribga": "OC Khouribga",
    "ock": "OC Khouribga",
    "olympique casablanca": "Olympique Casablanca",
    "kawkab athletic club de marrakech": "KAC Marrakech",
    "kawkab athletique club de marrakech": "KAC Marrakech",
    "kac marrakech": "KAC Marrakech",
    "ittihad riadi de tanger": "IR Tanger",
    "ir tanger": "IR Tanger",
    "renaissance sportive de settat": "RS Settat",
    "association des douanes marocaines": "Association des Douanes Marocaines",
    "association des douanes marocaines casablanca": "Association des Douanes Marocaines",
    "association des douanes marocaines casablnca": "Association des Douanes Marocaines",
    "raja beni mellal": "Raja Beni Mellal",
    "etoile jeunesse sportive casablanca": "Etoile Jeunesse Sportive Casablanca"
}
PRE_INDEPENDENCE_CHAMPIONS = [
    ("1915/16", "CA Casablanca"),
    ("1916/17", "US Marocaine"),
    ("1917/18", "US Marocaine"),
    ("1918/19", "US Marocaine"),
    ("1919/20", "US Marocaine"),
    ("1920/21", "Olympique Marocain"),
    ("1921/22", "US de Meknes"),
    ("1922/23", "Olympique Marocain"),
    ("1923/24", "Olympique Marocain"),
    ("1924/25", "US Fes"),
    ("1925/26", "US Fes"),
    ("1926/27", "US Athletique"),
    ("1927/28", "Stade Marocain"),
    ("1928/29", "US Athletique"),
    ("1929/30", "Olympique Marocain"),
    ("1930/31", "Stade Marocain"),
    ("1931/32", "US Marocaine"),
    ("1932/33", "US Marocaine"),
    ("1933/34", "US Marocaine"),
    ("1934/35", "US Marocaine"),
    ("1935/36", "Olympique Marocain"),
    ("1936/37", "Olympique Marocain"),
    ("1937/38", "US Marocaine"),
    ("1938/39", "US Marocaine"),
    ("1939/40", "US Marocaine"),
    ("1940/41", "US Marocaine"),
    ("1941/42", "US Marocaine"),
    ("1943/44", "Stade Marocain"),
    ("1944/45", "Racing Casablanca"),
    ("1945/46", "US Marocaine"),
    ("1946/47", "US Marocaine"),
    ("1951/52", "US Marocaine"),
    ("1952/53", "SA Marrakech"),
    ("1953/54", "Racing Casablanca")
]

# --- Authentication Logic ---
ADMIN_USER = os.environ.get("ADMIN_USER", "admin")
DEFAULT_ADMIN_PASSWORD_HASH = "scrypt:32768:8:1$WPog1wAr2PKSAgJk$7a97d1f1cb700c5368db9e3d9163055ea6cf84b0e097eeff58ef1c0601c10a14d681e0b83eca4e90462c316c79a77468ae74f9a56dec5767926a62ac11136b9d"
ADMIN_PASSWORD_HASH = os.environ.get("ADMIN_PASSWORD_HASH", DEFAULT_ADMIN_PASSWORD_HASH)

def get_visitor_id():
    forwarded_for = request.headers.get("X-Forwarded-For", "")
    ip_address = forwarded_for.split(",")[0].strip() or request.remote_addr or "unknown"
    user_agent = request.headers.get("User-Agent", "")
    salt = app.secret_key or "visit-counter"
    raw_id = f"{salt}|{ip_address}|{user_agent}"
    return hashlib.sha256(raw_id.encode("utf-8")).hexdigest()[:16]

def get_db_connection():
    if not DATABASE_URL or psycopg2 is None:
        return None
    try:
        return psycopg2.connect(DATABASE_URL, sslmode="require")
    except Exception as exc:
        app.logger.warning("Could not connect to visit database: %s", exc)
        return None

def write_visit_to_csv(visit_row):
    os.makedirs(os.path.dirname(VISIT_LOG_PATH), exist_ok=True)
    file_exists = os.path.exists(VISIT_LOG_PATH)

    with open(VISIT_LOG_PATH, "a", newline="", encoding="utf-8") as log_file:
        writer = csv.DictWriter(log_file, fieldnames=VISIT_LOG_FIELDS)
        if not file_exists:
            writer.writeheader()
        writer.writerow(visit_row)

def track_visit():
    if request.method != "GET":
        return

    excluded_prefixes = (
        "/admin",
        "/login",
        "/logout",
        "/static",
        "/favicon.ico",
        "/.env",
        "/.git",
        "/wp-",
        "/xmlrpc.php",
        "/robots.txt",
        "/sitemap.xml",
        "/google",
    )
    if request.path.startswith(excluded_prefixes):
        return

    visit_row = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "visitor_id": get_visitor_id(),
        "path": request.path,
        "method": request.method
    }

    conn = get_db_connection()
    if conn:
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        insert into public.visit_log (timestamp, visitor_id, path, method)
                        values (%s, %s, %s, %s)
                        """,
                        (
                            visit_row["timestamp"],
                            visit_row["visitor_id"],
                            visit_row["path"],
                            visit_row["method"],
                        ),
                    )
            return
        except Exception as exc:
            app.logger.warning("Could not write visit to database: %s", exc)
        finally:
            conn.close()

    write_visit_to_csv(visit_row)

def get_visit_stats():
    stats = {
        "today_views": 0,
        "today_visitors": 0,
        "month_views": 0,
        "month_visitors": 0,
        "total_views": 0,
        "total_visitors": 0,
        "top_pages": []
    }

    conn = get_db_connection()
    if conn:
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        select count(*), count(distinct visitor_id)
                        from public.visit_log
                        where timestamp::date = current_date
                        """
                    )
                    stats["today_views"], stats["today_visitors"] = cur.fetchone()

                    cur.execute(
                        """
                        select count(*), count(distinct visitor_id)
                        from public.visit_log
                        where timestamp >= date_trunc('month', current_date)
                        """
                    )
                    stats["month_views"], stats["month_visitors"] = cur.fetchone()

                    cur.execute(
                        """
                        select count(*), count(distinct visitor_id)
                        from public.visit_log
                        """
                    )
                    stats["total_views"], stats["total_visitors"] = cur.fetchone()

                    cur.execute(
                        """
                        select path, count(*) as views
                        from public.visit_log
                        group by path
                        order by views desc
                        limit 8
                        """
                    )
                    stats["top_pages"] = cur.fetchall()
            return stats
        except Exception as exc:
            app.logger.warning("Could not read visit stats from database: %s", exc)
        finally:
            conn.close()

    if not os.path.exists(VISIT_LOG_PATH):
        return stats

    today = date.today()
    current_month = today.strftime("%Y-%m")
    today_visitors = set()
    month_visitors = set()
    total_visitors = set()
    pages = Counter()

    with open(VISIT_LOG_PATH, newline="", encoding="utf-8") as log_file:
        reader = csv.DictReader(log_file)
        for row in reader:
            try:
                visited_at = datetime.fromisoformat(row.get("timestamp", "")).date()
            except ValueError:
                continue

            visitor_id = row.get("visitor_id", "")
            path = row.get("path", "/")

            stats["total_views"] += 1
            total_visitors.add(visitor_id)
            pages[path] += 1

            if visited_at == today:
                stats["today_views"] += 1
                today_visitors.add(visitor_id)

            if visited_at.strftime("%Y-%m") == current_month:
                stats["month_views"] += 1
                month_visitors.add(visitor_id)

    stats["today_visitors"] = len(today_visitors)
    stats["month_visitors"] = len(month_visitors)
    stats["total_visitors"] = len(total_visitors)
    stats["top_pages"] = pages.most_common(8)
    return stats

def load_botola_seasons():
    if not os.path.exists(BOTOLA_SEASONS_PATH):
        return []

    with open(BOTOLA_SEASONS_PATH, encoding="utf-8") as seasons_file:
        seasons = json.load(seasons_file)

    for season in seasons:
        season["championDisplay"] = canonical_club_name(season.get("champion", ""))
        for row in season.get("table", []):
            row["clubDisplay"] = canonical_club_name(row.get("club") or row.get("code", ""))
        if season.get("wac"):
            season["wac"]["clubDisplay"] = canonical_club_name(season["wac"].get("club", ""))
    return recalculate_champion_title_counts(seasons)

def is_wac_name(team_name):
    return canonical_club_name(team_name) == "Wydad Athletic Club"

def normalize_name(team_name):
    value = unicodedata.normalize("NFKD", str(team_name or ""))
    value = value.encode("ascii", "ignore").decode("ascii")
    return " ".join(
        "".join(char.lower() if char.isalnum() else " " for char in value).split()
    )

def canonical_club_name(team_name):
    normalized = normalize_name(team_name)
    return CLUB_DISPLAY_ALIASES.get(normalized, str(team_name or "Non renseigne").strip())

def season_start(label):
    try:
        return int(str(label).split("/")[0])
    except (TypeError, ValueError):
        return 0

def recalculate_champion_title_counts(botola_seasons):
    counts = Counter()
    for _, champion in PRE_INDEPENDENCE_CHAMPIONS:
        counts[canonical_club_name(champion)] += 1

    for season in botola_seasons:
        season.pop("championTitleCount", None)
        for row in season.get("table", []):
            row.pop("championTitleCount", None)

    for season in sorted(botola_seasons, key=lambda item: season_start(item.get("label"))):
        champion = canonical_club_name(season.get("champion", ""))
        if not champion:
            continue

        counts[champion] += 1
        season["championTitleCount"] = counts[champion]

        for row in season.get("table", []):
            if row.get("rank") == 1:
                row["championTitleCount"] = counts[champion]
                row["clubDisplay"] = champion
                break

    return botola_seasons

def trophy_competitions(trophies, icons):
    grouped = {}
    for trophy in trophies:
        competition = trophy["competition"]
        grouped.setdefault(competition, {
            "competition": competition,
            "icon": icons.get(competition, "trophy"),
            "titles": []
        })
        grouped[competition]["titles"].append(trophy)

    return sorted(grouped.values(), key=lambda item: item["competition"])

def build_league_honours(botola_seasons):
    season_rows = []
    seen_pre_seasons = {
        season.get("label")
        for season in botola_seasons
        if season.get("preIndependence")
    }

    for season, champion in PRE_INDEPENDENCE_CHAMPIONS:
        if season not in seen_pre_seasons:
            season_rows.append({
                "season": season,
                "champion": canonical_club_name(champion),
                "preIndependence": True
            })

    for season in botola_seasons:
        season_rows.append({
            "season": season.get("label", ""),
            "champion": canonical_club_name(season.get("champion", "")),
            "preIndependence": bool(season.get("preIndependence"))
        })

    clubs = {}
    for row in sorted(season_rows, key=lambda item: season_start(item["season"])):
        champion = row["champion"]
        clubs.setdefault(champion, {"club": champion, "count": 0, "seasons": []})
        clubs[champion]["count"] += 1
        clubs[champion]["seasons"].append(row["season"])

    return sorted(
        clubs.values(),
        key=lambda item: (-item["count"], item["club"])
    )

def build_wac_honours(botola_seasons):
    league_titles = []
    cup_finals = []

    for season in botola_seasons:
        label = season.get("label", "")
        if is_wac_name(season.get("champion")):
            league_titles.append({
                "season": label,
                "competition": "Botola",
                "detail": season.get("wac", {})
            })

        cup_runner_up = season.get("cupRunnerUp", "")
        if is_wac_name(cup_runner_up):
            cup_finals.append({
                "season": label,
                "competition": "Coupe du Trone",
                "winner": season.get("cupWinner", "")
            })

    cup_titles = [
        {"season": season, "competition": "Coupe du Trone"}
        for season in WAC_CUP_TITLES
    ]
    national_trophies = [
        *league_titles,
        *cup_titles
    ]
    african_icons = {
        "Ligue des Champions CAF": "img-caf-champions-league",
        "Coupe d'Afrique des vainqueurs de coupe": "trophy",
        "Super Coupe Africaine": "badge-check"
    }
    arab_icons = {
        "Coupe Arabe des Clubs Champions": "sparkles",
        "Super Coupe Arabe": "badge-check"
    }
    intercontinental_icons = {
        "Coupe Afro-Asiatique": "globe-2"
    }
    national_icons = {
        "Botola": "img-botola",
        "Coupe du Trone": "img-coupe-trone"
    }

    return {
        "league_titles": league_titles,
        "cup_titles": cup_titles,
        "cup_finals": cup_finals,
        "national_competitions": trophy_competitions(national_trophies, national_icons),
        "african_competitions": trophy_competitions(WAC_AFRICAN_TROPHIES, african_icons),
        "arab_competitions": trophy_competitions(WAC_ARAB_TROPHIES, arab_icons),
        "intercontinental_competitions": trophy_competitions(WAC_INTERCONTINENTAL_TROPHIES, intercontinental_icons),
        "total_league_titles": len(league_titles),
        "total_cup_titles": len(cup_titles),
        "total_cup_finals": len(cup_finals),
        "total_african_trophies": len(WAC_AFRICAN_TROPHIES),
        "total_arab_trophies": len(WAC_ARAB_TROPHIES),
        "total_intercontinental_trophies": len(WAC_INTERCONTINENTAL_TROPHIES)
    }

app.before_request(track_visit)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if ADMIN_PASSWORD_HASH and username == ADMIN_USER and check_password_hash(ADMIN_PASSWORD_HASH, password):
            session['logged_in'] = True
            return redirect(url_for('admin'))
        else:
            flash("Identifiants incorrects. Veuillez réessayer.")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('index'))

@app.route(f"/{GOOGLE_VERIFICATION_FILE}")
def google_site_verification():
    return Response(
        f"google-site-verification: {GOOGLE_VERIFICATION_FILE}",
        mimetype="text/plain",
    )

@app.route("/robots.txt")
def robots_txt():
    lines = [
        "User-agent: *",
        "Disallow: /admin",
        "Disallow: /login",
        "Disallow: /logout",
        f"Sitemap: {SITE_URL}/sitemap.xml",
        "",
    ]
    return Response("\n".join(lines), mimetype="text/plain")

@app.route("/sitemap.xml")
def sitemap_xml():
    pages = [
        ("/", "daily", "1.0"),
        ("/matchs", "weekly", "0.9"),
        ("/players", "weekly", "0.8"),
        ("/stats", "weekly", "0.8"),
        ("/legends", "monthly", "0.7"),
        ("/trophies", "monthly", "0.7"),
        ("/formations", "monthly", "0.6"),
    ]
    xml = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for path, changefreq, priority in pages:
        xml.extend([
            "  <url>",
            f"    <loc>{SITE_URL}{path}</loc>",
            f"    <changefreq>{changefreq}</changefreq>",
            f"    <priority>{priority}</priority>",
            "  </url>",
        ])
    xml.append("</urlset>")
    return Response("\n".join(xml), mimetype="application/xml")

@app.route('/')
def index():
    # Read formation data
    df = pd.read_csv('data/Wac_Formation.csv', encoding="utf-8", sep=";")
    df = df.rename(columns={
        "saison": "Saison",
        "dateMatch": "Date",
        "adversaire": "Equipe"
    })
    data = df.to_dict(orient='records')

    # Load the latest match for the "Dernière Mise à jour" section
    latest_match = None
    try:
        df_m = pd.read_csv("data/Test_import.csv", encoding="utf-8", sep=";").fillna("")
        df_m["DateMatch"] = pd.to_datetime(df_m["DateMatch"], errors="coerce")
        df_m = df_m.dropna(subset=["DateMatch"]).sort_values("DateMatch", ascending=False)
        if not df_m.empty:
            row = df_m.iloc[0]
            latest_match = {
                "equipe": row.get("Equipe", ""),
                "competition": row.get("Competition", ""),
                "saison": row.get("Saison", ""),
                "date": row["DateMatch"].strftime("%d/%m/%Y"),
                "score": row.get("Score", ""),
                "lieu": row.get("Lieu", ""),
                "journee": row.get("Journee", ""),
            }
    except Exception:
        latest_match = None

    return render_template('index.html', data=data, latest_match=latest_match)

@app.route('/matchs')
def matchs():
    df = pd.read_csv("data/Test_import.csv", encoding="utf-8", sep=";").fillna("")

    df["Equipe"] = df["Equipe"].astype(str).str.strip().str.replace("/", "-")
    df["Journee"] = df["Journee"].astype(str).str.strip().str.replace("/", "-")
    df["match_key"] = (
        df["Saison"].astype(str).str.replace("/", "-")
        + "_"
        + df["DateMatch"].astype(str)
        + "_"
        + df["Journee"]
        + "_"
        + df["Equipe"]
    )
    df["_row_order"] = range(len(df))
    df["_date_sort"] = pd.to_datetime(df["DateMatch"], errors="coerce")
    df["_season_sort"] = pd.to_numeric(
        df["Saison"].astype(str).str.extract(r"(\d{4})")[0],
        errors="coerce"
    ).fillna(0)
    df = df.sort_values(
        ["_season_sort", "_date_sort", "_row_order"],
        ascending=[False, False, True],
        na_position="last"
    ).drop(columns=["_row_order", "_date_sort", "_season_sort"])
    matches = df.to_dict(orient="records")
    return render_template("matchs.html", matches=matches)

@app.route('/stats')
def stats():
    df = pd.read_csv("data/Test_import.csv", encoding="utf-8", sep=";").fillna("")
    df = df.rename(columns={
        "Saison": "Saison",
        "DateMatch": "Date",
        "Equipe": "Equipe"
    })
    df["Equipe"] = df["Equipe"].apply(canonical_club_name)
    matches = df.to_dict(orient="records")
    return render_template("stats.html", matches=matches, botola_seasons=load_botola_seasons())

@app.route("/trophies")
def trophies():
    botola_seasons = load_botola_seasons()
    honours = build_wac_honours(botola_seasons)
    return render_template(
        "trophies.html",
        botola_seasons=botola_seasons,
        honours=honours,
        league_honours=build_league_honours(botola_seasons)
    )

@app.route("/legends")
def legends():
    return render_template("legends.html", legends=WAC_LEGENDS)


@app.route("/formations")
def formations():
    df = pd.read_csv("data/Wac_Formation.csv", encoding="utf-8-sig")
    formations = df.to_dict(orient="records")
    return render_template("formations.html", formations=formations)

@app.route("/formation/<match_key>")
def formation(match_key):
    df = pd.read_csv("data/Wac_Formation.csv", encoding="utf-8", sep=";")
    df = df.rename(columns={
        "saison": "Saison",
        "dateMatch": "Date",
        "adversaire": "Equipe"
    })
    
    # Normalization for matching
    df["Equipe"] = df["Equipe"].astype(str).str.strip().str.replace("/", "-")
    df["Journee"] = df["Journee"].astype(str).str.strip().str.replace("/", "-")
    
    df["match_key"] = (
        df["Saison"].astype(str).str.replace("/", "-")
        + "_"
        + df["Date"].astype(str)
        + "_"
        + df["Journee"]
        + "_"
        + df["Equipe"]
    )

    formation_match = df[df["match_key"] == match_key]

    titulaires = formation_match[
        formation_match["Titulaire"].astype(str).str.contains("Tit", na=False)
    ].fillna(0).to_dict(orient="records")

    remplacants = formation_match[
        formation_match["Titulaire"].astype(str).str.contains("Remp", na=False)
    ].fillna(0).to_dict(orient="records")

    return render_template(
        "formations.html",
        titulaires=titulaires,
        remplacants=remplacants
    )

@app.route("/players")
def players():
    df = pd.read_csv("data/Wac_Formation.csv", encoding="utf-8", sep=";")
    df = df.rename(columns={"saison": "Saison", "dateMatch": "Date", "adversaire": "Equipe", "lieu": "Lieu"})
    
    # Strip whitespace and normalize slashes
    df["Saison"] = df["Saison"].astype(str).str.strip().str.replace("/", "-")
    df["Equipe"] = df["Equipe"].astype(str).str.strip().str.replace("/", "-")
    df["Journee"] = df["Journee"].astype(str).str.strip().str.replace("/", "-")
    
    df["match_key"] = (
        df["Saison"]
        + "_"
        + df["Date"].astype(str)
        + "_"
        + df["Journee"]
        + "_"
        + df["Equipe"]
    )
    df = df.fillna(0)

    df_matchs = pd.read_csv("data/Test_import.csv", encoding="utf-8", sep=";").fillna("")
    df_matchs = df_matchs.rename(columns={"Saison": "Saison", "DateMatch": "Date", "Equipe": "Equipe"})
    
    # Strip whitespace here too, and normalize slashes (same as df above)
    df_matchs["Equipe"] = df_matchs["Equipe"].astype(str).str.strip().str.replace("/", "-")
    
    df_matchs["match_key"] = (
        df_matchs["Saison"].astype(str).str.replace("/", "-")
        + "_"
        + df_matchs["Date"].astype(str)
        + "_"
        + df_matchs["Journee"].astype(str)
        + "_"
        + df_matchs["Equipe"].astype(str)
    )

    # Merge to get Competition
    df = pd.merge(df, df_matchs[['match_key', 'Competition']], on='match_key', how='left')
    df['Competition'] = df['Competition'].fillna("Inconnu")

    # Clean numeric columns to ensure JS gets proper numbers
    for col in ["Buts", "CartonJaune", "CartonRouge", "Minutes", "TAB_Marque", "TAB_Rate"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    # Force string types and trim
    for col in ["Joueur", "Saison", "Equipe", "Journee", "Competition"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()

    raw_data = df.to_dict(orient="records")

    return render_template(
        "players.html",
        raw_data=raw_data
    )

@app.route("/admin")
@login_required
def admin():
    # Load unique teams and players for autocomplete
    try:
        df_m = pd.read_csv("data/Test_import.csv", sep=";", encoding="utf-8").fillna("")
        equipes = sorted(df_m['Equipe'].dropna().unique().tolist())
        journees = sorted(df_m['Journee'].dropna().unique().tolist(), key=lambda x: str(x))
        
        # Get all matches for the management list
        df_m["Equipe"] = df_m["Equipe"].astype(str).str.strip().str.replace("/", "-")
        df_m["Journee"] = df_m["Journee"].astype(str).str.strip().str.replace("/", "-")
        df_m["match_key"] = (
            df_m["Saison"].astype(str).str.replace("/", "-")
            + "_"
            + df_m["DateMatch"].astype(str)
            + "_"
            + df_m["Journee"]
            + "_"
            + df_m["Equipe"]
        )
        recent_matches = df_m.sort_values("DateMatch", ascending=False).to_dict(orient="records")
    except:
        equipes = []
        journees = []
        recent_matches = []
        
    try:
        df_f = pd.read_csv("data/Wac_Formation.csv", sep=";", encoding="utf-8")
        joueurs = sorted(df_f['Joueur'].dropna().unique().tolist())
    except:
        joueurs = []
        
    visit_stats = get_visit_stats()
    return render_template(
        "admin.html",
        equipes=equipes,
        joueurs=joueurs,
        journees=journees,
        recent_matches=recent_matches,
        visit_stats=visit_stats
    )

@app.route("/admin/add_match", methods=["POST"])
@login_required
def add_match():
    try:
        # 1. Get Match Data
        saison = request.form.get("saison")
        date = request.form.get("date")
        journee = request.form.get("journee")
        equipe = request.form.get("equipe")
        competition = request.form.get("competition")
        lieu = request.form.get("lieu")
        score = request.form.get("score")
        score_tab = request.form.get("score_tab")
        if score_tab:
            score = f"{score} ({score_tab})"

        # Handle Update: Delete old entries if editing
        old_key = request.form.get("old_match_key")
        if old_key:
            # Delete from Test_import
            df_m = pd.read_csv("data/Test_import.csv", sep=";", encoding="utf-8").fillna("")
            df_m["temp_key"] = (df_m["Saison"].astype(str).str.replace("/", "-") + "_" + df_m["DateMatch"].astype(str) + "_" + df_m["Journee"].astype(str) + "_" + df_m["Equipe"].astype(str))
            df_m = df_m[df_m["temp_key"] != old_key].drop(columns=["temp_key"])
            df_m.to_csv("data/Test_import.csv", index=False, sep=";", encoding="utf-8")
            
            # Delete from Wac_Formation
            df_f = pd.read_csv("data/Wac_Formation.csv", sep=";", encoding="utf-8")
            df_f["temp_key"] = (df_f["saison"].astype(str).str.replace("/", "-") + "_" + df_f["dateMatch"].astype(str) + "_" + df_f["Journee"].astype(str) + "_" + df_f["adversaire"].astype(str))
            df_f = df_f[df_f["temp_key"] != old_key].drop(columns=["temp_key"])
            df_f.to_csv("data/Wac_Formation.csv", index=False, sep=";", encoding="utf-8")

        # 1. Save Match Data
        new_match = pd.DataFrame([{
            "Saison": saison,
            "DateMatch": date,
            "Journee": journee,
            "Equipe": equipe,
            "Competition": competition,
            "Lieu": lieu,
            "Score": score
        }])
        test_import_path = "data/Test_import.csv"
        new_match.to_csv(test_import_path, mode='a', header=not os.path.exists(test_import_path), index=False, sep=";", encoding="utf-8")

        # 2. Save Players Data
        players = request.form.getlist("player_name[]")
        titulaires = request.form.getlist("player_titulaire[]")
        minutes = request.form.getlist("player_minutes[]")
        buts = request.form.getlist("player_buts[]")
        jaunes = request.form.getlist("player_jaunes[]")
        rouges = request.form.getlist("player_rouges[]")
        tab_marques = request.form.getlist("player_tab_marque[]")
        tab_rates = request.form.getlist("player_tab_rate[]")

        formation_records = []
        for i in range(len(players)):
            if players[i]:
                formation_records.append({
                    "saison": saison,
                    "dateMatch": date,
                    "Journee": journee,
                    "adversaire": equipe,
                    "lieu": lieu,
                    "Joueur": players[i],
                    "Titulaire": titulaires[i],
                    "Minutes": minutes[i] or "0",
                    "Buts": buts[i] or "0",
                    "CartonJaune": jaunes[i] or "0",
                    "CartonRouge": rouges[i] or "0",
                    "TAB_Marque": tab_marques[i] if i < len(tab_marques) else 0,
                    "TAB_Rate": tab_rates[i] if i < len(tab_rates) else 0
                })

        if formation_records:
            df_formation = pd.DataFrame(formation_records)
            formation_path = "data/Wac_Formation.csv"
            df_formation.to_csv(formation_path, mode='a', header=not os.path.exists(formation_path), index=False, sep=";", encoding="utf-8")

        msg = "Match mis à jour avec succès !" if old_key else "Match ajouté avec succès !"
        return redirect(url_for("admin", success=msg))
    except Exception as e:
        return str(e)

@app.route("/admin/import_csv", methods=["POST"])
@login_required
def import_csv():
    try:
        file_type = request.form.get("file_type") # 'matches' or 'formations'
        file = request.files['file']
        
        if file:
            filename = file.filename
            temp_path = os.path.join("data", "temp_" + filename)
            file.save(temp_path)
            
            target_file = "data/Test_import.csv" if file_type == "matches" else "data/Wac_Formation.csv"
            
            # Read temp and append to main
            df_new = pd.read_csv(temp_path, sep=";", encoding="utf-8")
            df_new.to_csv(target_file, mode='a', header=False, index=False, sep=";", encoding="utf-8")
            
            os.remove(temp_path)
            return redirect(url_for("admin", success=f"Fichier {file_type} importé avec succès !"))
            
        return redirect(url_for("admin", error="Aucun fichier sélectionné."))
    except Exception as e:
        return str(e)

@app.route("/admin/delete_match/<match_key>")
@login_required
def delete_match(match_key):
    try:
        # 1. Delete from Test_import.csv
        df_m = pd.read_csv("data/Test_import.csv", sep=";", encoding="utf-8").fillna("")
        df_m["temp_key"] = (
            df_m["Saison"].astype(str).str.replace("/", "-")
            + "_"
            + df_m["DateMatch"].astype(str)
            + "_"
            + df_m["Journee"].astype(str)
            + "_"
            + df_m["Equipe"].astype(str)
        )
        df_m = df_m[df_m["temp_key"] != match_key].drop(columns=["temp_key"])
        df_m.to_csv("data/Test_import.csv", index=False, sep=";", encoding="utf-8")

        # 2. Delete from Wac_Formation.csv
        df_f = pd.read_csv("data/Wac_Formation.csv", sep=";", encoding="utf-8")
        df_f["temp_key"] = (
            df_f["saison"].astype(str).str.replace("/", "-")
            + "_"
            + df_f["dateMatch"].astype(str)
            + "_"
            + df_f["Journee"].astype(str)
            + "_"
            + df_f["adversaire"].astype(str)
        )
        df_f = df_f[df_f["temp_key"] != match_key].drop(columns=["temp_key"])
        df_f.to_csv("data/Wac_Formation.csv", index=False, sep=";", encoding="utf-8")

        return redirect(url_for("admin", success="Match supprimé avec succès."))
    except Exception as e:
        return str(e)
@app.route("/admin/get_match/<match_key>")
@login_required
def get_match(match_key):
    try:
        df_m = pd.read_csv("data/Test_import.csv", sep=";", encoding="utf-8").fillna("")
        df_m["temp_key"] = (df_m["Saison"].astype(str).str.replace("/", "-") + "_" + df_m["DateMatch"].astype(str) + "_" + df_m["Journee"].astype(str) + "_" + df_m["Equipe"].astype(str))
        match_data = df_m[df_m["temp_key"] == match_key].to_dict(orient="records")
        
        if not match_data:
            return {"error": "Match non trouvé"}, 404
            
        df_f = pd.read_csv("data/Wac_Formation.csv", sep=";", encoding="utf-8")
        df_f["temp_key"] = (df_f["saison"].astype(str).str.replace("/", "-") + "_" + df_f["dateMatch"].astype(str) + "_" + df_f["Journee"].astype(str) + "_" + df_f["adversaire"].astype(str))
        players_data = df_f[df_f["temp_key"] == match_key].to_dict(orient="records")
        
        return {
            "match": match_data[0],
            "players": players_data
        }
    except Exception as e:
        return {"error": str(e)}, 500

if __name__ == '__main__':
    app.run(
        debug=os.environ.get("FLASK_DEBUG", "0") == "1",
        host='0.0.0.0'
    )

import json
import re
import time
import xml.etree.ElementTree as ET

import requests

from config import Config

USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36")
DEFAULT_COVER = "https://kissfm.com.br/wp-content/themes/KISSFM/img/logofot.png"
TRITON_API_URL = "https://np.tritondigital.com/public/nowplaying?mountName=RADIO_KISSFM&numberToFetch=6&eventType=track"
ITUNES_API_URL = "https://itunes.apple.com/search"
CONF_FILE = "kiss_db.json"

conf = Config()


class ForumScraper:
    def __init__(self, url, cookie):
        self.url = url
        self.ses = requests.Session()
        self.ses.headers.update({"user-agent": USER_AGENT})
        self.ses.cookies.update({"234_user" if conf.IS_DEMO else "xf_user": cookie})
        self._authorize()

    def _authorize(self):
        response = self.ses.get(f"{self.url}/help", timeout=7)
        response.raise_for_status()
        # print(response.text[0:1500])
        if 'data-logged-in="true"' not in response.text:
            raise ValueError("Erro: Não logado no fórum.")
        self._xfToken = re.search(r'name="_xfToken" value="([^"]+)"', response.text).group(1)

    def reply(self, thread_id, message):
        url = f"{self.url}/threads/{thread_id}/add-reply"
        payload = {"_xfToken": self._xfToken, "message_html": message}
        self.ses.post(url, data=payload, timeout=7)


def load_db():
    try:
        with open(CONF_FILE, 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        return {"stamp": 0, "position": 500}


def save_db(data):
    with open(CONF_FILE, 'w') as file:
        json.dump(data, file, indent=2)


def set_position(position: int):
    ldb = load_db()
    ldb["position"] = position
    save_db(ldb)


def check_timestamp(prev_timestamp):
    current_time = int(time.time())
    try:
        timestamp = int(prev_timestamp)
    except ValueError:
        return 0
    time_difference = current_time - timestamp
    if 0 < time_difference <= 30:
        remaining_seconds = 30 - time_difference
        return remaining_seconds
    else:
        return 0


def get_playlist():
    try:
        req = requests.get(TRITON_API_URL)
        req.raise_for_status()
        root = ET.fromstring(req.text)
        tracks = []
        for nowplaying_info in root.findall(".//nowplaying-info"):
            timestamp = nowplaying_info.get("timestamp")
            title = ""
            artist = ""
            for prop in nowplaying_info.findall("property"):
                if prop.get("name") == "cue_title":
                    title = prop.text or ""
                elif prop.get("name") == "track_artist_name":
                    artist = prop.text or ""
            tracks.append([timestamp, title, artist])
        return tracks

    except requests.RequestException as e:
        print(f"Erro na requisição: {e}")
        raise
    except ET.ParseError as e:
        print(f"Erro ao processar o XML: {e}")
        raise


def get_cover(title, artist):
    print(title, artist)
    try:
        params = {"term": f"{artist} {title}", "media": "music", "entity": "song", "limit": 1, "explicit": "Yes"}
        response = requests.get(ITUNES_API_URL, params=params)
        response.raise_for_status()
        results = response.json().get("results", [])
        if results:
            return results[0]["artworkUrl100"].replace("/100x100bb.jpg", "/500x500bb.jpg")
    except requests.RequestException:
        print("Aviso: Erro ao obter capa do álbum.")
    return DEFAULT_COVER


def format_response(position, data, cover):
    """Formata a mensagem para o fórum."""
    playlist = ""
    pos = position
    for _, artist, title in data[1:]:
        pos += 1
        playlist += (
            f"<p style='text-align: center;'><span style='font-size: 12px; color: rgb(124, 112, 107);'>{pos} - "
            f"<strong>{artist}</strong> -&nbsp;<strong>{title}</strong></span></p>")
    return (
        f"<p style='text-align: center;'>As 500 mais da <strong><span style='color: rgb(184, 49, 47);'>Kiss FM</span></strong></p>"
        f"<p style='text-align: center;'><strong>ouça AO VIVO:</strong></p>"
        f"<p style='text-align: center;'><a href='https://kissfm.com.br/aovivo/' target='_blank' rel='noopener'>"
        f"<strong>https://kissfm.com.br/ao-vivo/</strong></a></p><br>"
        f"<p style='text-align: center;'><strong><span style='font-size: 18px;'>POSIÇÃO N# {position}</span></strong></p>"
        f"<p style='text-align: center;'>Banda: <strong>{data[0][2]}</strong></p>"
        f"<p style='text-align: center;'>Música: <strong>{data[0][1]}</strong></p><br>"
        f"<p style='text-align: center;'><img src='{cover}' style='width: 250px;'></p>"
        f"<p style='text-align: center;'><br></p>"
        f"<p style='text-align: center;'><span style='font-size: 15px; color: rgb(124, 112, 107);'>anteriores:</span></p>"
        f"{playlist}")


def main(thread_id):
    forum_scraper = ForumScraper(conf.FORUM_URL, conf.COOKIE)
    db = load_db()
    playlist = get_playlist()
    track_timestamp, title, artist = playlist[0]
    if db["stamp"] != track_timestamp:
        print(track_timestamp, title, artist)
        position = db["position"] - 1
        cover = get_cover(title, artist)
        # anti-flood countdown
        time.sleep(check_timestamp(db["stamp"]))
        forum_scraper.reply(thread_id, format_response(position, playlist, cover))
        save_db({"stamp": track_timestamp, "position": position})
        if position == 1:
            print("Fim das 500 mais!")
            exit()

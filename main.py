import flet as ft
import yt_dlp
import os
import re
import threading
import time

C_BG = "#0d0d12"; C_SURFACE = "#1a1a22"; C_ACCENT = "#00d9ff"
C_TEXT = "#f0f0f5"; C_DIM = "#888890"; C_INK = "#000000"
C_ERROR = "#ff4455"; C_SUCCESS = "#00d47a"


def human_size(n):
    try: n = float(n)
    except (TypeError, ValueError): return "—"
    if n < 1024: return f"{int(n)} Б"
    for u in ("КБ", "МБ", "ГБ", "ТБ"):
        n /= 1024
        if n < 1024: return f"{n:.1f} {u}"
    return f"{n:.1f} ТБ"


def human_eta(sec):
    try: sec = int(sec)
    except (TypeError, ValueError): return "—"
    if sec < 60: return f"{sec} с"
    m, s = divmod(sec, 60)
    if m < 60: return f"{m}:{s:02d}"
    h, m = divmod(m, 60)
    return f"{h}:{m:02d}:{s:02d}"


def main(page: ft.Page):
    page.title = "FIT Download"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = C_BG
    page.padding = 16

    ddir = os.environ.get("FLET_APP_STORAGE_DATA") or os.path.expanduser("~")
    ddir = os.path.join(ddir, "FIT Download")
    os.makedirs(ddir, exist_ok=True)

    status = ft.Text("Готов к работе", color=C_DIM, size=11)
    url_input = ft.TextField(
        hint_text="Вставьте ссылку (YouTube, TikTok, VK…)",
        bgcolor=C_SURFACE, color=C_TEXT, border_color=C_SURFACE,
        cursor_color=C_ACCENT, text_size=14, content_padding=14,
        border_radius=12, expand=True,
    )
    st = {"format": "video", "quality": "720p", "downloading": False, "gen": 0}
    last_upd = {"t": 0.0}

    p_name = ft.Text("", color=C_TEXT, size=13, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS)
    p_bar = ft.ProgressBar(value=0, color=C_ACCENT, bgcolor=C_SURFACE)
    p_info = ft.Text("", color=C_DIM, size=12)
    p_box = ft.Container(
        content=ft.Column([p_name, p_bar, p_info], spacing=6), visible=False,
    )

    dl_list = ft.ListView(spacing=6, expand=True)

    def fmt_string():
        if st["format"] == "audio":
            return "bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio/best"
        lim = ""
        if st["quality"] == "480p": lim = "[height<=480]"
        elif st["quality"] == "720p": lim = "[height<=720]"
        elif st["quality"] == "1080p": lim = "[height<=1080]"
        return f"best{lim}[ext=mp4][acodec!=none][vcodec!=none]/best{lim}[acodec!=none][vcodec!=none]/best[acodec!=none][vcodec!=none]/best"

    def add_row(title, size, ok):
        icon = "✅" if ok else "❌"
        color = C_SUCCESS if ok else C_ERROR
        row = ft.Container(
            content=ft.Column([
                ft.Text(title, color=C_TEXT, size=13, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
                ft.Text(f"{icon} {human_size(size)}", color=color, size=11),
            ], spacing=2),
            bgcolor=C_SURFACE, border_radius=10,
            padding=ft.padding.symmetric(horizontal=12, vertical=8),
        )
        dl_list.controls.insert(0, row)
        try: page.update()
        except Exception: pass

    def worker(url, g):
        is_yt = "youtube.com" in url or "youtu.be" in url
        outtmpl = os.path.join(ddir, "%(title).120B [%(id)s].%(ext)s")

        def hook(d):
            if g != st["gen"]: return
            now = time.time()
            if d.get("status") == "downloading":
                if now - last_upd["t"] < 0.3: return
                last_upd["t"] = now
                total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                got = d.get("downloaded_bytes") or 0
                pct = (got / total) if total else 0
                spd = d.get("speed") or 0
                eta = d.get("eta") or 0
                name = os.path.basename(d.get("filename") or "")
                if name: p_name.value = name
                p_bar.value = pct
                ss = f"{human_size(spd)}/с" if spd else "—"
                es = human_eta(eta) if eta else "—"
                p_info.value = f"{pct*100:.1f}% · {ss} · осталось {es}"
                try: page.update()
                except Exception: pass

        opts = {"format": fmt_string(), "outtmpl": outtmpl, "noplaylist": True,
                "quiet": True, "no_warnings": True, "progress_hooks": [hook],
                "socket_timeout": 20, "retries": 3, "nocheckcertificate": True, "impersonate": "chrome-131"}
        if is_yt:
            opts["extractor_args"] = {"youtube": {"player_client": ["mweb", "tv", "web_safari"]}}

        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)
                if info and info.get("entries"):
                    info = next((e for e in info["entries"] if e), info)
            title = (info or {}).get("title") or "видео"
            try: path = info["requested_downloads"][0]["filepath"]
            except (KeyError, IndexError, TypeError): path = ""
            if not path or not os.path.exists(path):
                fs = [os.path.join(ddir, f) for f in os.listdir(ddir)]
                fs = [f for f in fs if os.path.isfile(f)]
                fs.sort(key=os.path.getmtime, reverse=True)
                path = fs[0] if fs else ""
            size = os.path.getsize(path) if path and os.path.exists(path) else 0
            add_row(title or os.path.basename(path), size, True)
            status.value = f"Сохранено: {os.path.basename(path) if path else title}"
            p_info.value = f"Готово · {human_size(size)}"
        except Exception as e:
            status.value = f"Ошибка: {str(e)[:120]}"
            p_box.visible = False
            add_row(f"Ошибка: {str(e)[:100]}", 0, False)
        finally:
            st["downloading"] = False
            download_btn.disabled = False
            try: page.update()
            except Exception: pass
            time.sleep(4)
            p_box.visible = False
            try: page.update()
            except Exception: pass

    def start_download(e=None):
        url = (url_input.value or "").strip()
        if not url:
            status.value = "Вставьте ссылку"; page.update(); return
        if not re.match(r"^https?://", url, re.I):
            status.value = "Ссылка должна начинаться с http:// или https://"; page.update(); return
        if st["downloading"]:
            status.value = "Уже идёт загрузка"; page.update(); return
        st["gen"] += 1
        g = st["gen"]
        st["downloading"] = True
        p_box.visible = True
        p_name.value = "Подготовка…"
        p_bar.value = 0
        p_info.value = ""
        status.value = "Загрузка…"
        download_btn.disabled = True
        page.update()
        threading.Thread(target=worker, args=(url, g), daemon=True).start()

    def set_video(e):
        st["format"] = "video"
        video_btn.bgcolor = C_ACCENT; video_btn.color = C_INK
        audio_btn.bgcolor = C_SURFACE; audio_btn.color = C_TEXT
        quality_row.visible = True; page.update()

    def set_audio(e):
        st["format"] = "audio"
        audio_btn.bgcolor = C_ACCENT; audio_btn.color = C_INK
        video_btn.bgcolor = C_SURFACE; video_btn.color = C_TEXT
        quality_row.visible = False; page.update()

    def make_q(q):
        def h(e):
            st["quality"] = q
            for bq, btn in quality_buttons:
                btn.bgcolor = C_ACCENT if bq == q else C_SURFACE
                btn.color = C_INK if bq == q else C_TEXT
            page.update()
        return h

    video_btn = ft.Container(content=ft.Text("Видео", color=C_INK, weight=ft.FontWeight.BOLD),
                         bgcolor=C_ACCENT, border_radius=10, padding=ft.padding.symmetric(horizontal=16, vertical=10),
                         on_click=set_video, expand=True, alignment=ft.alignment.center)
    audio_btn = ft.Container(content=ft.Text("Аудио", color=C_TEXT, weight=ft.FontWeight.BOLD),
                         bgcolor=C_SURFACE, border_radius=10, padding=ft.padding.symmetric(horizontal=16, vertical=10),
                         on_click=set_audio, expand=True, alignment=ft.alignment.center)

    quality_buttons = []
    quality_row = ft.Row(spacing=6)
    for q, label in (("480p", "480"), ("720p", "720"), ("1080p", "1080"), ("best", "Макс")):
        a = q == "720p"
        b = ft.Container(content=ft.Text(label, color=C_INK if a else C_TEXT, weight=ft.FontWeight.BOLD),
                         bgcolor=C_ACCENT if a else C_SURFACE, border_radius=10,
                         padding=ft.padding.symmetric(horizontal=10, vertical=8),
                         on_click=make_q(q), expand=True, alignment=ft.alignment.center)
        quality_buttons.append((q, b))
        quality_row.controls.append(b)

    download_btn = ft.Container(
        content=ft.Text("Скачать", color=C_INK, weight=ft.FontWeight.BOLD, size=16),
        bgcolor=C_ACCENT, border_radius=12, padding=ft.padding.symmetric(horizontal=32, vertical=14),
        on_click=start_download, alignment=ft.alignment.center,
    )

    def open_settings(e):
        page.dialog = ft.AlertDialog(
            title=ft.Text("Настройки"),
            content=ft.Column([
                ft.Text("Папка загрузок:", color=C_TEXT, size=13, weight=ft.FontWeight.BOLD),
                ft.Text(ddir, color=C_DIM, size=12, selectable=True),
                ft.Divider(color=C_DIM),
                ft.Text("Поддерживаются: YouTube, TikTok, VK, SoundCloud, Rutube, Twitter/X, Instagram и сотни других (yt-dlp).", color=C_DIM, size=12),
                ft.Text("Ограничение: 1080p без ffmpeg — максимум 720p single-file.", color=C_DIM, size=12),
            ], spacing=10, scroll=ft.ScrollMode.AUTO),
        )
        page.dialog.open = True
        page.update()

    page.appbar = ft.AppBar(
        title=ft.Row([
            ft.Text("FIT", color=C_ACCENT, weight=ft.FontWeight.BOLD, size=22),
            ft.Text(" Download", color=C_TEXT, weight=ft.FontWeight.BOLD, size=18),
        ], spacing=0),
        bgcolor=C_BG,
        actions=[ft.TextButton("Настройки", on_click=open_settings)],
    )

    page.add(
        url_input,
        ft.Row([video_btn, audio_btn], spacing=8),
        quality_row,
        download_btn,
        p_box,
        ft.Text("Недавние загрузки", color=C_DIM, size=12, weight=ft.FontWeight.BOLD),
        ft.Container(content=dl_list, expand=True),
        status,
    )

    def load_existing():
        try:
            fs = []
            for f in os.listdir(ddir):
                p = os.path.join(ddir, f)
                if os.path.isfile(p) and not f.endswith((".part", ".ytdl", ".tmp")):
                    fs.append((os.path.getmtime(p), p))
            fs.sort(reverse=True)
            for _, p in fs[:20]:
                add_row(os.path.basename(p), os.path.getsize(p), True)
        except Exception as e:
            status.value = f"Ошибка: {e}"; page.update()

    threading.Timer(0.3, load_existing).start()


ft.app(target=main)

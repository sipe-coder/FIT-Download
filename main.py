# -*- coding: utf-8 -*-
"""
FIT Download — простой загрузчик видео с YouTube, TikTok, VK, SoundCloud и т.д.
Сохранение в /storage/emulated/0/Download/FIT Download/
"""
import os
import re
import json
import time
import threading

import yt_dlp
from kivy.app import App
from kivy.clock import Clock
from kivy.core.clipboard import Clipboard
from kivy.core.window import Window
from kivy.lang import Builder
from kivy.metrics import dp, sp
from kivy.properties import BooleanProperty, ColorProperty, NumericProperty, StringProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.utils import platform

ON_ANDROID = platform == "android"

C_BG       = (0.051, 0.051, 0.071, 1)
C_SURFACE  = (0.102, 0.102, 0.133, 1)
C_RAISED   = (0.141, 0.141, 0.180, 1)
C_ACCENT   = (0.0,   0.851, 1.0,   1)
C_TEXT     = (0.941, 0.941, 0.961, 1)
C_DIM      = (0.533, 0.533, 0.565, 1)
C_INK      = (0.0,   0.0,   0.0,   1)
C_ERROR    = (1.0,   0.267, 0.333, 1)
C_SUCCESS  = (0.0,   0.831, 0.478, 1)


def load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def save_json(path, obj):
    try:
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=1)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except Exception as e:
        print("[WARN] save", path, e)


def human_size(n):
    try:
        n = float(n)
    except (TypeError, ValueError):
        return "\u2014"
    if n < 1024:
        return f"{int(n)} \u0411"
    for unit in ("\u041a\u0411", "\u041c\u0411", "\u0413\u0411", "\u0422\u0411"):
        n /= 1024
        if n < 1024:
            return f"{n:.1f} {unit}"
    return f"{n:.1f} \u0422\u0411"


def human_eta(sec):
    try:
        sec = int(sec)
    except (TypeError, ValueError):
        return "\u2014"
    if sec < 60:
        return f"{sec} \u0441"
    m, s = divmod(sec, 60)
    if m < 60:
        return f"{m}:{s:02d}"
    h, m = divmod(m, 60)
    return f"{h}:{m:02d}:{s:02d}"


KV = """
#:import dp kivy.metrics.dp
#:import sp kivy.metrics.sp

<FlatBtn>:
    background_normal: ''
    background_down: ''
    background_color: 0, 0, 0, 0
    color: app.c_text
    font_size: sp(15)
    markup: False
    canvas.before:
        Color:
            rgba: self.bg_color
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(12)]

<SegBtn>:
    background_normal: ''
    background_down: ''
    background_color: 0, 0, 0, 0
    font_size: sp(14)
    bold: True
    canvas.before:
        Color:
            rgba: (app.c_accent if self.active else app.c_surface)
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(10)]

BoxLayout:
    orientation: 'vertical'
    canvas.before:
        Color:
            rgba: app.c_bg
        Rectangle:
            pos: self.pos
            size: self.size

    BoxLayout:
        size_hint_y: None
        height: dp(64)
        padding: dp(20), dp(8)
        Label:
            text: 'FIT'
            color: app.c_accent
            bold: True
            font_size: sp(26)
            halign: 'left'
            valign: 'middle'
            text_size: self.size
            size_hint_x: None
            width: dp(52)
        Label:
            text: ' Download'
            color: app.c_text
            bold: True
            font_size: sp(20)
            halign: 'left'
            valign: 'middle'
            text_size: self.size
        FlatBtn:
            text: '\u041d\u0430\u0441\u0442\u0440\u043e\u0439\u043a\u0438'
            bg_color: app.c_surface
            size_hint_x: None
            width: dp(112)
            height: dp(40)
            size_hint_y: None
            pos_hint: {'center_y': .5}
            on_release: app.open_settings()

    BoxLayout:
        size_hint_y: None
        height: dp(72)
        padding: dp(16), dp(8)
        spacing: dp(8)
        TextInput:
            id: url_input
            hint_text: '\u0412\u0441\u0442\u0430\u0432\u044c\u0442\u0435 \u0441\u0441\u044b\u043b\u043a\u0443 (YouTube, TikTok, VK\u2026)'
            multiline: False
            font_size: sp(14)
            background_normal: ''
            background_active: ''
            background_color: app.c_surface
            foreground_color: app.c_text
            cursor_color: app.c_accent
            hint_text_color: app.c_dim
            padding: dp(14), dp(14)
            on_text_validate: app.start_download(self.text)
        FlatBtn:
            text: '\u0412\u0441\u0442\u0430\u0432\u0438\u0442\u044c'
            bg_color: app.c_surface
            size_hint_x: None
            width: dp(96)
            height: dp(56)
            size_hint_y: None
            pos_hint: {'center_y': .5}
            on_release: app.paste_url(url_input)

    BoxLayout:
        size_hint_y: None
        height: dp(52)
        padding: dp(16), 0
        spacing: dp(8)
        SegBtn:
            text: '\u0412\u0438\u0434\u0435\u043e'
            active: app.format_mode == 'video'
            color: app.c_ink if app.format_mode == 'video' else app.c_text
            on_release: app.set_format('video')
        SegBtn:
            text: '\u0410\u0443\u0434\u0438\u043e'
            active: app.format_mode == 'audio'
            color: app.c_ink if app.format_mode == 'audio' else app.c_text
            on_release: app.set_format('audio')

    BoxLayout:
        size_hint_y: None
        height: dp(46) if app.format_mode == 'video' else 0
        opacity: 1 if app.format_mode == 'video' else 0
        disabled: app.format_mode != 'video'
        padding: dp(16), dp(4)
        spacing: dp(6)
        SegBtn:
            text: '480'
            font_size: sp(13)
            active: app.quality == '480p'
            color: app.c_ink if app.quality == '480p' else app.c_text
            on_release: app.set_quality('480p')
        SegBtn:
            text: '720'
            font_size: sp(13)
            active: app.quality == '720p'
            color: app.c_ink if app.quality == '720p' else app.c_text
            on_release: app.set_quality('720p')
        SegBtn:
            text: '1080'
            font_size: sp(13)
            active: app.quality == '1080p'
            color: app.c_ink if app.quality == '1080p' else app.c_text
            on_release: app.set_quality('1080p')
        SegBtn:
            text: '\u041c\u0430\u043a\u0441'
            font_size: sp(13)
            active: app.quality == 'best'
            color: app.c_ink if app.quality == 'best' else app.c_text
            on_release: app.set_quality('best')

    BoxLayout:
        size_hint_y: None
        height: dp(74)
        padding: dp(16), dp(8)
        FlatBtn:
            text: '\u0421\u043a\u0430\u0447\u0430\u0442\u044c'
            bg_color: app.c_raised if app.downloading else app.c_accent
            color: app.c_dim if app.downloading else app.c_ink
            bold: True
            font_size: sp(18)
            disabled: app.downloading
            on_release: app.start_download(url_input.text)

    BoxLayout:
        size_hint_y: None
        height: dp(104) if app.show_progress else 0
        opacity: 1 if app.show_progress else 0
        padding: dp(16), dp(4)
        orientation: 'vertical'
        spacing: dp(6)
        Label:
            text: app.current_name
            color: app.c_text
            font_size: sp(13)
            text_size: self.width, None
            halign: 'left'
            valign: 'middle'
            size_hint_y: None
            height: dp(24)
            shorten: True
            max_lines: 1
        ProgressBar:
            max: 100
            value: app.progress_pct
            size_hint_y: None
            height: dp(8)
        Label:
            text: app.current_info
            color: app.c_dim
            font_size: sp(12)
            text_size: self.width, None
            halign: 'left'
            valign: 'middle'
            size_hint_y: None
            height: dp(20)
            shorten: True
            max_lines: 1

    Label:
        text: '\u041d\u0435\u0434\u0430\u0432\u043d\u0438\u0435 \u0437\u0430\u0433\u0440\u0443\u0437\u043a\u0438'
        color: app.c_dim
        font_size: sp(12)
        bold: True
        size_hint_y: None
        height: dp(26)
        text_size: self.width, self.height
        halign: 'left'
        valign: 'middle'
        padding: dp(20), 0

    ScrollView:
        bar_color: app.c_accent
        bar_width: dp(2)
        GridLayout:
            id: dl_list
            cols: 1
            size_hint_y: None
            height: self.minimum_height
            spacing: dp(6)
            padding: dp(16), 0, dp(16), dp(16)

    Label:
        text: app.status
        color: app.c_dim
        font_size: sp(11)
        size_hint_y: None
        height: dp(30)
        text_size: self.width - dp(32), self.height
        halign: 'left'
        valign: 'middle'
        shorten: True
        padding: dp(16), 0
"""


class FlatBtn(Button):
    bg_color = ColorProperty(C_RAISED)


class SegBtn(Button):
    active = BooleanProperty(False)


class FitApp(App):
    status = StringProperty("\u0413\u043e\u0442\u043e\u0432 \u043a \u0440\u0430\u0431\u043e\u0442\u0435")
    format_mode = StringProperty("video")
    quality = StringProperty("720p")

    downloading = BooleanProperty(False)
    show_progress = BooleanProperty(False)
    progress_pct = NumericProperty(0.0)
    current_name = StringProperty("")
    current_info = StringProperty("")

    c_bg = ColorProperty(C_BG)
    c_surface = ColorProperty(C_SURFACE)
    c_raised = ColorProperty(C_RAISED)
    c_accent = ColorProperty(C_ACCENT)
    c_text = ColorProperty(C_TEXT)
    c_dim = ColorProperty(C_DIM)
    c_ink = ColorProperty(C_INK)

    def build(self):
        Window.softinput_mode = "below_target"
        Window.clearcolor = C_BG
        self.cfg_path = os.path.join(self.user_data_dir, "config.json")
        self.cfg = load_json(self.cfg_path, {})
        self.format_mode = self.cfg.get("format", "video")
        self.quality = self.cfg.get("quality", "720p")
        self._gen = 0
        self._last_progress_update = 0.0
        self._history = []
        return Builder.load_string(KV)

    def on_start(self):
        Clock.schedule_once(lambda dt: self._load_existing(), 0.3)

    def _download_dir(self):
        if ON_ANDROID:
            try:
                from jnius import autoclass
                env = autoclass("android.os.Environment")
                ext = str(env.getExternalStorageDirectory().getAbsolutePath())
                base = os.path.join(ext, "Download", "FIT Download")
                try:
                    os.makedirs(base, exist_ok=True)
                except Exception:
                    pass
                return base
            except Exception:
                pass
            try:
                from jnius import autoclass
                act = autoclass("org.kivy.android.PythonActivity").mActivity
                base = str(act.getExternalFilesDir("Download").getAbsolutePath())
                os.makedirs(base, exist_ok=True)
                return base
            except Exception:
                pass
        base = os.path.join(self.user_data_dir, "downloads")
        os.makedirs(base, exist_ok=True)
        return base

    def paste_url(self, widget):
        try:
            text = Clipboard.paste()
        except Exception:
            text = ""
        if text:
            widget.text = text.strip()
            self.status = "\u0421\u0441\u044b\u043b\u043a\u0430 \u0432\u0441\u0442\u0430\u0432\u043b\u0435\u043d\u0430"
        else:
            self.status = "\u0411\u0443\u0444\u0435\u0440 \u043e\u0431\u043c\u0435\u043d\u0430 \u043f\u0443\u0441\u0442"

    def set_format(self, fmt):
        self.format_mode = fmt
        self.cfg["format"] = fmt
        save_json(self.cfg_path, self.cfg)

    def set_quality(self, q):
        self.quality = q
        self.cfg["quality"] = q
        save_json(self.cfg_path, self.cfg)

    def _fmt_string(self):
        if self.format_mode == "audio":
            return "bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio/best"
        if self.quality == "480p":
            lim = "[height<=480]"
        elif self.quality == "720p":
            lim = "[height<=720]"
        elif self.quality == "1080p":
            lim = "[height<=1080]"
        else:
            lim = ""
        return (
            f"best{lim}[ext=mp4][acodec!=none][vcodec!=none]/"
            f"best{lim}[acodec!=none][vcodec!=none]/"
            f"best[acodec!=none][vcodec!=none]/best"
        )

    def start_download(self, url):
        url = (url or "").strip()
        if not url:
            self.status = "\u0412\u0441\u0442\u0430\u0432\u044c\u0442\u0435 \u0441\u0441\u044b\u043b\u043a\u0443"
            return
        if not re.match(r"^https?://", url, re.I):
            self.status = "\u0421\u0441\u044b\u043b\u043a\u0430 \u0434\u043e\u043b\u0436\u043d\u0430 \u043d\u0430\u0447\u0438\u043d\u0430\u0442\u044c\u0441\u044f \u0441 http:// \u0438\u043b\u0438 https://"
            return
        if self.downloading:
            self.status = "\u0423\u0436\u0435 \u0438\u0434\u0451\u0442 \u0437\u0430\u0433\u0440\u0443\u0437\u043a\u0430"
            return
        self._gen += 1
        gen = self._gen
        self.downloading = True
        self.show_progress = True
        self.progress_pct = 0.0
        self.current_name = "\u041f\u043e\u0434\u0433\u043e\u0442\u043e\u0432\u043a\u0430\u2026"
        self.current_info = ""
        self.status = "\u0417\u0430\u0433\u0440\u0443\u0437\u043a\u0430\u2026"
        threading.Thread(target=self._download_w, args=(url, gen), daemon=True).start()

    def _download_w(self, url, gen):
        is_yt = "youtube.com" in url or "youtu.be" in url
        out_dir = self._download_dir()
        outtmpl = os.path.join(out_dir, "%(title).120B [%(id)s].%(ext)s")

        def hook(d):
            if gen != self._gen:
                return
            now = time.time()
            if d.get("status") == "downloading":
                if now - self._last_progress_update < 0.2:
                    return
                self._last_progress_update = now
                total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                got = d.get("downloaded_bytes") or 0
                pct = (got / total * 100.0) if total else 0.0
                speed = d.get("speed") or 0
                eta = d.get("eta") or 0
                name = d.get("filename") or ""
                name = os.path.basename(name) if name else ""
                Clock.schedule_once(lambda dt: self._on_progress(pct, speed, eta, name))
            elif d.get("status") == "finished":
                Clock.schedule_once(lambda dt: self._on_progress(100.0, 0, 0, ""))

        opts = {
            "format": self._fmt_string(),
            "outtmpl": outtmpl,
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "progress_hooks": [hook],
            "socket_timeout": 20,
            "retries": 3,
            "fragment_retries": 3,
            "nocheckcertificate": True,
            "restrictfilenames": False,
        }
        if is_yt:
            opts["extractor_args"] = {"youtube": {"player_client": ["mweb", "tv", "web_safari"]}}

        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)
                if info and info.get("entries"):
                    info = next((e for e in info["entries"] if e), info)
            title = (info or {}).get("title") or "\u0432\u0438\u0434\u0435\u043e"
            try:
                path = info["requested_downloads"][0]["filepath"]
            except (KeyError, IndexError, TypeError):
                path = ""
            if not path or not os.path.exists(path):
                try:
                    files = [os.path.join(out_dir, f) for f in os.listdir(out_dir)]
                    files = [f for f in files if os.path.isfile(f)]
                    files.sort(key=os.path.getmtime, reverse=True)
                    path = files[0] if files else ""
                except Exception:
                    path = ""
            size = os.path.getsize(path) if path and os.path.exists(path) else 0
            Clock.schedule_once(lambda dt: self._on_done(title, path, size, gen, None))
        except Exception as e:
            Clock.schedule_once(lambda dt: self._on_done(None, "", 0, gen, f"{type(e).__name__}: {str(e)[:300]}"))

    def _on_progress(self, pct, speed, eta, name):
        self.progress_pct = max(0.0, min(100.0, float(pct)))
        if name:
            self.current_name = name
        speed_s = f"{human_size(speed)}/\u0441" if speed else "\u2014"
        eta_s = human_eta(eta) if eta else "\u2014"
        self.current_info = f"{self.progress_pct:.1f}% \u00b7 {speed_s} \u00b7 \u043e\u0441\u0442\u0430\u043b\u043e\u0441\u044c {eta_s}"

    def _on_done(self, title, path, size, gen, error):
        self.downloading = False
        if gen != self._gen:
            return
        if error:
            self.show_progress = False
            self.current_name = ""
            self.current_info = ""
            self.status = f"\u041e\u0448\u0438\u0431\u043a\u0430: {error[:120]}"
            self._add_row(f"\u274c {error[:100]}", "", False)
            return
        self.progress_pct = 100.0
        self.current_info = f"\u0413\u043e\u0442\u043e\u0432\u043e \u00b7 {human_size(size)}"
        self.status = f"\u0421\u043e\u0445\u0440\u0430\u043d\u0435\u043d\u043e: {os.path.basename(path) if path else title}"
        self._add_row(title or os.path.basename(path), path, True)
        Clock.schedule_once(lambda dt: self._auto_hide_progress(), 4.0)

    def _auto_hide_progress(self):
        if not self.downloading:
            self.show_progress = False

    def _add_row(self, title, path, ok):
        try:
            lst = self.root.ids.dl_list
        except Exception:
            return
        row = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(54),
                        spacing=dp(2), padding=(dp(12), dp(6)))
        name = os.path.basename(path) if path else (title or "\u2014")
        size_s = human_size(os.path.getsize(path)) if path and os.path.exists(path) else ""
        top = Label(
            text=name, color=C_TEXT, font_size=sp(13),
            halign="left", valign="middle",
            text_size=(Window.width - dp(72), None),
            shorten=True, max_lines=1,
            size_hint_y=None, height=dp(20),
        )
        sub_text = ("\u2705 " if ok else "\u274c ") + (size_s or title or "")
        sub = Label(
            text=sub_text, color=C_SUCCESS if ok else C_ERROR,
            font_size=sp(11), halign="left", valign="middle",
            text_size=(Window.width - dp(72), None),
            shorten=True, max_lines=1,
            size_hint_y=None, height=dp(18),
        )
        row.add_widget(top)
        row.add_widget(sub)
        lst.add_widget(row, index=0)
        self._history.insert(0, {"title": title, "path": path, "ok": ok})

    def _load_existing(self):
        d = self._download_dir()
        try:
            files = []
            for f in os.listdir(d):
                p = os.path.join(d, f)
                if os.path.isfile(p) and not f.endswith((".part", ".ytdl", ".tmp")):
                    files.append((os.path.getmtime(p), p))
            files.sort(reverse=True)
            for _, p in files[:20]:
                self._add_row(os.path.basename(p), p, True)
        except Exception as e:
            print("[WARN] load_existing:", e)

    def open_settings(self):
        box = BoxLayout(orientation="vertical", spacing=dp(10), padding=dp(14))
        path = self._download_dir()
        box.add_widget(Label(
            text=f"\u041f\u0430\u043f\u043a\u0430 \u0437\u0430\u0433\u0440\u0443\u0437\u043e\u043a:\n[color=888890]{path}[/color]",
            markup=True, color=C_TEXT, font_size=sp(13),
            halign="left", valign="top",
            text_size=(Window.width * 0.85, None),
            size_hint_y=None, height=dp(70),
        ))
        info = Label(
            text=("\u041f\u043e\u0434\u0434\u0435\u0440\u0436\u0438\u0432\u0430\u044e\u0442\u0441\u044f: YouTube, TikTok, VK, SoundCloud, Rutube, "
                  "Twitter/X, Instagram \u0438 \u0441\u043e\u0442\u043d\u0438 \u0434\u0440\u0443\u0433\u0438\u0445 \u0441\u0430\u0439\u0442\u043e\u0432 (yt-dlp).\n\n"
                  "\u041e\u0433\u0440\u0430\u043d\u0438\u0447\u0435\u043d\u0438\u0435: 1080p \u0438 \u0432\u044b\u0448\u0435 \u0431\u0435\u0437 ffmpeg \u043d\u0435 \u0432\u0441\u0435\u0433\u0434\u0430 \u0434\u043e\u0441\u0442\u0443\u043f\u043d\u044b \u2014 "
                  "\u0432 \u0442\u0430\u043a\u043e\u043c \u0441\u043b\u0443\u0447\u0430\u0435 \u0441\u043a\u0430\u0447\u0438\u0432\u0430\u0435\u0442\u0441\u044f \u043c\u0430\u043a\u0441\u0438\u043c\u0443\u043c (\u043e\u0431\u044b\u0447\u043d\u043e 720p single-file)."),
            color=C_DIM, font_size=sp(12),
            halign="left", valign="top",
            text_size=(Window.width * 0.85, None),
            size_hint_y=None, height=dp(130),
        )
        box.add_widget(info)
        row = BoxLayout(size_hint_y=None, height=dp(52), spacing=dp(8))
        b_copy = FlatBtn(text="\u041a\u043e\u043f\u0438\u0440\u043e\u0432\u0430\u0442\u044c \u043f\u0443\u0442\u044c", bg_color=C_SURFACE)
        b_close = FlatBtn(text="\u0417\u0430\u043a\u0440\u044b\u0442\u044c", bg_color=C_ACCENT, color=C_INK, bold=True)
        row.add_widget(b_copy)
        row.add_widget(b_close)
        box.add_widget(row)
        pop = Popup(
            title="\u041d\u0430\u0441\u0442\u0440\u043e\u0439\u043a\u0438", content=box, size_hint=(0.94, None), height=dp(360),
            background="", background_color=C_BG,
            separator_color=C_ACCENT, title_color=C_TEXT, title_font="Roboto",
        )
        b_copy.bind(on_release=lambda *_: (Clipboard.copy(path), setattr(self, "status", "\u041f\u0443\u0442\u044c \u0441\u043a\u043e\u043f\u0438\u0440\u043e\u0432\u0430\u043d")))
        b_close.bind(on_release=pop.dismiss)
        pop.open()


if __name__ == "__main__":
    FitApp().run()

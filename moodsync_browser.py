#!/usr/bin/env python3
"""
MoodSync Browser v2 — Navigateur Chrome-like avec compte MoodSync
"""

import sys, os, json, re
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLineEdit, QLabel, QTabWidget, QStatusBar,
    QFrame, QProgressBar, QMenu, QDialog, QCheckBox,
    QStackedWidget, QGraphicsDropShadowEffect
)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import (
    QWebEnginePage, QWebEngineProfile, QWebEngineSettings
)
from PyQt6.QtCore import QUrl, Qt, QPoint, pyqtSignal, QObject
from PyQt6.QtGui import (
    QFont, QPalette, QColor, QKeySequence, QShortcut
)

# ── Config ───────────────────────────────────────────────────────────────────

HOME_URL     = "https://moodsync.alwaysdata.net"
LOGIN_URL    = "https://moodsync.alwaysdata.net/login.php"
PROFILE_URL  = "https://moodsync.alwaysdata.net/profile.php"
DATA_DIR     = Path.home() / ".moodsync_browser"
DATA_DIR.mkdir(exist_ok=True)
ACCOUNT_FILE = DATA_DIR / "account.json"

C = {
    "bg":         "#202124",
    "surface":    "#292a2d",
    "surface2":   "#35363a",
    "toolbar":    "#202124",
    "tabbar":     "#35363a",
    "tab_active": "#202124",
    "tab_hover":  "#404145",
    "border":     "#3c3c3f",
    "accent":     "#8ab4f8",
    "accent_dark":"#1a73e8",
    "ms_purple":  "#7c5cfc",
    "ms_purple2": "#a78bfa",
    "text":       "#e8eaed",
    "text_dim":   "#9aa0a6",
    "text_dimmer":"#5f6368",
    "danger":     "#f28b82",
    "success":    "#81c995",
    "warning":    "#fdd663",
    "white":      "#ffffff",
}

NAV_BTN_STYLE = f"""
    QPushButton {{
        background: transparent; border: none;
        border-radius: 17px;
        color: {C['text_dim']}; font-size: 16px;
        min-width:34px; min-height:34px;
        max-width:34px; max-height:34px;
    }}
    QPushButton:hover   {{ background: rgba(255,255,255,0.1); color:{C['text']}; }}
    QPushButton:pressed {{ background: rgba(255,255,255,0.15); }}
    QPushButton:disabled{{ color:{C['text_dimmer']}; }}
"""

GLOBAL_STYLE = f"""
QMainWindow, QWidget {{
    background: {C['bg']};
    color: {C['text']};
    font-family: 'Segoe UI', 'SF Pro Text', Ubuntu, sans-serif;
    font-size: 13px;
}}
QTabWidget::pane {{ border:none; background:{C['bg']}; }}
QTabBar {{ background:{C['tabbar']}; }}
QTabBar::tab {{
    background:{C['tabbar']}; color:{C['text_dim']};
    padding:0 12px; height:34px;
    min-width:80px; max-width:220px;
    border-top-left-radius:8px; border-top-right-radius:8px;
    margin-top:4px; margin-right:1px; font-size:12px;
}}
QTabBar::tab:selected {{
    background:{C['tab_active']}; color:{C['text']};
    margin-top:0; height:38px;
}}
QTabBar::tab:hover:!selected {{
    background:{C['tab_hover']}; color:{C['text']};
}}
QProgressBar {{
    background:transparent; border:none; height:3px;
}}
QProgressBar::chunk {{
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 {C['ms_purple']}, stop:0.5 {C['accent']}, stop:1 {C['ms_purple2']});
}}
QStatusBar {{
    background:{C['surface']}; color:{C['text_dimmer']};
    font-size:11px; border-top:1px solid {C['border']};
}}
QMenu {{
    background:{C['surface']}; border:1px solid {C['border']};
    border-radius:8px; padding:6px 4px; color:{C['text']};
}}
QMenu::item {{ padding:7px 20px; border-radius:4px; font-size:13px; }}
QMenu::item:selected {{ background:rgba(138,180,248,0.15); color:{C['accent']}; }}
QMenu::separator {{ height:1px; background:{C['border']}; margin:4px 8px; }}
QLineEdit {{
    background:{C['surface2']}; border:1.5px solid {C['border']};
    border-radius:8px; padding:8px 12px; color:{C['text']}; font-size:13px;
}}
QLineEdit:focus {{ border-color:{C['ms_purple']}; }}
QCheckBox {{ color:{C['text_dim']}; font-size:12px; spacing:6px; }}
QCheckBox::indicator {{
    width:14px; height:14px; border-radius:3px;
    border:1.5px solid {C['border']}; background:{C['surface2']};
}}
QCheckBox::indicator:checked {{
    background:{C['ms_purple']}; border-color:{C['ms_purple']};
}}
QScrollBar:vertical {{
    background:transparent; width:8px; margin:0;
}}
QScrollBar::handle:vertical {{
    background:{C['border']}; border-radius:4px; min-height:24px;
}}
QScrollBar::handle:vertical:hover {{ background:{C['text_dimmer']}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height:0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background:transparent; }}
"""

# ── Compte ────────────────────────────────────────────────────────────────────

class AccountManager(QObject):
    login_changed = pyqtSignal(bool, str)

    def __init__(self):
        super().__init__()
        self._user = ""
        self._load()

    def _load(self):
        if ACCOUNT_FILE.exists():
            try:
                d = json.loads(ACCOUNT_FILE.read_text())
                self._user = d.get("username", "")
            except Exception:
                pass

    def save(self, username: str):
        self._user = username
        ACCOUNT_FILE.write_text(json.dumps({"username": username}))
        self.login_changed.emit(True, username)

    def logout(self):
        self._user = ""
        if ACCOUNT_FILE.exists():
            ACCOUNT_FILE.unlink()
        self.login_changed.emit(False, "")

    @property
    def logged(self): return bool(self._user)
    @property
    def username(self): return self._user
    @property
    def initials(self):
        if not self._user: return "?"
        parts = self._user.strip().split()
        return (parts[0][0] + (parts[-1][0] if len(parts) > 1 else "")).upper()


account_mgr = AccountManager()

# ── Dialog compte ─────────────────────────────────────────────────────────────

class AccountDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Compte MoodSync")
        self.setFixedWidth(340)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._build()

    def _build(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        card = QWidget()
        card.setStyleSheet(f"""
            QWidget {{
                background:{C['surface']};
                border:1px solid {C['border']};
                border-radius:16px;
            }}
        """)
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(40)
        shadow.setColor(QColor(0, 0, 0, 160))
        shadow.setOffset(0, 8)
        card.setGraphicsEffect(shadow)

        lay = QVBoxLayout(card)
        lay.setContentsMargins(28, 22, 28, 22)
        lay.setSpacing(14)

        # Header
        hdr = QHBoxLayout()
        logo = QLabel("🎵")
        logo.setFont(QFont("", 20))
        logo.setStyleSheet("border:none; background:transparent;")
        title = QLabel("MoodSync")
        title.setFont(QFont("", 15, QFont.Weight.Bold))
        title.setStyleSheet(f"color:{C['ms_purple2']}; border:none; background:transparent;")
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(22, 22)
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background:transparent; border:none;
                color:{C['text_dim']}; font-size:12px; border-radius:11px;
            }}
            QPushButton:hover {{ background:rgba(255,255,255,0.1); color:{C['text']}; }}
        """)
        close_btn.clicked.connect(self.reject)
        hdr.addWidget(logo)
        hdr.addWidget(title)
        hdr.addStretch()
        hdr.addWidget(close_btn)
        lay.addLayout(hdr)

        self.stack = QStackedWidget()
        self.stack.setStyleSheet("QWidget { background: transparent; border: none; }")
        lay.addWidget(self.stack)

        # ── Page login ──
        login_w = QWidget()
        login_w.setStyleSheet("QWidget { background: transparent; border: none; }")
        lp = QVBoxLayout(login_w)
        lp.setContentsMargins(0, 0, 0, 0)
        lp.setSpacing(10)

        sub = QLabel("Connecte-toi à ton compte")
        sub.setStyleSheet(f"color:{C['text_dim']}; font-size:12px; border:none; background:transparent;")
        lp.addWidget(sub)

        self.inp_user = QLineEdit()
        self.inp_user.setPlaceholderText("Email ou identifiant")
        self.inp_user.setFixedHeight(40)
        lp.addWidget(self.inp_user)

        self.inp_pass = QLineEdit()
        self.inp_pass.setPlaceholderText("Mot de passe")
        self.inp_pass.setEchoMode(QLineEdit.EchoMode.Password)
        self.inp_pass.setFixedHeight(40)
        self.inp_pass.returnPressed.connect(self._do_login)
        lp.addWidget(self.inp_pass)

        self.cb_remember = QCheckBox("Rester connecté")
        self.cb_remember.setChecked(True)
        lp.addWidget(self.cb_remember)

        self.err_lbl = QLabel("")
        self.err_lbl.setStyleSheet(f"color:{C['danger']}; font-size:12px; border:none; background:transparent;")
        self.err_lbl.hide()
        lp.addWidget(self.err_lbl)

        btn_login = self._primary("Se connecter")
        btn_login.clicked.connect(self._do_login)
        lp.addWidget(btn_login)

        # Séparateur
        sep_row = QHBoxLayout()
        sl = QFrame(); sl.setFrameShape(QFrame.Shape.HLine)
        sl.setStyleSheet(f"color:{C['border']}; border:none; max-height:1px; background:{C['border']};")
        sr = QFrame(); sr.setFrameShape(QFrame.Shape.HLine)
        sr.setStyleSheet(f"color:{C['border']}; border:none; max-height:1px; background:{C['border']};")
        sl_lbl = QLabel("ou")
        sl_lbl.setStyleSheet(f"color:{C['text_dimmer']}; font-size:11px; border:none; background:transparent;")
        sep_row.addWidget(sl, 1)
        sep_row.addWidget(sl_lbl)
        sep_row.addWidget(sr, 1)
        lp.addLayout(sep_row)

        btn_open = self._secondary("Ouvrir dans l'onglet")
        btn_open.clicked.connect(self._open_in_tab)
        lp.addWidget(btn_open)

        self.stack.addWidget(login_w)

        # ── Page profil ──
        profile_w = QWidget()
        profile_w.setStyleSheet("QWidget { background: transparent; border: none; }")
        pp = QVBoxLayout(profile_w)
        pp.setContentsMargins(0, 0, 0, 0)
        pp.setSpacing(12)

        # Avatar
        av_row = QHBoxLayout()
        av_row.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.avatar_lbl = QLabel("?")
        self.avatar_lbl.setFixedSize(58, 58)
        self.avatar_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.avatar_lbl.setFont(QFont("", 20, QFont.Weight.Bold))
        self.avatar_lbl.setStyleSheet(f"""
            background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                stop:0 {C['ms_purple']}, stop:1 {C['ms_purple2']});
            color:white; border-radius:29px; border:none;
        """)
        av_row.addWidget(self.avatar_lbl)
        pp.addLayout(av_row)

        self.uname_lbl = QLabel("Utilisateur")
        self.uname_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.uname_lbl.setFont(QFont("", 14, QFont.Weight.Bold))
        self.uname_lbl.setStyleSheet(f"color:{C['text']}; border:none; background:transparent;")
        pp.addWidget(self.uname_lbl)

        st = QLabel("✅ Connecté à MoodSync")
        st.setAlignment(Qt.AlignmentFlag.AlignCenter)
        st.setStyleSheet(f"color:{C['success']}; font-size:12px; border:none; background:transparent;")
        pp.addWidget(st)

        btn_profile = self._primary("Voir mon profil")
        btn_profile.clicked.connect(self._open_profile)
        pp.addWidget(btn_profile)

        btn_logout = self._secondary("Se déconnecter")
        btn_logout.clicked.connect(self._do_logout)
        pp.addWidget(btn_logout)

        self.stack.addWidget(profile_w)
        outer.addWidget(card)
        self._refresh()

    def _primary(self, txt):
        b = QPushButton(txt)
        b.setFixedHeight(40)
        b.setStyleSheet(f"""
            QPushButton {{
                background:{C['ms_purple']}; border:none; border-radius:8px;
                color:white; font-size:13px; font-weight:600;
            }}
            QPushButton:hover {{ background:{C['ms_purple2']}; }}
            QPushButton:pressed {{ background:#6b48e8; }}
        """)
        return b

    def _secondary(self, txt):
        b = QPushButton(txt)
        b.setFixedHeight(38)
        b.setStyleSheet(f"""
            QPushButton {{
                background:transparent; border:1.5px solid {C['border']};
                border-radius:8px; color:{C['text_dim']}; font-size:13px;
            }}
            QPushButton:hover {{
                border-color:{C['ms_purple']}; color:{C['ms_purple2']};
            }}
        """)
        return b

    def _refresh(self):
        if account_mgr.logged:
            self.avatar_lbl.setText(account_mgr.initials)
            self.uname_lbl.setText(account_mgr.username)
            self.stack.setCurrentIndex(1)
        else:
            self.stack.setCurrentIndex(0)
        self.adjustSize()

    def _do_login(self):
        user = self.inp_user.text().strip()
        pwd  = self.inp_pass.text()
        if not user or not pwd:
            self.err_lbl.setText("Remplis tous les champs.")
            self.err_lbl.show()
            return
        account_mgr.save(user)
        if p := self.parent():
            p._autofill_login(user, pwd)
        self._refresh()

    def _do_logout(self):
        account_mgr.logout()
        if p := self.parent():
            p._on_logout()
        self._refresh()

    def _open_in_tab(self):
        if p := self.parent():
            p.new_tab(LOGIN_URL)
        self.accept()

    def _open_profile(self):
        if p := self.parent():
            p.new_tab(PROFILE_URL)
        self.accept()

    # Drag
    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._dp = e.globalPosition().toPoint() - self.frameGeometry().topLeft()
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        if e.buttons() == Qt.MouseButton.LeftButton and hasattr(self, '_dp'):
            self.move(e.globalPosition().toPoint() - self._dp)
        super().mouseMoveEvent(e)


# ── WebView ───────────────────────────────────────────────────────────────────

class TabPage(QWidget):
    def __init__(self, url, profile, win, parent=None):
        super().__init__(parent)
        self.win = win
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        self.prog = QProgressBar()
        self.prog.setTextVisible(False)
        self.prog.setFixedHeight(3)
        self.prog.setRange(0, 100)
        self.prog.setVisible(False)
        lay.addWidget(self.prog)

        self.view = QWebEngineView()
        page = QWebEnginePage(profile, self.view)
        self.view.setPage(page)

        s = self.view.settings()
        s.setAttribute(QWebEngineSettings.WebAttribute.LocalStorageEnabled, True)
        s.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        s.setAttribute(QWebEngineSettings.WebAttribute.FullScreenSupportEnabled, True)
        s.setAttribute(QWebEngineSettings.WebAttribute.PlaybackRequiresUserGesture, False)
        s.setAttribute(QWebEngineSettings.WebAttribute.ScrollAnimatorEnabled, True)
        lay.addWidget(self.view)

        self.view.loadStarted.connect(lambda: self.prog.setVisible(True))
        self.view.loadProgress.connect(self.prog.setValue)
        self.view.loadFinished.connect(lambda ok: (self.prog.setVisible(False), win.update_nav_state()))
        self.view.titleChanged.connect(self._on_title)
        self.view.urlChanged.connect(self._on_url)
        self.view.load(QUrl(url))

    def _on_title(self, t):
        idx = self.win.tabs.indexOf(self)
        if idx >= 0:
            short = (t[:20] + "…") if len(t) > 22 else t
            self.win.tabs.setTabText(idx, short or "Nouvel onglet")
            self.win.tabs.setTabToolTip(idx, t)

    def _on_url(self, url):
        if self.win.current_tab() is self:
            self.win.urlbar.setText(url.toString())
            self.win.update_nav_state()
            self.win._update_lock(url.toString())


# ── Fenêtre principale ────────────────────────────────────────────────────────

class MoodSyncBrowser(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MoodSync")
        self.resize(1280, 840)
        self.setMinimumSize(900, 600)
        self._muted = False

        # Profil persistant
        self.profile = QWebEngineProfile("MoodSync", self)
        self.profile.setPersistentStoragePath(str(DATA_DIR / "storage"))
        self.profile.setCachePath(str(DATA_DIR / "cache"))
        self.profile.setPersistentCookiesPolicy(
            QWebEngineProfile.PersistentCookiesPolicy.ForcePersistentCookies)
        self.profile.setHttpUserAgent(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36 MoodSyncBrowser/2.0")

        self._setup_ui()
        self._setup_shortcuts()
        account_mgr.login_changed.connect(self._on_account_changed)
        self.new_tab(HOME_URL)

    # ── UI ────────────────────────────────────────────────────────────────────

    def _setup_ui(self):
        self.setStyleSheet(GLOBAL_STYLE)
        root = QWidget()
        self.setCentralWidget(root)
        vbox = QVBoxLayout(root)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(0)

        # ── Toolbar ──────────────────────────────────────────────────────────
        toolbar = QWidget()
        toolbar.setFixedHeight(50)
        toolbar.setStyleSheet(
            f"background:{C['toolbar']}; border-bottom:1px solid {C['border']};")
        tl = QHBoxLayout(toolbar)
        tl.setContentsMargins(8, 6, 8, 6)
        tl.setSpacing(4)

        self.btn_back    = self._nbtn("←", "Précédent (Alt+←)")
        self.btn_forward = self._nbtn("→", "Suivant (Alt+→)")
        self.btn_reload  = self._nbtn("⟳", "Recharger (F5)")
        self.btn_back.clicked.connect(lambda: self.current_tab() and self.current_tab().view.back())
        self.btn_forward.clicked.connect(lambda: self.current_tab() and self.current_tab().view.forward())
        self.btn_reload.clicked.connect(self._reload)
        for b in (self.btn_back, self.btn_forward, self.btn_reload):
            tl.addWidget(b)

        tl.addSpacing(4)

        # URL bar wrapper
        url_wrap = QWidget()
        url_wrap.setStyleSheet("background:transparent;")
        ul = QHBoxLayout(url_wrap)
        ul.setContentsMargins(0, 0, 0, 0)
        ul.setSpacing(0)

        self.lock_lbl = QLabel("🔒")
        self.lock_lbl.setFixedWidth(30)
        self.lock_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lock_lbl.setStyleSheet(f"color:{C['success']}; font-size:12px; background:transparent;")

        self.urlbar = QLineEdit()
        self.urlbar.setPlaceholderText("Rechercher ou entrer une adresse")
        self.urlbar.returnPressed.connect(self._navigate)
        self.urlbar.setStyleSheet(f"""
            QLineEdit {{
                background:{C['surface2']}; border:1px solid transparent;
                border-radius:22px; padding:6px 16px 6px 8px;
                color:{C['text']}; font-size:13px;
            }}
            QLineEdit:focus {{
                border-color:{C['accent']}; background:{C['surface']};
                border-radius:4px;
            }}
            QLineEdit:hover:!focus {{ background:{C['surface']}; }}
        """)
        ul.addWidget(self.lock_lbl)
        ul.addWidget(self.urlbar, 1)
        tl.addWidget(url_wrap, 1)

        tl.addSpacing(4)

        # Boutons droite
        btn_home = self._nbtn("⌂", "Accueil MoodSync")
        btn_home.clicked.connect(lambda: self.current_tab() and
            self.current_tab().view.load(QUrl(HOME_URL)))

        btn_links = self._nbtn("⊕", "Liens rapides MoodSync")
        btn_links.clicked.connect(self._quick_links)

        btn_more = self._nbtn("⋮", "Paramètres et plus")
        btn_more.clicked.connect(self._more_menu)
        self._btn_more = btn_more

        # Bouton compte
        self.acc_btn = QPushButton("👤")
        self.acc_btn.setFixedSize(32, 32)
        self.acc_btn.setToolTip("Compte MoodSync")
        self.acc_btn.clicked.connect(self._show_account)
        self._refresh_acc_btn()

        for b in (btn_home, btn_links, btn_more):
            tl.addWidget(b)
        tl.addSpacing(2)
        tl.addWidget(self.acc_btn)

        vbox.addWidget(toolbar)

        # ── Tabs ─────────────────────────────────────────────────────────────
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.setTabsClosable(True)
        self.tabs.setMovable(True)
        self.tabs.tabCloseRequested.connect(self._close_tab)
        self.tabs.currentChanged.connect(self._tab_changed)

        newtab = QPushButton("+")
        newtab.setFixedSize(28, 28)
        newtab.setStyleSheet(f"""
            QPushButton {{
                background:transparent; border:none; border-radius:14px;
                color:{C['text_dim']}; font-size:18px;
            }}
            QPushButton:hover {{ background:rgba(255,255,255,0.1); color:{C['text']}; }}
        """)
        newtab.clicked.connect(lambda: self.new_tab(HOME_URL))
        self.tabs.setCornerWidget(newtab, Qt.Corner.TopRightCorner)
        vbox.addWidget(self.tabs)

        # ── Status bar ───────────────────────────────────────────────────────
        sb = QStatusBar()
        self.setStatusBar(sb)
        sb.setFixedHeight(22)
        self._sb_lbl = QLabel("● MoodSync Browser")
        self._sb_lbl.setStyleSheet(f"color:{C['text_dimmer']}; font-size:11px;")
        sb.addPermanentWidget(self._sb_lbl)

    def _nbtn(self, icon, tip):
        b = QPushButton(icon)
        b.setFixedSize(34, 34)
        b.setToolTip(tip)
        b.setStyleSheet(NAV_BTN_STYLE)
        return b

    # ── Tabs ──────────────────────────────────────────────────────────────────

    def new_tab(self, url=HOME_URL):
        p = TabPage(url, self.profile, self)
        idx = self.tabs.addTab(p, "Chargement…")
        self.tabs.setCurrentIndex(idx)
        self.urlbar.setText(url)

    def current_tab(self):
        w = self.tabs.currentWidget()
        return w if isinstance(w, TabPage) else None

    def _close_tab(self, idx):
        if self.tabs.count() <= 1:
            self.close(); return
        w = self.tabs.widget(idx)
        self.tabs.removeTab(idx)
        if w: w.deleteLater()

    def _tab_changed(self, idx):
        t = self.tabs.widget(idx)
        if isinstance(t, TabPage):
            url = t.view.url().toString()
            self.urlbar.setText(url)
            self.update_nav_state()
            self._update_lock(url)

    # ── Navigation ────────────────────────────────────────────────────────────

    def _navigate(self):
        text = self.urlbar.text().strip()
        if not text: return
        if re.match(r'^https?://', text):   url = text
        elif "." in text and " " not in text: url = "https://" + text
        else: url = f"https://www.google.com/search?q={text}"
        if t := self.current_tab():
            t.view.load(QUrl(url))

    def _reload(self):
        if t := self.current_tab():
            t.view.reload()

    def update_nav_state(self):
        if t := self.current_tab():
            self.btn_back.setEnabled(t.view.history().canGoBack())
            self.btn_forward.setEnabled(t.view.history().canGoForward())

    def _update_lock(self, url):
        if url.startswith("https://"):
            self.lock_lbl.setText("🔒")
            self.lock_lbl.setStyleSheet(f"color:{C['success']}; font-size:12px; background:transparent;")
        elif url.startswith("http://"):
            self.lock_lbl.setText("⚠")
            self.lock_lbl.setStyleSheet(f"color:{C['warning']}; font-size:13px; background:transparent;")
        else:
            self.lock_lbl.setText("")

    # ── Compte ────────────────────────────────────────────────────────────────

    def _show_account(self):
        dlg = AccountDialog(self)
        pos = self.acc_btn.mapToGlobal(
            QPoint(self.acc_btn.width() - 340, self.acc_btn.height() + 6))
        dlg.move(pos)
        dlg.exec()

    def _refresh_acc_btn(self):
        if account_mgr.logged:
            self.acc_btn.setText(account_mgr.initials)
            self.acc_btn.setToolTip(f"Connecté : {account_mgr.username}")
            self.acc_btn.setStyleSheet(f"""
                QPushButton {{
                    background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                        stop:0 {C['ms_purple']}, stop:1 {C['ms_purple2']});
                    border:none; border-radius:16px;
                    color:white; font-size:12px; font-weight:700;
                    min-width:32px; min-height:32px;
                    max-width:32px; max-height:32px;
                }}
                QPushButton:hover {{ background:{C['ms_purple2']}; }}
            """)
            self._sb_lbl.setText(f"● {account_mgr.username}")
            self._sb_lbl.setStyleSheet(f"color:{C['success']}; font-size:11px;")
        else:
            self.acc_btn.setText("👤")
            self.acc_btn.setToolTip("Se connecter à MoodSync")
            self.acc_btn.setStyleSheet(f"""
                QPushButton {{
                    background:{C['surface2']}; border:1.5px solid {C['border']};
                    border-radius:16px; color:{C['text_dim']}; font-size:16px;
                    min-width:32px; min-height:32px;
                    max-width:32px; max-height:32px;
                }}
                QPushButton:hover {{
                    border-color:{C['ms_purple']}; color:{C['text']};
                }}
            """)
            self._sb_lbl.setText("● MoodSync Browser")
            self._sb_lbl.setStyleSheet(f"color:{C['text_dimmer']}; font-size:11px;")

    def _on_account_changed(self, logged, username):
        self._refresh_acc_btn()

    def _autofill_login(self, user, pwd):
        """Ouvre login.php et injecte les credentials via JS."""
        def inject(ok):
            if not ok: return
            js = f"""
            (function() {{
                var u = document.querySelector(
                    'input[type=email],input[name=email],input[name=username],'
                    'input[id*=email],input[id*=user],input[name=login]');
                var p = document.querySelector('input[type=password]');
                if(u){{ u.value={json.dumps(user)};
                         u.dispatchEvent(new Event('input',{{bubbles:true}})); }}
                if(p){{ p.value={json.dumps(pwd)};
                         p.dispatchEvent(new Event('input',{{bubbles:true}})); }}
                var btn = document.querySelector(
                    'button[type=submit],input[type=submit],button.login-btn');
                if(btn) btn.click();
            }})();
            """
            if t := self.current_tab():
                t.view.page().runJavaScript(js)

        if t := self.current_tab():
            t.view.loadFinished.connect(inject)
            t.view.load(QUrl(LOGIN_URL))

    def _on_logout(self):
        self.profile.cookieStore().deleteAllCookies()
        if t := self.current_tab():
            t.view.load(QUrl(HOME_URL))

    # ── Menus ─────────────────────────────────────────────────────────────────

    def _quick_links(self):
        btn = self.sender()
        m = QMenu(self)
        links = [
            ("🏠 Accueil",        HOME_URL),
            ("💬 Messages",       HOME_URL + "/chat.php"),
            ("🔔 Notifications",  HOME_URL + "/notifications.php"),
            ("🎨 Studio",         HOME_URL + "/studio.php"),
            ("👤 Profil",         PROFILE_URL),
        ]
        for label, url in links:
            m.addAction(label, lambda u=url: self.new_tab(u))
        m.exec(btn.mapToGlobal(QPoint(0, btn.height() + 4)))

    def _more_menu(self):
        m = QMenu(self)
        m.addAction("➕  Nouvel onglet",         lambda: self.new_tab(HOME_URL))
        m.addSeparator()
        m.addAction("🔍  Zoom +",               lambda: self._zoom(1.1))
        m.addAction("🔍  Zoom −",               lambda: self._zoom(0.9))
        m.addAction("🔍  100%",                 self._zoom_reset)
        m.addSeparator()
        m.addAction("🔇  Couper/activer son",   self._toggle_mute)
        m.addAction("🛠  Outils dev  (F12)",    self._devtools)
        m.addAction("📄  Source page  (Ctrl+U)",self._view_source)
        m.addSeparator()
        m.addAction("🚪  Quitter",              self.close)
        m.exec(self._btn_more.mapToGlobal(
            QPoint(0, self._btn_more.height() + 4)))

    def _zoom(self, f):
        if t := self.current_tab():
            t.view.setZoomFactor(min(max(t.view.zoomFactor() * f, 0.25), 5.0))

    def _zoom_reset(self):
        if t := self.current_tab():
            t.view.setZoomFactor(1.0)

    def _toggle_mute(self):
        self._muted = not self._muted
        if t := self.current_tab():
            t.view.page().setAudioMuted(self._muted)

    def _devtools(self):
        if t := self.current_tab():
            dv = QWebEngineView()
            t.view.page().setDevToolsPage(dv.page())
            dv.resize(1000, 650)
            dv.setWindowTitle("DevTools — MoodSync Browser")
            dv.show()
            self._dv = dv

    def _view_source(self):
        if t := self.current_tab():
            self.new_tab("view-source:" + t.view.url().toString())

    # ── Raccourcis ────────────────────────────────────────────────────────────

    def _setup_shortcuts(self):
        sc = lambda key, fn: QShortcut(QKeySequence(key), self, fn)
        sc("Ctrl+T",          lambda: self.new_tab(HOME_URL))
        sc("Ctrl+W",          lambda: self._close_tab(self.tabs.currentIndex()))
        sc("Ctrl+L",          lambda: (self.urlbar.setFocus(), self.urlbar.selectAll()))
        sc("F5",              self._reload)
        sc("Ctrl+R",          self._reload)
        sc("F12",             self._devtools)
        sc("Ctrl+Shift+I",    self._devtools)
        sc("Ctrl+U",          self._view_source)
        sc("Alt+Left",        lambda: self.current_tab() and self.current_tab().view.back())
        sc("Alt+Right",       lambda: self.current_tab() and self.current_tab().view.forward())
        sc("Ctrl++",          lambda: self._zoom(1.1))
        sc("Ctrl+=",          lambda: self._zoom(1.1))
        sc("Ctrl+-",          lambda: self._zoom(0.9))
        sc("Ctrl+0",          self._zoom_reset)
        sc("Ctrl+Tab",        lambda: self.tabs.setCurrentIndex(
            (self.tabs.currentIndex()+1) % self.tabs.count()))
        sc("Ctrl+Shift+Tab",  lambda: self.tabs.setCurrentIndex(
            (self.tabs.currentIndex()-1) % self.tabs.count()))
        sc("Escape",          lambda: self.urlbar.clearFocus())

    # ── Drag & Drop ───────────────────────────────────────────────────────────

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls(): e.accept()

    def dropEvent(self, e):
        if urls := e.mimeData().urls():
            self.new_tab(urls[0].toString())


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS",
        "--disable-gpu-driver-bug-workarounds --no-sandbox")

    app = QApplication(sys.argv)
    app.setApplicationName("MoodSync Browser")
    app.setApplicationVersion("2.0")

    pal = QPalette()
    for role, col in [
        (QPalette.ColorRole.Window,          C["bg"]),
        (QPalette.ColorRole.WindowText,      C["text"]),
        (QPalette.ColorRole.Base,            C["surface"]),
        (QPalette.ColorRole.Text,            C["text"]),
        (QPalette.ColorRole.Button,          C["surface2"]),
        (QPalette.ColorRole.ButtonText,      C["text"]),
        (QPalette.ColorRole.Highlight,       C["ms_purple"]),
        (QPalette.ColorRole.HighlightedText, C["white"]),
        (QPalette.ColorRole.Link,            C["accent"]),
        (QPalette.ColorRole.PlaceholderText, C["text_dimmer"]),
    ]:
        pal.setColor(role, QColor(col))
    app.setPalette(pal)

    win = MoodSyncBrowser()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

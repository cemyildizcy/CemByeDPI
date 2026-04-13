"""
CemByeDPI - Ana Pencere
Modern PyQt6 arayüzü: Başlat/Durdur, DNS seçimi, hız testi, log, istatistikler.
Kapatınca sistem tepsisinde çalışmaya devam eder.
"""

import sys
import os
import time
from datetime import datetime

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QComboBox, QTextEdit, QProgressBar,
    QCheckBox, QFrame, QSystemTrayIcon, QMenu, QApplication,
    QSizePolicy,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject, QSize
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QAction, QFont

from gui.styles import STYLESHEET, ACCENT, GREEN, RED, TEXT_DIM, BG_CARD
from core.engine import Engine
from core.dns_manager import DNS_SERVERS, DEFAULT_DNS
from core.speed_test import SpeedTest


# ---------------------------------------------------------------------------
# Signal bridge (thread → GUI)
# ---------------------------------------------------------------------------
class _SignalBridge(QObject):
    log_signal = pyqtSignal(str)
    speed_progress = pyqtSignal(float, float)
    speed_done = pyqtSignal(float, float)
    engine_done = pyqtSignal(bool)
    update_found = pyqtSignal(str, str) # version_name, download_url
    update_progress = pyqtSignal(int)



# ---------------------------------------------------------------------------
def _find_icon_path() -> str | None:
    """icon.ico dosyasını bul (exe veya kaynak klasörde)."""
    import sys
    candidates = [
        os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "icon.ico"),
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "icon.ico"),
        os.path.join(getattr(sys, '_MEIPASS', ''), "icon.ico"),
    ]
    for p in candidates:
        if os.path.isfile(p):
            return p
    return None


_ICON_PATH = _find_icon_path()


def _make_icon(color: str = "", size: int = 64) -> QIcon:
    """Logo ikonunu yükle. Bulamazsa basit yuvarlak oluştur."""
    if _ICON_PATH:
        return QIcon(_ICON_PATH)
    # Fallback: basit yuvarlak
    size = max(size, 16)
    pm = QPixmap(size, size)
    pm.fill(QColor(0, 0, 0, 0))
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setBrush(QColor(color or "#5865F2"))
    p.setPen(Qt.PenStyle.NoPen)
    m = max(size // 8, 2)
    p.drawEllipse(m, m, size - m * 2, size - m * 2)
    p.setPen(QColor("#FFFFFF"))
    f = QFont("Segoe UI", max(size // 3, 8), QFont.Weight.Bold)
    p.setFont(f)
    p.drawText(pm.rect(), Qt.AlignmentFlag.AlignCenter, "C")
    p.end()
    return QIcon(pm)


# ---------------------------------------------------------------------------
# Ana Pencere
# ---------------------------------------------------------------------------
class MainWindow(QMainWindow):
    def __init__(self, start_minimized: bool = False, app_version: str = "v1.0"):
        super().__init__()
        self.app_version = app_version
        self.engine = Engine()
        self.speed_test = SpeedTest()
        self._bridge = _SignalBridge()

        self._setup_ui()
        self._setup_tray()
        self._connect_signals()
        self._start_timers()

        # Autostart durumunu yükle
        self.chk_autostart.setChecked(Engine.get_autostart())

        if start_minimized:
            self.hide()
        else:
            self.show()

    # ======================================================================
    # UI KURULUMU
    # ======================================================================
    def _setup_ui(self):
        self.setWindowTitle("CemByeDPI — Discord Erişim Aracı")
        self.setFixedSize(440, 920)
        self.setWindowIcon(_make_icon(ACCENT))

        central = QWidget()
        central.setObjectName("centralWidget")
        self.setCentralWidget(central)
        self.setStyleSheet(STYLESHEET)

        root = QVBoxLayout(central)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(12)

        # -- Başlık --
        title = QLabel("🛡️ CemByeDPI")
        title.setObjectName("titleLabel")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(title)

        sub = QLabel("Discord Erişim Engeli Aşma Aracı")
        sub.setObjectName("subtitleLabel")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(sub)

        root.addSpacing(4)

        # -- Power Button --
        pwr_row = QHBoxLayout()
        pwr_row.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.btn_power = QPushButton("⏻")
        self.btn_power.setObjectName("powerBtn")
        self.btn_power.setCheckable(True)
        self.btn_power.setToolTip("Başlat / Durdur")
        pwr_row.addWidget(self.btn_power)
        root.addLayout(pwr_row)

        # -- Durum --
        self.lbl_status = QLabel("● Bağlı Değil")
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_status.setFixedHeight(32)
        self.lbl_status.setStyleSheet(
            f"color: {TEXT_DIM}; background: #1a1b30; border-radius: 8px; font-weight: 600;"
        )
        root.addWidget(self.lbl_status)

        # -- DNS Seçimi --
        dns_card = self._card()
        dns_lay = QVBoxLayout(dns_card)
        dns_lay.setSpacing(6)
        dns_title = QLabel("🌐 DNS Sunucusu")
        dns_title.setObjectName("sectionTitle")
        dns_lay.addWidget(dns_title)
        self.cmb_dns = QComboBox()
        for name in DNS_SERVERS:
            primary, secondary = DNS_SERVERS[name]
            self.cmb_dns.addItem(f"{name}  ({primary})", name)
        dns_lay.addWidget(self.cmb_dns)
        root.addWidget(dns_card)
        
        # -- Platformlar --
        from core.domains import DOMAINS
        plat_card = self._card()
        plat_lay = QVBoxLayout(plat_card)
        plat_lay.setSpacing(6)
        plat_title = QLabel("🎯 Hedef Platformlar")
        plat_title.setObjectName("sectionTitle")
        plat_lay.addWidget(plat_title)
        
        # Checkboxes
        self.plat_boxes = {}
        for p_name in DOMAINS.keys():
            cb = QCheckBox(p_name)
            if p_name == "Discord":
                cb.setChecked(True)
            self.plat_boxes[p_name] = cb
            plat_lay.addWidget(cb)
            
        self.txt_custom = QLineEdit()
        self.txt_custom.setPlaceholderText("Özel Domain (Örn: pastebin.com)")
        self.txt_custom.setStyleSheet(
            "background: #202225; color: #dcddde; border: 1px solid #4f545c; padding: 4px; border-radius: 4px;"
        )
        plat_lay.addWidget(self.txt_custom)
        root.addWidget(plat_card)

        # -- Hız Testi --
        speed_card = self._card()
        speed_lay = QVBoxLayout(speed_card)
        speed_lay.setSpacing(8)

        speed_header = QHBoxLayout()
        st = QLabel("⚡ Hız Testi")
        st.setObjectName("sectionTitle")
        speed_header.addWidget(st)
        speed_header.addStretch()
        self.btn_speed = QPushButton("Teste Başla")
        self.btn_speed.setObjectName("speedBtn")
        speed_header.addWidget(self.btn_speed)
        speed_lay.addLayout(speed_header)

        self.speed_bar = QProgressBar()
        self.speed_bar.setValue(0)
        self.speed_bar.setFixedHeight(10)
        speed_lay.addWidget(self.speed_bar)

        results_row = QHBoxLayout()
        # Download
        dl_box = QVBoxLayout()
        self.lbl_speed = QLabel("—")
        self.lbl_speed.setObjectName("speedResult")
        self.lbl_speed.setAlignment(Qt.AlignmentFlag.AlignCenter)
        dl_box.addWidget(self.lbl_speed)
        dl_lbl = QLabel("İndirme (Mbps)")
        dl_lbl.setObjectName("statLabel")
        dl_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        dl_box.addWidget(dl_lbl)
        results_row.addLayout(dl_box)
        # Ping
        ping_box = QVBoxLayout()
        self.lbl_ping = QLabel("—")
        self.lbl_ping.setObjectName("pingResult")
        self.lbl_ping.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ping_box.addWidget(self.lbl_ping)
        ping_lbl = QLabel("Ping (ms)")
        ping_lbl.setObjectName("statLabel")
        ping_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ping_box.addWidget(ping_lbl)
        results_row.addLayout(ping_box)
        speed_lay.addLayout(results_row)
        root.addWidget(speed_card)

        # -- İstatistikler --
        stat_card = self._card()
        stat_grid = QGridLayout(stat_card)
        stat_grid.setSpacing(6)

        st2 = QLabel("📊 İstatistikler")
        st2.setObjectName("sectionTitle")
        stat_grid.addWidget(st2, 0, 0, 1, 3)

        self.lbl_processed = QLabel("0")
        self.lbl_processed.setObjectName("statValue")
        self.lbl_processed.setAlignment(Qt.AlignmentFlag.AlignCenter)
        stat_grid.addWidget(self.lbl_processed, 1, 0)

        self.lbl_fragmented = QLabel("0")
        self.lbl_fragmented.setObjectName("statValue")
        self.lbl_fragmented.setAlignment(Qt.AlignmentFlag.AlignCenter)
        stat_grid.addWidget(self.lbl_fragmented, 1, 1)

        self.lbl_uptime = QLabel("00:00:00")
        self.lbl_uptime.setObjectName("statValue")
        self.lbl_uptime.setAlignment(Qt.AlignmentFlag.AlignCenter)
        stat_grid.addWidget(self.lbl_uptime, 1, 2)

        for col, txt in enumerate(["İşlenen Paket", "Parçalanan", "Çalışma Süresi"]):
            l = QLabel(txt)
            l.setObjectName("statLabel")
            l.setAlignment(Qt.AlignmentFlag.AlignCenter)
            stat_grid.addWidget(l, 2, col)

        root.addWidget(stat_card)

        # -- Log --
        self.log_box = QTextEdit()
        self.log_box.setObjectName("logBox")
        self.log_box.setReadOnly(True)
        self.log_box.setFixedHeight(110)
        self.log_box.setPlaceholderText("Log mesajları burada gösterilecek...")
        root.addWidget(self.log_box)

        # -- Alt Seçenekler --
        opts = QHBoxLayout()
        self.chk_autostart = QCheckBox("Bilgisayar açılışında başlat")
        opts.addWidget(self.chk_autostart)
        opts.addStretch()
        
        # Sürüm Bilgisi
        self.lbl_version = QLabel(self.app_version)
        self.lbl_version.setObjectName("statLabel")
        self.lbl_version.setStyleSheet("color: #72767d; font-size: 11px;")
        opts.addWidget(self.lbl_version)
        
        opts.addStretch()
        self.chk_tray = QCheckBox("Kapatınca arka planda çalış")
        self.chk_tray.setChecked(True)
        opts.addWidget(self.chk_tray)
        root.addLayout(opts)

    def _card(self) -> QFrame:
        f = QFrame()
        f.setObjectName("card")
        return f

    # ======================================================================
    # SİSTEM TEPSİSİ
    # ======================================================================
    def _setup_tray(self):
        self.tray = QSystemTrayIcon(_make_icon(ACCENT), self)
        self.tray.setToolTip("CemByeDPI")

        menu = QMenu()
        self.tray_toggle = QAction("▶  Başlat", self)
        self.tray_toggle.triggered.connect(self._on_power)
        menu.addAction(self.tray_toggle)
        menu.addSeparator()

        show_act = QAction("Pencereyi Göster", self)
        show_act.triggered.connect(self._show_window)
        menu.addAction(show_act)

        quit_act = QAction("Çıkış", self)
        quit_act.triggered.connect(self._quit)
        menu.addAction(quit_act)

        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._on_tray_click)
        self.tray.show()

    def _on_tray_click(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._show_window()

    def _show_window(self):
        self.showNormal()
        self.activateWindow()

    # ======================================================================
    # SİNYALLER
    # ======================================================================
    def _connect_signals(self):
        self.btn_power.clicked.connect(self._on_power)
        self.btn_speed.clicked.connect(self._on_speed_test)
        self.chk_autostart.toggled.connect(Engine.set_autostart)

        self.engine.on_log(self._bridge.log_signal.emit)
        self._bridge.log_signal.connect(self._append_log)
        self._bridge.speed_progress.connect(self._on_speed_progress)
        self._bridge.speed_done.connect(self._on_speed_done)
        self._bridge.engine_done.connect(self._on_engine_done)
        
        self._bridge.update_found.connect(self._on_update_found)
        self._bridge.update_progress.connect(self._on_update_progress)

    def _start_timers(self):
        self._stats_timer = QTimer(self)
        self._stats_timer.timeout.connect(self._refresh_stats)
        self._stats_timer.start(1000)
        
        # Güncelleme kontrolünü pencere açıldıktan 2 saniye sonra başlat
        QTimer.singleShot(2000, self._start_update_check)
        
    def _start_update_check(self):
        import threading
        from utils.updater import check_for_updates
        def _check():
            has_update, new_ver, dl_url = check_for_updates(self.app_version)
            if has_update:
                self._bridge.update_found.emit(new_ver, dl_url)
        threading.Thread(target=_check, daemon=True).start()


    # ======================================================================
    # GÜNCELLEME EKRANI
    # ======================================================================
    def _on_update_found(self, new_ver: str, dl_url: str):
        from PyQt6.QtWidgets import QMessageBox
        msg = QMessageBox(self)
        msg.setWindowTitle("Güncelleme Mevcut!")
        msg.setText(f"CemByeDPI'ın yeni sürümü ({new_ver}) bulundu.\n\nŞimdi otomatik olarak indirilip kurulsun mu?")
        msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg.setDefaultButton(QMessageBox.StandardButton.Yes)
        msg.setStyleSheet("QLabel{color:white;} QMessageBox{background:#2b2d31;} QPushButton{background:#5865F2;color:white;border-radius:4px;padding:6px;min-width:60px;}")
        
        if msg.exec() == QMessageBox.StandardButton.Yes:
            self._start_update_download(dl_url, new_ver)

    def _start_update_download(self, dl_url: str, new_ver: str):
        from PyQt6.QtWidgets import QProgressDialog
        import threading
        from utils.updater import download_and_update
        
        self.update_dlg = QProgressDialog(f"{new_ver} İndiriliyor...", "İptal (Kapat)", 0, 100, self)
        self.update_dlg.setWindowTitle("Güncelleme")
        self.update_dlg.setStyleSheet("QLabel{color:white;} QProgressDialog{background:#2b2d31;} QProgressBar{border:1px solid #4f545c;border-radius:4px;text-align:center;color:white;} QProgressBar::chunk{background:#5865F2;}")
        self.update_dlg.setWindowModality(Qt.WindowModality.WindowModal)
        self.update_dlg.setCancelButton(None) # iptal edilemez
        self.update_dlg.show()
        
        def _dl():
            download_and_update(dl_url, progress_callback=self._bridge.update_progress.emit)
        
        threading.Thread(target=_dl, daemon=True).start()

    def _on_update_progress(self, pct: int):
        if hasattr(self, "update_dlg"):
            self.update_dlg.setValue(pct)
            if pct >= 100:
                self.update_dlg.setLabelText("Kuruluyor... Lütfen Bekleyin.")

    # ======================================================================
    # EYLEMLER
    # ======================================================================
    def _on_power(self):
        if self.engine.active:
            self.engine.stop()
            self.btn_power.setChecked(False)
            self.lbl_status.setText("● Bağlı Değil")
            self.lbl_status.setStyleSheet(
                f"color: {TEXT_DIM}; background: #1a1b30; border-radius: 8px;"
            )
            self.tray_toggle.setText("▶  Başlat")
            self.tray.setIcon(_make_icon(ACCENT))
            self.cmb_dns.setEnabled(True)
            self.btn_power.setEnabled(True)
        else:
            # Loading durumu göster
            self.btn_power.setEnabled(False)
            self.btn_power.setChecked(True)
            self.lbl_status.setText("● Bağlanıyor... (DNS çözümleniyor)")
            self.lbl_status.setStyleSheet(
                f"color: #FEE75C; background: #2e2a15; border-radius: 8px;"
            )
            self.cmb_dns.setEnabled(False)

            dns_name = self.cmb_dns.currentData()
            
            from core.domains import get_combined_domains
            sel_plats = [k for k, v in self.plat_boxes.items() if v.isChecked()]
            c_txt = self.txt_custom.text().strip()
            c_doms = c_txt.split(",") if c_txt else []
            targets = get_combined_domains(sel_plats, c_doms)

            self.engine.start_async(
                dns_name=dns_name,
                target_domains=targets,
                done_cb=self._bridge.engine_done.emit,
            )

    def _on_engine_done(self, ok: bool):
        """Arka plan engine başlatma tamamlandı."""
        self.btn_power.setEnabled(True)
        self.btn_power.setChecked(ok)
        if ok:
            self.lbl_status.setText("● Bağlı — Discord Erişimi Aktif")
            self.lbl_status.setStyleSheet(
                f"color: {GREEN}; background: #122e1a; border-radius: 8px;"
            )
            self.tray_toggle.setText("⏸  Durdur")
            self.tray.setIcon(_make_icon(GREEN))
        else:
            self.lbl_status.setText("● Hata — Başlatılamadı")
            self.lbl_status.setStyleSheet(
                f"color: {RED}; background: #2e1215; border-radius: 8px;"
            )
            self.cmb_dns.setEnabled(True)

    def _on_speed_test(self):
        if self.speed_test.running:
            return
        self.btn_speed.setEnabled(False)
        self.btn_speed.setText("Test yapılıyor...")
        self.speed_bar.setValue(0)
        self.lbl_speed.setText("...")
        self.lbl_ping.setText("...")

        self.speed_test.on_progress(self._bridge.speed_progress.emit)
        self.speed_test.on_done(self._bridge.speed_done.emit)
        self.speed_test.start()

    def _on_speed_progress(self, pct: float, speed: float):
        self.speed_bar.setValue(int(pct))
        if speed > 0:
            self.lbl_speed.setText(f"{speed:.1f}")

    def _on_speed_done(self, dl: float, ping: float):
        self.speed_bar.setValue(100)
        self.lbl_speed.setText(f"{dl:.1f}" if dl > 0 else "Hata")
        self.lbl_ping.setText(f"{ping:.0f}" if ping < 900 else "Hata")
        self.btn_speed.setEnabled(True)
        self.btn_speed.setText("Teste Başla")
        self._append_log(f"⚡ Hız: {dl:.1f} Mbps | Ping: {ping:.0f} ms")

    def _refresh_stats(self):
        if self.engine.active:
            frag = self.engine.fragmenter
            self.lbl_processed.setText(f"{frag.packets_processed:,}")
            self.lbl_fragmented.setText(f"{frag.packets_fragmented:,}")
            self.lbl_uptime.setText(self.engine.get_uptime())

    def _append_log(self, msg: str):
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_box.append(f"[{ts}] {msg}")
        sb = self.log_box.verticalScrollBar()
        sb.setValue(sb.maximum())

    # ======================================================================
    # PENCERE OLAYLARI
    # ======================================================================
    def closeEvent(self, event):
        if self.chk_tray.isChecked():
            event.ignore()
            self.hide()
            self.tray.showMessage(
                "CemByeDPI",
                "Arka planda çalışmaya devam ediyor.",
                QSystemTrayIcon.MessageIcon.Information,
                2000,
            )
        else:
            self._quit()

    def _quit(self):
        import time
        import subprocess
        import os
        self.engine.stop()
        self.tray.hide()
        
        # PyInstaller _MEI hatasının ana çözümü: WinDivert kernel sürücüsü, 
        # program kapandıktan sonra bile arka planda Windows hizmeti (service) 
        # olarak çalışmaya devam eder ve dosya kilidini bırakmaz.
        try:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = 0
            
            subprocess.run(["sc.exe", "stop", "WinDivert"], capture_output=True, startupinfo=startupinfo, creationflags=subprocess.CREATE_NO_WINDOW)
            subprocess.run(["sc.exe", "delete", "WinDivert"], capture_output=True, startupinfo=startupinfo, creationflags=subprocess.CREATE_NO_WINDOW)
        except Exception:
            pass
            
        time.sleep(0.5)
        
        # Kesin Çözüm: PyInstaller'ın ctypes DLL'leri kilitliyken "Failed to remove" 
        # hatası vermesini engellemek için, Bootloader'i (ana çalıştırıcıyı) arkadan vuruyoruz.
        # Bootloader silme işlemini yapmaya yeltenemeden zorla (force) kapatılıyor.
        try:
            ppid = os.getppid()
            subprocess.run(["taskkill", "/F", "/PID", str(ppid)], startupinfo=startupinfo, creationflags=subprocess.CREATE_NO_WINDOW)
        except Exception:
            pass
        os._exit(0)

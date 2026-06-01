import sys
import os
import subprocess
import json
import csv
import math
import time
import re
import urllib.request
import requests
import socket
from typing import Dict, Optional, Set

from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QComboBox,
    QFileDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QMessageBox,
    QGridLayout, QTableWidget, QTableWidgetItem, QFrame, QDialog,
    QTextEdit, QHeaderView, QAbstractItemView, QColorDialog, QScrollArea,
    QStackedWidget, QSizePolicy, QSpacerItem, QProgressBar
)
from PySide6.QtGui import (
    QFont, QPixmap, QColor, QLinearGradient, QBrush, QPalette,
    QPainter, QPen, QRadialGradient, QIcon, QCursor, QPainterPath
)
from PySide6.QtCore import (
    Qt, QThread, Signal, QProcess, QTimer, QPropertyAnimation,
    QEasingCurve, QSize, QRect, QPoint, QRectF
)
from PySide6.QtCore import qInstallMessageHandler

def silence_qt_warnings(msg_type, context, message):
    pass
qInstallMessageHandler(silence_qt_warnings)

# -------------------------------------------------------
# CONFIG  (unchanged from original)
# -------------------------------------------------------
TEST_CASES = [
    "SoC BEHAVIOR", "SHUTDOWN PROCESS", "PRECHARGE PROCESS",
    "BMS STATE TRANSITION", "CELL TEMP IMBALANCE", "BMS PCB TEMP",
    "ANY BMS ERROR", "FLAG FULL CHARGE DISABLE", "DCLI / DCLO MAP",
    "EQUIVALENT CYCLE COUNT", "BMS BALANCING",
    "PRIMARY VS SECONDARY LATCH", "MCU OBC ERROR",
    "AuxCharge_with_Vehicle_state_change",
    "SoC vs VOLTAGE SUMMARY", "CAPACITY + SoC vs RANGE CHECK",
    "BMS CURRENT IN READY MODE", "DRIVE_CHARGE Max Min Avg CURRENT"
]

FW_CHECKER = "FW_Config_checker.py"
CLEAR_OUTPUTS_ON_RUN_ALL = True

SCRIPT_BY_ROW: Dict[int, str] = {
    0:  "SoC_behavior.py",
    1:  "Shutdown_Process.py",
    2:  "Precharge_Process.py",
    3:  "BMS_State_transition.py",
    4:  "Cell_Temp_Imbalance.py",
    5:  "BMS_PCB_Temp.py",
    6:  "Any_BMS_Error.py",
    7:  "Flag_Full_Charge_Disable.py",
    8:  "DCLI_DCLO_Map.py",
    9:  "Equivalent_cycle_count.py",
    10: "BMS_Balancing.py",
    11: "Primary_vs_Secondary_Latch.py",
    12: "MCU_OBC_Error.py",
    13: "AuxCharge_with_Vehicle_state_change.py",
    14: "SoC_vs_Voltage_Summary.py",
    15: "Capacity_check.py",
    16: "BMS_Current_in_Ready_Mode.py",
    17: "DRIVE_CHARGE_Max_Min_Avg_CURRENT.py",
}

RESULT_POLL_ATTEMPTS = 10
RESULT_POLL_DELAY_MS  = 500

# -------------------------------------------------------
# DESIGN TOKENS  – one place to tweak everything
# -------------------------------------------------------
C = {
    # backgrounds
    "bg_app":       "#0D1117",
    "bg_sidebar":   "#161B22",
    "bg_panel":     "#1C2128",
    "bg_card":      "#21262D",
    "bg_input":     "#161B22",
    "bg_hover":     "#2D333B",
    "bg_active":    "#1F3A5F",

    # borders
    "border":       "#30363D",
    "border_accent":"#388BFD",

    # text
    "text_primary":  "#E6EDF3",
    "text_secondary":"#8B949E",
    "text_accent":   "#58A6FF",
    "text_muted":    "#484F58",

    # status colours
    "pass":    "#1F6B3A",
    "pass_fg": "#3FB950",
    "fail":    "#6B1A1A",
    "fail_fg": "#F85149",
    "warn":    "#6B4E10",
    "warn_fg": "#D29922",
    "run":     "#1F3A5F",
    "run_fg":  "#388BFD",
    "notrun":  "#2D333B",
    "notrun_fg":"#8B949E",

    # accent
    "blue":    "#388BFD",
    "green":   "#3FB950",
    "red":     "#F85149",
    "orange":  "#D29922",
    "purple":  "#BC8CFF",

    # sidebar nav
    "nav_icon": "#8B949E",
    "nav_active_bg": "#1F3A5F",
    "nav_active_fg": "#58A6FF",
}

FONT_MAIN  = "Segoe UI"
FONT_MONO  = "Consolas"

# -------------------------------------------------------
# STYLESHEET
# -------------------------------------------------------
APP_STYLE = f"""
QWidget {{
    background: {C['bg_app']};
    color: {C['text_primary']};
    font-family: '{FONT_MAIN}';
    font-size: 13px;
}}
QScrollBar:vertical {{
    background: {C['bg_panel']};
    width: 6px;
    border-radius: 3px;
}}
QScrollBar::handle:vertical {{
    background: {C['border']};
    border-radius: 3px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{
    background: {C['text_secondary']};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}
QScrollBar:horizontal {{
    height: 0px;
}}
QLineEdit {{
    background: {C['bg_input']};
    border: 1px solid {C['border']};
    border-radius: 6px;
    padding: 6px 10px;
    color: {C['text_primary']};
    font-family: '{FONT_MONO}';
    font-size: 12px;
}}
QLineEdit:focus {{
    border-color: {C['border_accent']};
}}
QComboBox {{
    background: {C['bg_input']};
    border: 1px solid {C['border']};
    border-radius: 6px;
    padding: 6px 10px;
    color: {C['text_primary']};
    min-width: 120px;
}}
QComboBox::drop-down {{
    border: none;
    width: 24px;
}}
QComboBox::down-arrow {{
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid {C['text_secondary']};
    margin-right: 6px;
}}
QComboBox QAbstractItemView {{
    background: {C['bg_panel']};
    border: 1px solid {C['border']};
    selection-background-color: {C['bg_active']};
    color: {C['text_primary']};
}}
QTableWidget {{
    background: transparent;
    border: none;
    gridline-color: {C['border']};
    outline: none;
}}
QTableWidget::item {{
    padding: 6px 10px;
    border-bottom: 1px solid {C['border']};
}}
QTableWidget::item:selected {{
    background: {C['bg_hover']};
    color: {C['text_primary']};
}}
QHeaderView::section {{
    background: {C['bg_panel']};
    color: {C['text_secondary']};
    font-size: 11px;
    font-weight: bold;
    letter-spacing: 1px;
    text-transform: uppercase;
    padding: 8px 10px;
    border: none;
    border-bottom: 1px solid {C['border']};
}}
QToolTip {{
    background: {C['bg_panel']};
    color: {C['text_primary']};
    border: 1px solid {C['border']};
    border-radius: 4px;
    padding: 4px 8px;
}}
QMessageBox {{
    background: {C['bg_panel']};
}}
QDialog {{
    background: {C['bg_panel']};
}}
"""

# -------------------------------------------------------
# REUSABLE WIDGETS
# -------------------------------------------------------
class SidebarBtn(QPushButton):
    """Left navigation button."""
    def __init__(self, icon_char: str, label: str, parent=None):
        super().__init__(parent)
        self.icon_char = icon_char
        self.label_text = label
        self._active = False
        self.setCheckable(False)
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setFixedHeight(44)
        self._update_style()

    def set_active(self, active: bool):
        self._active = active
        self._update_style()

    def _update_style(self):
        if self._active:
            self.setStyleSheet(f"""
                QPushButton {{
                    background: {C['nav_active_bg']};
                    color: {C['nav_active_fg']};
                    border: none;
                    border-left: 3px solid {C['blue']};
                    border-radius: 0px;
                    text-align: left;
                    padding: 0 16px;
                    font-weight: 600;
                    font-size: 13px;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    color: {C['nav_icon']};
                    border: none;
                    border-left: 3px solid transparent;
                    border-radius: 0px;
                    text-align: left;
                    padding: 0 16px;
                    font-size: 13px;
                }}
                QPushButton:hover {{
                    background: {C['bg_hover']};
                    color: {C['text_primary']};
                }}
            """)
        self.setText(f"  {self.icon_char}   {self.label_text}")


class PrimaryBtn(QPushButton):
    def __init__(self, text, color=None, parent=None):
        super().__init__(text, parent)
        color = color or C['blue']
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setStyleSheet(f"""
            QPushButton {{
                background: {color};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 18px;
                font-weight: 600;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background: {color}cc;
            }}
            QPushButton:disabled {{
                background: {C['border']};
                color: {C['text_muted']};
            }}
        """)


class GhostBtn(QPushButton):
    def __init__(self, text, color=None, parent=None):
        super().__init__(text, parent)
        color = color or C['blue']
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {color};
                border: 1px solid {color}66;
                border-radius: 6px;
                padding: 5px 12px;
                font-size: 12px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background: {color}22;
                border-color: {color};
            }}
            QPushButton:disabled {{
                color: {C['text_muted']};
                border-color: {C['border']};
            }}
        """)


class IconBtn(QPushButton):
    """Small round icon button for ▶ run."""
    def __init__(self, icon="▶", color=None, parent=None):
        super().__init__(icon, parent)
        color = color or C['blue']
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setFixedSize(28, 28)
        self.setStyleSheet(f"""
            QPushButton {{
                background: {color}22;
                color: {color};
                border: 1px solid {color}55;
                border-radius: 14px;
                font-size: 11px;
                font-weight: bold;
                padding: 0px;
            }}
            QPushButton:hover {{
                background: {color}44;
                border-color: {color};
            }}
            QPushButton:pressed {{
                background: {color}66;
            }}
        """)


class CardFrame(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"""
            QFrame {{
                background: {C['bg_card']};
                border: 1px solid {C['border']};
                border-radius: 10px;
            }}
        """)


class SectionHeader(QLabel):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setStyleSheet(f"""
            QLabel {{
                color: {C['text_secondary']};
                font-size: 10px;
                font-weight: 700;
                letter-spacing: 2px;
                background: transparent;
                padding: 14px 0 6px 0;
            }}
        """)


class FWRow(QFrame):
    def __init__(self, label: str, color_bar: str = C['blue'], parent=None):
        super().__init__(parent)
        self.setStyleSheet("QFrame { background: transparent; border: none; }")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        bar = QFrame()
        bar.setFixedWidth(3)
        bar.setStyleSheet(f"background: {color_bar}; border-radius: 1px; border: none;")
        lay.addWidget(bar)

        lbl = QLabel(label)
        lbl.setFixedWidth(170)
        lbl.setStyleSheet(f"color: {C['text_secondary']}; font-size: 11px; padding: 4px 8px; background: transparent; border: none;")
        lay.addWidget(lbl)

        self.value_box = QLineEdit()
        self.value_box.setReadOnly(True)
        self.value_box.setStyleSheet(f"""
            QLineEdit {{
                background: {C['bg_input']};
                border: none;
                border-radius: 0px;
                border-bottom: 1px solid {C['border']};
                color: {C['text_primary']};
                font-family: '{FONT_MONO}';
                font-size: 11px;
                padding: 4px 8px;
            }}
        """)
        lay.addWidget(self.value_box, 1)

    def set_value(self, v: str):
        self.value_box.setText(v)

    def get_value(self) -> str:
        return self.value_box.text()


class StatusDot(QWidget):
    """Coloured circle for status column."""
    COLORS = {
        "Not Run":  C['text_muted'],
        "Running":  C['blue'],
        "Completed": C['green'],
        "Error":    C['red'],
        "PASS":     C['green'],
        "FAIL":     C['red'],
        "WARNING":  C['orange'],
    }
    def __init__(self, status="Not Run", parent=None):
        super().__init__(parent)
        self.status = status
        self.setFixedSize(10, 10)

    def set_status(self, s):
        self.status = s
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        color = QColor(self.COLORS.get(self.status, C['text_muted']))
        p.setBrush(color)
        p.setPen(Qt.NoPen)
        p.drawEllipse(0, 0, 10, 10)


class StatusPill(QLabel):
    """Pill-shaped status label."""
    STYLES = {
        "Not Run":   (C['notrun'],    C['notrun_fg']),
        "Running":   (C['run'],       C['run_fg']),
        "Completed": (C['pass'],      C['pass_fg']),
        "Error":     (C['fail'],      C['fail_fg']),
        "PASS":      (C['pass'],      C['pass_fg']),
        "FAIL":      (C['fail'],      C['fail_fg']),
        "WARNING":   (C['warn'],      C['warn_fg']),
        "N/A":       (C['notrun'],    C['notrun_fg']),
    }
    def __init__(self, text="Not Run", parent=None):
        super().__init__(text, parent)
        self.set_status(text)
        self.setAlignment(Qt.AlignCenter)

    def set_status(self, text: str):
        self.setText(text)
        bg, fg = self.STYLES.get(text, (C['notrun'], C['notrun_fg']))
        self.setStyleSheet(f"""
            QLabel {{
                background: {bg};
                color: {fg};
                border-radius: 10px;
                padding: 3px 10px;
                font-size: 11px;
                font-weight: 600;
            }}
        """)


class StatCard(QFrame):
    def __init__(self, icon, label, value="0", color=C['blue'], parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"""
            QFrame {{
                background: {C['bg_card']};
                border: 1px solid {C['border']};
                border-radius: 10px;
            }}
        """)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(12)

        icon_lbl = QLabel(icon)
        icon_lbl.setStyleSheet(f"color: {color}; font-size: 22px; background: transparent; border: none;")
        lay.addWidget(icon_lbl)

        txt = QVBoxLayout()
        txt.setSpacing(2)
        self.val_lbl = QLabel(value)
        self.val_lbl.setStyleSheet(f"color: {color}; font-size: 20px; font-weight: 700; background: transparent; border: none;")
        lbl_w = QLabel(label)
        lbl_w.setStyleSheet(f"color: {C['text_secondary']}; font-size: 11px; background: transparent; border: none;")
        txt.addWidget(self.val_lbl)
        txt.addWidget(lbl_w)
        lay.addLayout(txt)
        lay.addStretch()

    def set_value(self, v: str):
        self.val_lbl.setText(v)


# -------------------------------------------------------
# JSON / IMAGE POPUPS  (same logic, new style)
# -------------------------------------------------------
class JsonDialog(QDialog):
    def __init__(self, json_path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Test Result")
        self.resize(580, 420)
        self.setStyleSheet(f"background:{C['bg_panel']}; color:{C['text_primary']};")

        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(10)

        header = QLabel("📋  Test Result JSON")
        header.setStyleSheet(f"font-size:15px; font-weight:700; color:{C['text_accent']};")
        lay.addWidget(header)

        text = QTextEdit()
        text.setReadOnly(True)
        text.setStyleSheet(f"""
            QTextEdit {{
                background:{C['bg_app']};
                border:1px solid {C['border']};
                border-radius:8px;
                font-family:'{FONT_MONO}';
                font-size:12px;
                color:{C['text_primary']};
                padding:10px;
            }}
        """)

        if os.path.exists(json_path):
            try:
                with open(json_path, "r", encoding="cp1252", errors="replace") as f:
                    loaded = json.load(f)
                pretty = json.dumps(loaded, indent=4, ensure_ascii=False)
            except Exception as e:
                pretty = f"Failed to load JSON:\n{e}"
        else:
            pretty = f"File not found:\n{json_path}"

        text.setPlainText(pretty)
        lay.addWidget(text)

        btn = GhostBtn("Close", C['text_secondary'])
        btn.clicked.connect(self.accept)
        lay.addWidget(btn, alignment=Qt.AlignRight)


class ImageDialog(QDialog):
    def __init__(self, image_path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Graph")
        self.resize(700, 520)
        self.setStyleSheet(f"background:{C['bg_panel']};")

        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 16, 16, 16)
        lbl = QLabel()
        lbl.setAlignment(Qt.AlignCenter)

        if os.path.exists(image_path):
            pix = QPixmap(image_path)
            if not pix.isNull():
                pix = pix.scaled(640, 440, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                lbl.setPixmap(pix)
            else:
                lbl.setText("Failed to load image.")
        else:
            lbl.setText(f"File not found:\n{image_path}")

        lay.addWidget(lbl)
        btn = GhostBtn("Close", C['text_secondary'])
        btn.clicked.connect(self.accept)
        lay.addWidget(btn, alignment=Qt.AlignRight)


# -------------------------------------------------------
# BACKGROUND THREADS  (all unchanged from original)
# -------------------------------------------------------
class FWCheckerThread(QThread):
    finished_ok  = Signal(dict)
    finished_err = Signal(str)
    def __init__(self, trc_file):
        super().__init__()
        self.trc_file = trc_file
    def run(self):
        try:
            proc = subprocess.Popen(
                [sys.executable, FW_CHECKER, self.trc_file],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            out, err = proc.communicate()
            if proc.returncode != 0:
                self.finished_err.emit(err); return
            try:
                self.finished_ok.emit(json.loads(out))
            except Exception:
                self.finished_err.emit("Invalid FW JSON output")
        except Exception as e:
            self.finished_err.emit(str(e))


class VCUResetThread(QThread):
    finished_ok  = Signal(dict)
    finished_err = Signal(str)
    def __init__(self, trc_file, script_path, output_path):
        super().__init__()
        self.trc_file = trc_file
        self.script_path = script_path
        self.output_path = output_path
    def run(self):
        try:
            proc = subprocess.Popen(
                [sys.executable, self.script_path, self.trc_file, self.output_path],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                cwd=os.path.dirname(self.script_path))
            out, err = proc.communicate()
            if proc.returncode != 0:
                self.finished_err.emit(err or out or "VCU reset script failed"); return
            with open(self.output_path, "r", encoding="utf-8", errors="ignore") as f:
                data = json.load(f)
            self.finished_ok.emit(data)
        except Exception as e:
            self.finished_err.emit(str(e))


class BMSResetThread(QThread):
    finished_ok  = Signal(dict)
    finished_err = Signal(str)
    def __init__(self, trc_file, script_path, output_path):
        super().__init__()
        self.trc_file = trc_file
        self.script_path = script_path
        self.output_path = output_path
    def run(self):
        try:
            proc = subprocess.Popen(
                [sys.executable, self.script_path, self.trc_file, self.output_path],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                cwd=os.path.dirname(self.script_path))
            out, err = proc.communicate()
            if proc.returncode != 0:
                self.finished_err.emit(err or out or "BMS reset script failed"); return
            with open(self.output_path, "r", encoding="utf-8", errors="ignore") as f:
                data = json.load(f)
            self.finished_ok.emit(data)
        except Exception as e:
            self.finished_err.emit(str(e))


class MCUDetectionThread(QThread):
    finished_ok  = Signal(dict)
    finished_err = Signal(str)
    def __init__(self, trc_file, script_dir):
        super().__init__()
        self.trc_file = trc_file
        self.script_dir = script_dir
    def run(self):
        try:
            proc = subprocess.Popen(
                [sys.executable, os.path.join(self.script_dir, "MCU_detection.py"), self.trc_file],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            out, err = proc.communicate()
            if proc.returncode != 0:
                self.finished_err.emit(err or "MCU detection failed"); return
            self.finished_ok.emit(json.loads(out.strip()))
        except Exception as e:
            self.finished_err.emit(str(e))


# -------------------------------------------------------
# DASHBOARD PANEL  (left side content area)
# -------------------------------------------------------
class DashboardPanel(QWidget):
    """File browse + BMS info + VCU/BMS reset + generate buttons."""

    # signals to main window
    file_selected = Signal(str)
    run_all_clicked = Signal()
    generate_report = Signal()
    generate_excel  = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background: transparent;")
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        inner = QWidget()
        inner.setStyleSheet("background: transparent;")
        self._lay = QVBoxLayout(inner)
        self._lay.setContentsMargins(16, 8, 16, 16)
        self._lay.setSpacing(6)

        # ── MAKE LOGS section ──────────────────────────────
        self._build_make_logs_section()

        # ── FILE SELECT section ───────────────────────────
        self._build_file_section()

        # ── RUN ALL ────────────────────────────────────────
        self.run_all_btn = PrimaryBtn("  ▶  RUN ALL TEST CASES", C['blue'])
        self.run_all_btn.setEnabled(False)
        self.run_all_btn.setFixedHeight(42)
        self.run_all_btn.clicked.connect(self.run_all_clicked.emit)
        self._lay.addWidget(self.run_all_btn)

        # ── BMS INFORMATION ───────────────────────────────
        self._build_bms_section()

        # ── RESET CHECKS ─────────────────────────────────
        self._build_reset_section()

        # ── GENERATE BUTTONS ──────────────────────────────
        self._build_generate_section()

        self._lay.addStretch()
        scroll.setWidget(inner)
        root.addWidget(scroll)

    # ── builders ──────────────────────────────────────────
    def _build_make_logs_section(self):
        hdr = SectionHeader("MAKE YOUR LOGS ORGANISED")
        self._lay.addWidget(hdr)

        self.make_btn = PrimaryBtn("📁  Organise Logs", C['orange'])
        self.make_btn.setFixedHeight(38)
        self._lay.addWidget(self.make_btn)

    def _build_file_section(self):
        hdr = SectionHeader("SELECT FILE TYPE")
        self._lay.addWidget(hdr)

        row = QHBoxLayout()
        row.setSpacing(8)
        self.ft_combo = QComboBox()
        self.ft_combo.addItems([".trc", ".log", ".csv", ".xlsx"])
        self.ft_combo.setFixedHeight(36)
        row.addWidget(self.ft_combo, 1)
        self._lay.addLayout(row)

        # Browse area  – card style
        self.browse_card = CardFrame()
        self.browse_card.setFixedHeight(72)
        bc_lay = QVBoxLayout(self.browse_card)
        bc_lay.setContentsMargins(0, 0, 0, 0)

        self.browse_btn = QPushButton("☁  Browse File\nor drag and drop")
        self.browse_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {C['text_secondary']};
                border: none;
                font-size: 12px;
            }}
            QPushButton:hover {{
                color: {C['text_accent']};
            }}
        """)
        self.browse_btn.setCursor(QCursor(Qt.PointingHandCursor))
        bc_lay.addWidget(self.browse_btn, alignment=Qt.AlignCenter)
        self._lay.addWidget(self.browse_card)

        self.file_box = QLineEdit("No file selected")
        self.file_box.setReadOnly(True)
        self.file_box.setFixedHeight(32)
        self._lay.addWidget(self.file_box)

    def _build_bms_section(self):
        hdr = SectionHeader("BMS INFORMATION")

        toggle_row = QHBoxLayout()
        toggle_row.addWidget(hdr)
        toggle_row.addStretch()
        self.bms_toggle = QPushButton("▲")
        self.bms_toggle.setFixedSize(22, 22)
        self.bms_toggle.setStyleSheet(f"background:transparent; color:{C['text_secondary']}; border:none; font-size:10px;")
        self.bms_toggle.clicked.connect(self._toggle_bms)
        toggle_row.addWidget(self.bms_toggle)
        self._lay.addLayout(toggle_row)

        self.bms_container = QWidget()
        self.bms_container.setStyleSheet("background:transparent;")
        bc = QVBoxLayout(self.bms_container)
        bc.setContentsMargins(0, 0, 0, 0)
        bc.setSpacing(2)

        # colour bars: blue=BMS, purple=STARK, green=XAVIER, orange=DISTANCE, teal=MCU
        self.fw_hw        = FWRow("BMS HW VERSION",         C['blue'])
        self.fw_fw        = FWRow("BMS FIRMWARE",           C['blue'])
        self.fw_cfg       = FWRow("BMS CONFIG ID",          C['blue'])
        self.fw_git       = FWRow("BMS GITSHA",             C['blue'])
        self.fw_manifest  = FWRow("BMS MANIFEST",           C['blue'])
        self.fw_stark_fw  = FWRow("STARK FIRMWARE",         C['purple'])
        self.fw_stark_cfg = FWRow("STARK CONFIG",           C['purple'])
        self.fw_xavier_fw = FWRow("XAVIER FIRMWARE",        C['green'])
        self.fw_distance  = FWRow("DISTANCE COVERED",       C['orange'])
        self.fw_mcu       = FWRow("MCU BRANCH",             "#3FBEAA")
        self.fw_serial    = FWRow("SERIAL NO",              "#3FBEAA")
        self.fw_os        = FWRow("OS Version & Build No",  "#3FBEAA")

        for w in [self.fw_hw, self.fw_fw, self.fw_cfg, self.fw_git,
                  self.fw_manifest, self.fw_stark_fw, self.fw_stark_cfg,
                  self.fw_xavier_fw, self.fw_distance,
                  self.fw_mcu, self.fw_serial, self.fw_os]:
            bc.addWidget(w)

        self._lay.addWidget(self.bms_container)
        self._bms_expanded = True

    def _toggle_bms(self):
        self._bms_expanded = not self._bms_expanded
        self.bms_container.setVisible(self._bms_expanded)
        self.bms_toggle.setText("▲" if self._bms_expanded else "▼")

    def _build_reset_section(self):
        hdr = SectionHeader("RESET CHECKS")
        self._lay.addWidget(hdr)

        card = CardFrame()
        cl = QVBoxLayout(card)
        cl.setContentsMargins(12, 10, 12, 10)
        cl.setSpacing(8)

        # VCU row
        vcu_row = QHBoxLayout()
        vcu_icon = QLabel("⚙")
        vcu_icon.setStyleSheet(f"color:{C['blue']}; font-size:16px; background:transparent; border:none;")
        vcu_row.addWidget(vcu_icon)
        vcu_lbl = QLabel("VCU unexpected Reset")
        vcu_lbl.setStyleSheet(f"color:{C['text_primary']}; background:transparent; border:none;")
        vcu_row.addWidget(vcu_lbl, 1)
        self.tx_vcu_value = QLineEdit("0")
        self.tx_vcu_value.setReadOnly(True)
        self.tx_vcu_value.setFixedWidth(60)
        self.tx_vcu_value.setAlignment(Qt.AlignCenter)
        self.tx_vcu_result = QLineEdit("N/A")
        self.tx_vcu_result.setReadOnly(True)
        self.tx_vcu_result.setFixedWidth(60)
        self.tx_vcu_result.setAlignment(Qt.AlignCenter)
        vcu_row.addWidget(self.tx_vcu_value)
        vcu_row.addWidget(self.tx_vcu_result)
        cl.addLayout(vcu_row)

        # BMS row
        bms_row = QHBoxLayout()
        bms_icon = QLabel("🔋")
        bms_icon.setStyleSheet(f"background:transparent; border:none; font-size:14px;")
        bms_row.addWidget(bms_icon)
        bms_lbl = QLabel("MARVEL BMS unexpected Reset")
        bms_lbl.setStyleSheet(f"color:{C['text_primary']}; background:transparent; border:none;")
        bms_row.addWidget(bms_lbl, 1)
        self.tx_bms_value = QLineEdit("0")
        self.tx_bms_value.setReadOnly(True)
        self.tx_bms_value.setFixedWidth(60)
        self.tx_bms_value.setAlignment(Qt.AlignCenter)
        self.tx_bms_result = QLineEdit("N/A")
        self.tx_bms_result.setReadOnly(True)
        self.tx_bms_result.setFixedWidth(60)
        self.tx_bms_result.setAlignment(Qt.AlignCenter)
        bms_row.addWidget(self.tx_bms_value)
        bms_row.addWidget(self.tx_bms_result)
        cl.addLayout(bms_row)

        self._lay.addWidget(card)

        # store for compat
        self.vcu_value_palette_default = self.tx_vcu_value.palette()
        self.vcu_result_palette_default = self.tx_vcu_result.palette()
        self.bms_value_palette_default  = self.tx_bms_value.palette()
        self.bms_result_palette_default = self.tx_bms_result.palette()

    def _build_generate_section(self):
        hdr = SectionHeader("GENERATE")
        self._lay.addWidget(hdr)

        self.gen_btn = GhostBtn("📄  CREATE REPORT SUMMARY", C['text_primary'])
        self.gen_btn.setFixedHeight(38)
        self.gen_btn.clicked.connect(self.generate_report.emit)
        self._lay.addWidget(self.gen_btn)

        self.gen_excel_btn = GhostBtn("📊  CREATE EXCEL TRACKER", C['green'])
        self.gen_excel_btn.setFixedHeight(38)
        self.gen_excel_btn.clicked.connect(self.generate_excel.emit)
        self._lay.addWidget(self.gen_excel_btn)


# -------------------------------------------------------
# TEST CASES PANEL  (right content area)
# -------------------------------------------------------
class TestCasesPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background: transparent;")
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(14)

        # ── header row ────────────────────────────────────
        hdr_row = QHBoxLayout()
        title = QLabel("TEST CASES")
        title.setStyleSheet(f"font-size:18px; font-weight:700; color:{C['text_primary']};")
        sub = QLabel("Run, analyze and visualize test case results")
        sub.setStyleSheet(f"font-size:12px; color:{C['text_secondary']}; margin-top:3px;")

        hdr_left = QVBoxLayout()
        hdr_left.setSpacing(2)
        hdr_left.addWidget(title)
        hdr_left.addWidget(sub)
        hdr_row.addLayout(hdr_left)
        hdr_row.addStretch()

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("🔍  Search test cases...")
        self.search_box.setFixedWidth(240)
        self.search_box.setFixedHeight(34)
        self.search_box.textChanged.connect(self._filter_rows)
        hdr_row.addWidget(self.search_box)
        root.addLayout(hdr_row)

        # ── table ─────────────────────────────────────────
        self.table = QTableWidget(len(TEST_CASES), 5)
        self.table.setHorizontalHeaderLabels(
            ["TEST CASE", "STATUS", "VIEW RESULTS", "VIEW GRAPH", "RESULT"])
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(False)
        self.table.setSelectionMode(QAbstractItemView.NoSelection)
        self.table.setFocusPolicy(Qt.NoFocus)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.table.horizontalHeader().setHighlightSections(False)

        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.Stretch)
        hh.setSectionResizeMode(1, QHeaderView.Fixed);  self.table.setColumnWidth(1, 120)
        hh.setSectionResizeMode(2, QHeaderView.Fixed);  self.table.setColumnWidth(2, 110)
        hh.setSectionResizeMode(3, QHeaderView.Fixed);  self.table.setColumnWidth(3, 110)
        hh.setSectionResizeMode(4, QHeaderView.Fixed);  self.table.setColumnWidth(4, 90)

        self.table.setStyleSheet(f"""
            QTableWidget {{
                background: {C['bg_card']};
                border: 1px solid {C['border']};
                border-radius: 10px;
            }}
            QTableWidget::item {{
                border-bottom: 1px solid {C['border']};
                padding: 0px;
            }}
        """)
        self.table.verticalHeader().setDefaultSectionSize(46)

        # row widgets
        self._status_pills = []
        self._result_pills = []
        self._run_btns     = []
        self._view_btns    = []
        self._graph_btns   = []

        for i, name in enumerate(TEST_CASES):
            display_name = name
            if i == 0:
                display_name = "SoC BEHAVIOR + SoC STUCK"

            # col 0 – test name + expand chevron + run btn
            cell0 = QWidget()
            cell0.setStyleSheet("background: transparent;")
            h0 = QHBoxLayout(cell0)
            h0.setContentsMargins(12, 0, 8, 0)
            h0.setSpacing(8)

            chev = QLabel("›")
            chev.setStyleSheet(f"color:{C['text_muted']}; font-size:16px; background:transparent;")
            h0.addWidget(chev)

            lbl = QLabel(display_name)
            lbl.setStyleSheet(f"color:{C['text_primary']}; font-size:12px; font-weight:500; background:transparent;")
            h0.addWidget(lbl, 1)

            run_btn = IconBtn("▶", C['blue'])
            run_btn.clicked.connect(lambda _, r=i: self._on_run(r))
            h0.addWidget(run_btn)
            self._run_btns.append(run_btn)

            self.table.setCellWidget(i, 0, cell0)

            # col 1 – status pill
            status_w = QWidget()
            status_w.setStyleSheet("background:transparent;")
            s_lay = QHBoxLayout(status_w)
            s_lay.setContentsMargins(8, 0, 8, 0)
            pill = StatusPill("Not Run")
            s_lay.addWidget(pill)
            s_lay.addStretch()
            self.table.setCellWidget(i, 1, status_w)
            self._status_pills.append(pill)

            # col 2 – view btn
            view_btn = GhostBtn("👁  View", C['blue'])
            view_btn.clicked.connect(lambda _, r=i: self._on_view(r))
            vw = QWidget(); vw.setStyleSheet("background:transparent;")
            vl = QHBoxLayout(vw); vl.setContentsMargins(8,0,8,0)
            vl.addWidget(view_btn)
            self.table.setCellWidget(i, 2, vw)
            self._view_btns.append(view_btn)

            # col 3 – graph btn
            graph_btn = GhostBtn("↗  Graph", C['purple'])
            graph_btn.clicked.connect(lambda _, r=i: self._on_graph(r))
            gw = QWidget(); gw.setStyleSheet("background:transparent;")
            gl = QHBoxLayout(gw); gl.setContentsMargins(8,0,8,0)
            gl.addWidget(graph_btn)
            self.table.setCellWidget(i, 3, gw)
            self._graph_btns.append(graph_btn)

            # col 4 – result pill
            res_pill = StatusPill("N/A")
            rw = QWidget(); rw.setStyleSheet("background:transparent;")
            rl = QHBoxLayout(rw); rl.setContentsMargins(4,0,4,0)
            rl.addWidget(res_pill)
            self.table.setCellWidget(i, 4, rw)
            self._result_pills.append(res_pill)

        root.addWidget(self.table, 1)

        # ── stat bar ──────────────────────────────────────
        self._build_stat_bar(root)

        # callbacks (set by main window)
        self._cb_run_single = None
        self._cb_view = None
        self._cb_graph = None

    def _build_stat_bar(self, parent_layout):
        bar = QWidget()
        bar.setFixedHeight(72)
        bar.setStyleSheet(f"""
            background:{C['bg_card']};
            border:1px solid {C['border']};
            border-radius:10px;
        """)
        h = QHBoxLayout(bar)
        h.setContentsMargins(20, 8, 20, 8)
        h.setSpacing(0)

        self.stat_total   = StatCard("📋", "Total Test Cases", str(len(TEST_CASES)), C['blue'])
        self.stat_notrun  = StatCard("⬤",  "Not Run",          str(len(TEST_CASES)), C['text_secondary'])
        self.stat_pass    = StatCard("✓",  "Passed",           "0",                  C['green'])
        self.stat_fail    = StatCard("✗",  "Failed",           "0",                  C['red'])
        self.stat_warn    = StatCard("⚠",  "Warnings",         "0",                  C['orange'])

        for w in [self.stat_total, self.stat_notrun, self.stat_pass, self.stat_fail, self.stat_warn]:
            w.setStyleSheet("background:transparent; border:none;")
            h.addWidget(w, 1)

        # progress ring area
        sep = QFrame()
        sep.setFrameShape(QFrame.VLine)
        sep.setStyleSheet(f"color:{C['border']};")
        h.addWidget(sep)

        prog_w = QWidget()
        prog_w.setStyleSheet("background:transparent;")
        prog_w.setFixedWidth(120)
        pl = QVBoxLayout(prog_w)
        pl.setContentsMargins(10, 0, 10, 0)
        pl.setSpacing(2)
        self.prog_label = QLabel("0%")
        self.prog_label.setAlignment(Qt.AlignCenter)
        self.prog_label.setStyleSheet(f"font-size:20px; font-weight:700; color:{C['blue']};")
        sub = QLabel("Overall Progress")
        sub.setAlignment(Qt.AlignCenter)
        sub.setStyleSheet(f"font-size:10px; color:{C['text_secondary']};")
        pl.addStretch()
        pl.addWidget(self.prog_label)
        pl.addWidget(sub)
        pl.addStretch()
        h.addWidget(prog_w)

        parent_layout.addWidget(bar)

    def update_stats(self):
        total   = len(TEST_CASES)
        passed  = sum(1 for p in self._result_pills if p.text() == "PASS")
        failed  = sum(1 for p in self._result_pills if p.text() == "FAIL")
        warned  = sum(1 for p in self._result_pills if p.text() == "WARNING")
        notrun  = sum(1 for p in self._status_pills  if p.text() == "Not Run")
        done    = passed + failed + warned
        pct     = int(done / total * 100) if total else 0

        self.stat_total.set_value(str(total))
        self.stat_notrun.set_value(str(notrun))
        self.stat_pass.set_value(str(passed))
        self.stat_fail.set_value(str(failed))
        self.stat_warn.set_value(str(warned))
        self.prog_label.setText(f"{pct}%")

    # ── internal callbacks ────────────────────────────────
    def _on_run(self, row):
        if self._cb_run_single:
            self._cb_run_single(row)

    def _on_view(self, row):
        if self._cb_view:
            self._cb_view(row)

    def _on_graph(self, row):
        if self._cb_graph:
            self._cb_graph(row)

    def _filter_rows(self, text):
        text = text.lower()
        for i, name in enumerate(TEST_CASES):
            display = ("SoC BEHAVIOR + SoC STUCK" if i == 0 else name).lower()
            self.table.setRowHidden(i, text not in display and text not in "")

    # ── public helpers called by main window ──────────────
    def set_status(self, row: int, text: str):
        self._status_pills[row].set_status(text)
        self.update_stats()

    def set_result(self, row: int, text: str):
        self._result_pills[row].set_status(text)
        self.update_stats()

    def reset_row(self, row: int):
        self._status_pills[row].set_status("Not Run")
        self._result_pills[row].set_status("N/A")
        self.update_stats()

    def reset_all_rows(self):
        for i in range(len(TEST_CASES)):
            self.reset_row(i)


# -------------------------------------------------------
# SIDEBAR
# -------------------------------------------------------
class Sidebar(QFrame):
    page_changed = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(200)
        self.setStyleSheet(f"""
            QFrame {{
                background: {C['bg_sidebar']};
                border-right: 1px solid {C['border']};
                border-radius: 0px;
            }}
        """)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # logo
        logo_w = QWidget()
        logo_w.setFixedHeight(64)
        logo_w.setStyleSheet(f"background:{C['bg_app']}; border-bottom:1px solid {C['border']};")
        ll = QHBoxLayout(logo_w)
        ll.setContentsMargins(14, 0, 14, 0)
        icon_lbl = QLabel("◈")
        icon_lbl.setStyleSheet(f"color:{C['blue']}; font-size:22px; background:transparent;")
        title_col = QVBoxLayout()
        title_col.setSpacing(0)
        name = QLabel("CAN LOG ANALYSER")
        name.setStyleSheet(f"color:{C['text_primary']}; font-size:13px; font-weight:700; background:transparent;")
        self.ver_lbl = QLabel("v1.0.0")
        self.ver_lbl.setStyleSheet(f"color:{C['text_secondary']}; font-size:10px; background:transparent;")
        title_col.addWidget(name)
        title_col.addWidget(self.ver_lbl)
        ll.addWidget(icon_lbl)
        ll.addSpacing(8)
        ll.addLayout(title_col)
        lay.addWidget(logo_w)

        lay.addSpacing(10)

        # nav buttons
        pages = [
            ("⊞",  "Dashboard"),
            ("☑",  "Test Cases"),
            ("📄", "Reports"),
            ("📊", "Excel Tracker"),
            ("⚙",  "Settings"),
            ("ℹ",  "About"),
        ]
        self._btns = []
        for idx, (icon, label) in enumerate(pages):
            btn = SidebarBtn(icon, label)
            btn.clicked.connect(lambda _, i=idx: self._select(i))
            lay.addWidget(btn)
            self._btns.append(btn)

        lay.addStretch()

        # status dot
        status_w = QWidget()
        status_w.setFixedHeight(44)
        status_w.setStyleSheet("background:transparent;")
        sl = QHBoxLayout(status_w)
        sl.setContentsMargins(16, 0, 16, 0)
        dot = QLabel("●")
        dot.setStyleSheet(f"color:{C['green']}; font-size:10px; background:transparent;")
        stxt = QVBoxLayout()
        stxt.setSpacing(0)
        s1 = QLabel("System Ready")
        s1.setStyleSheet(f"color:{C['text_primary']}; font-size:11px; font-weight:600; background:transparent;")
        s2 = QLabel("All systems nominal")
        s2.setStyleSheet(f"color:{C['text_secondary']}; font-size:10px; background:transparent;")
        stxt.addWidget(s1)
        stxt.addWidget(s2)
        sl.addWidget(dot)
        sl.addSpacing(6)
        sl.addLayout(stxt)
        lay.addWidget(status_w)

        self._select(0)

    def _select(self, idx: int):
        for i, b in enumerate(self._btns):
            b.set_active(i == idx)
        self.page_changed.emit(idx)


# -------------------------------------------------------
# MAIN WINDOW
# -------------------------------------------------------
class CANLogDebugger(QWidget):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("CAN LOG ANALYSER")
        self.setMinimumSize(1280, 800)
        self.setStyleSheet(APP_STYLE)

        # ── state ──────────────────────────────────────────
        self.selected_file_path: str             = ""
        self.logs_last_output_path: Optional[str] = None
        self.script_dir    = os.path.dirname(os.path.realpath(__file__))
        self.default_tests_folder = os.path.join(self.script_dir, "TRC TEST CASES")
        self.tests_folder_overrides = {".csv": os.path.join(self.script_dir, "CSV TEST CASES")}
        self.tests_folder  = self._tests_folder_for_extension(".trc")
        self.vcu_reset_script = os.path.join(self.script_dir, "TRC TEST CASES", "ECU RESET", "VCU_Reset.py")
        self.vcu_reset_output = os.path.join(self.script_dir, "TRC TEST CASES", "ECU RESET", "VCU_Reset_Result.json")
        self.bms_reset_script = os.path.join(self.script_dir, "TRC TEST CASES", "ECU RESET", "BMS_Reset.py")
        self.bms_reset_output = os.path.join(self.script_dir, "TRC TEST CASES", "ECU RESET", "BMS_Reset_Result.json")

        self.scan_tasks    = 0
        self.processes:    Dict[int, QProcess] = {}
        self.running_rows: Set[int] = set()
        self.running_started_at: Dict[int, float] = {}
        self.running_pct:  Dict[int, float] = {}
        self.output_files  = self._load_output_config()
        self.pending_result_rows: Set[int] = set()

        self.result_refresh_timer = QTimer(self)
        self.result_refresh_timer.setInterval(1000)
        self.result_refresh_timer.timeout.connect(self._refresh_pending_results)

        # ── build UI ───────────────────────────────────────
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.sidebar = Sidebar()
        self.sidebar.page_changed.connect(self._on_page_changed)
        root.addWidget(self.sidebar)

        # content stack
        self.stack = QStackedWidget()
        self.stack.setStyleSheet("background: transparent;")
        root.addWidget(self.stack, 1)

        # page 0 = dashboard (left split)
        self._build_main_page()

        # pages 1-5 = placeholder cards
        placeholder_labels = ["Test Cases", "Reports", "Excel Tracker", "Settings", "About"]
        for lbl in placeholder_labels:
            ph = QWidget()
            ph.setStyleSheet(f"background:{C['bg_app']};")
            pl = QVBoxLayout(ph)
            t = QLabel(lbl)
            t.setAlignment(Qt.AlignCenter)
            t.setStyleSheet(f"font-size:24px; color:{C['text_secondary']};")
            pl.addWidget(t)
            self.stack.addWidget(ph)

        # version
        try:
            with open(os.path.join(self.script_dir, "version.txt")) as f:
                ver = f.read().strip().lstrip("vV") or "0.0.0"
        except Exception:
            ver = "0.0.0"
        self.sidebar.ver_lbl.setText(f"v{ver}")

        # wire up dashboard signals
        self.dash.browse_btn.clicked.connect(self.on_browse)
        self.dash.make_btn.clicked.connect(self.on_make_logs)
        self.dash.run_all_clicked.connect(self.start_all_tests)
        self.dash.generate_report.connect(self.generate_tracker)
        self.dash.generate_excel.connect(self.generate_excel_tracker)

        # wire up test-cases panel
        self.tc.  _cb_run_single = self.start_single_test
        self.tc.  _cb_view       = self.on_view_results
        self.tc.  _cb_graph      = self.on_view_graph

        # heartbeat
        self.heartbeat_timer = QTimer(self)
        self.heartbeat_timer.timeout.connect(send_heartbeat)
        self.heartbeat_timer.start(5000)

        # running animation timer
        self.anim_step = 0
        self.anim_timer = QTimer(self)
        self.anim_timer.setInterval(80)
        self.anim_timer.timeout.connect(self._tick_running_anim)
        self.anim_timer.start()

    def _build_main_page(self):
        page = QWidget()
        page.setStyleSheet(f"background:{C['bg_app']};")
        lay = QHBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # left panel
        left_wrapper = QFrame()
        left_wrapper.setFixedWidth(340)
        left_wrapper.setStyleSheet(f"""
            QFrame {{
                background: {C['bg_panel']};
                border-right: 1px solid {C['border']};
                border-radius: 0px;
            }}
        """)
        lw = QVBoxLayout(left_wrapper)
        lw.setContentsMargins(0, 0, 0, 0)
        self.dash = DashboardPanel()
        lw.addWidget(self.dash)
        lay.addWidget(left_wrapper)

        # right panel
        self.tc = TestCasesPanel()
        lay.addWidget(self.tc, 1)

        self.stack.addWidget(page)

    def _on_page_changed(self, idx: int):
        # page 0 is the main split page
        # pages 1-5 map to stack indices 1-5
        if idx == 0:
            self.stack.setCurrentIndex(0)
        elif idx == 1:
            # Switch to test-cases view (reuse main page, already there)
            self.stack.setCurrentIndex(0)
        else:
            self.stack.setCurrentIndex(idx)   # placeholders

    # ======================================================
    # UTILS
    # ======================================================
    def _tests_folder_for_extension(self, ext: str) -> str:
        return self.tests_folder_overrides.get((ext or "").lower(), self.default_tests_folder)

    def _set_tests_folder_for_extension(self, ext: str):
        nf = self._tests_folder_for_extension(ext)
        if nf != self.tests_folder:
            self.tests_folder = nf
            self.output_files = self._load_output_config()

    def _load_output_config(self) -> Dict[int, Dict[str, str]]:
        config_path = os.path.join(self.tests_folder, "file_name.json")
        config_data = {}
        if os.path.exists(config_path):
            try:
                with open(config_path) as f:
                    raw = json.load(f)
                config_data = {k.lower(): v for k, v in raw.items() if isinstance(v, dict)}
            except Exception:
                pass
        output_by_row: Dict[int, Dict[str, str]] = {}
        for row, script_name in SCRIPT_BY_ROW.items():
            test_name = TEST_CASES[row].lower()
            entry = config_data.get(test_name, {})
            defaults = self._default_output_names(script_name)
            output_by_row[row] = {
                "result":  entry.get("result",  defaults["result"]),
                "summary": entry.get("summary", defaults["summary"]),
                "graph":   entry.get("graph",   defaults["graph"]),
            }
        return output_by_row

    def _default_output_names(self, script_name: str) -> Dict[str, str]:
        base = os.path.splitext(script_name)[0]
        return {"result": f"{base}_results.json", "summary": f"{base}_summary.json", "graph": f"{base}_plot.png"}

    def _get_test_script_paths(self, row: int):
        script_name = SCRIPT_BY_ROW.get(row)
        if not script_name: return None, None
        folder_name = os.path.splitext(script_name)[0]
        folder_path = os.path.join(self.tests_folder, folder_name)
        script_path = os.path.join(folder_path, script_name)
        if not os.path.exists(script_path):
            fb_folder = os.path.join(self.default_tests_folder, folder_name)
            fb_script = os.path.join(fb_folder, script_name)
            if os.path.exists(fb_script):
                return fb_folder, fb_script
        return folder_path, script_path

    def _get_output_file_path(self, row: int, kind: str) -> Optional[str]:
        folder_path, _ = self._get_test_script_paths(row)
        if not folder_path: return None
        file_name = self.output_files.get(row, {}).get(kind)
        if not file_name: return None
        return os.path.join(folder_path, file_name)

    def _get_result_file_path(self, row: int):
        return self._get_output_file_path(row, "result")

    def _clear_all_outputs(self):
        for row in self.output_files:
            for kind in ("result", "summary", "graph"):
                p = self._get_output_file_path(row, kind)
                if p and os.path.exists(p):
                    try: os.remove(p)
                    except Exception: pass

    def _clear_outputs_for_row(self, row: int):
        for kind in ("result", "summary", "graph"):
            p = self._get_output_file_path(row, kind)
            if p and os.path.exists(p):
                try: os.remove(p)
                except Exception: pass

    def _register_scan_task(self):
        self.scan_tasks += 1

    def _on_scan_finished(self):
        self.scan_tasks = max(0, self.scan_tasks - 1)
        if self.scan_tasks == 0:
            self.dash.browse_btn.setText("☁  Browse File\nor drag and drop")
            self.dash.browse_btn.setEnabled(True)

    def _ensure_result_timer_running(self):
        if self.pending_result_rows:
            if not self.result_refresh_timer.isActive():
                self.result_refresh_timer.start()
        elif self.result_refresh_timer.isActive():
            self.result_refresh_timer.stop()

    def _refresh_pending_results(self):
        for row in list(self.pending_result_rows):
            self.update_result_cell(row)
        self._ensure_result_timer_running()

    def _maybe_finish_run_all(self):
        if any(p.state() != QProcess.NotRunning for p in self.processes.values()):
            return
        if self.pending_result_rows:
            return
        self.dash.run_all_btn.setEnabled(True)
        self.dash.run_all_btn.setText("  ▶  RUN ALL TEST CASES")

    def _tick_running_anim(self):
        self.anim_step = (self.anim_step + 1) % 100
        for row in list(self.running_rows):
            pct = self.running_pct.get(row)
            txt = f"Running {pct:.1f}%" if pct is not None else "Running…"
            self.tc._status_pills[row].setText(txt)

    # ======================================================
    # FILE BROWSE
    # ======================================================
    def on_browse(self):
        ft = self.dash.ft_combo.currentText()
        initial_dir = ""
        if self.logs_last_output_path:
            initial_dir = os.path.dirname(self.logs_last_output_path)
        elif self.selected_file_path:
            initial_dir = os.path.dirname(self.selected_file_path)
        else:
            home = os.path.expanduser("~")
            for d in [os.path.join(home, "Downloads"), os.path.join(home, "Desktop"), home]:
                if os.path.isdir(d): initial_dir = d; break

        path, _ = QFileDialog.getOpenFileName(self, "Select File", initial_dir, f"{ft} Files (*{ft})")
        if not path: return
        self._handle_file_selected(path)

    def _handle_file_selected(self, path: str):
        ext = os.path.splitext(path)[1].lower()
        self._set_tests_folder_for_extension(ext)
        self.selected_file_path = path
        self.dash.file_box.setText(path)
        self.dash.run_all_btn.setEnabled(True)

        self.scan_tasks = 0
        self.dash.browse_btn.setEnabled(False)
        self.dash.browse_btn.setText("Scanning…")

        self._start_fw_scan(path)
        if ext == ".trc":
            self._start_mcu_detection(path)
            self._start_vcu_reset_check(path, track_scan=True)
            self._start_bms_reset_check(path, track_scan=True)
        else:
            self.reset_vcu_fields()
            self.reset_bms_fields()
            for fw in [self.dash.fw_mcu, self.dash.fw_serial, self.dash.fw_os]:
                fw.set_value("N/A")

    # ── FW ────────────────────────────────────────────────
    def _start_fw_scan(self, path: str):
        t = FWCheckerThread(path); self.fw_thread = t
        self._register_scan_task()
        t.finished_ok.connect(self.update_fw_info)
        t.finished_err.connect(self.on_fw_error)
        t.finished.connect(self._on_scan_finished)
        t.start()

    def update_fw_info(self, info):
        self.dash.fw_hw.set_value(info.get("BMS_HW", ""))
        self.dash.fw_fw.set_value(info.get("BMS_FIRMWARE", ""))
        self.dash.fw_cfg.set_value(info.get("BMS_CONFIG_ID", ""))
        self.dash.fw_git.set_value(info.get("BMS_GITSHA", ""))
        self.dash.fw_manifest.set_value(info.get("BMS_MANIFEST", ""))
        self.dash.fw_stark_fw.set_value(info.get("STARK_FIRMWARE", ""))
        self.dash.fw_stark_cfg.set_value(info.get("STARK_CONFIG", ""))
        self.dash.fw_xavier_fw.set_value(info.get("XAVIER_FIRMWARE", ""))
        dist = info.get("DISTANCE_COVERED_KM", info.get("DISTANCE_COVERED", ""))
        try: dist = f"{float(dist):.1f} km"
        except Exception: dist = f"{dist} km" if dist else ""
        self.dash.fw_distance.set_value(dist)

    def on_fw_error(self, err):
        QMessageBox.warning(self, "FW Error", err)

    # ── MCU ───────────────────────────────────────────────
    def _start_mcu_detection(self, path: str):
        for fw in [self.dash.fw_mcu, self.dash.fw_serial, self.dash.fw_os]:
            fw.set_value("…")
        t = MCUDetectionThread(path, self.script_dir); self.mcu_thread = t
        self._register_scan_task()
        t.finished_ok.connect(self.update_mcu_fields)
        t.finished_err.connect(self.on_mcu_error)
        t.finished.connect(self._on_scan_finished)
        t.start()

    def update_mcu_fields(self, info: dict):
        self.dash.fw_mcu.set_value(info.get("platform", "N/A"))
        self.dash.fw_serial.set_value(info.get("serial", "N/A"))
        self.dash.fw_os.set_value(f"{info.get('os_version','N/A')} & {info.get('os_build','N/A')}")

    def on_mcu_error(self, _):
        for fw in [self.dash.fw_mcu, self.dash.fw_serial, self.dash.fw_os]:
            fw.set_value("N/A")

    # ── VCU reset ─────────────────────────────────────────
    def _start_vcu_reset_check(self, path: str, track_scan: bool):
        if not os.path.exists(self.vcu_reset_script):
            self.reset_vcu_fields(); return
        self.dash.tx_vcu_value.setText("…")
        self.dash.tx_vcu_result.setText("…")
        t = VCUResetThread(path, self.vcu_reset_script, self.vcu_reset_output)
        if track_scan: self._register_scan_task()
        t.finished_ok.connect(self.update_vcu_reset_fields)
        t.finished_err.connect(self.on_vcu_reset_error)
        t.finished.connect(lambda: self._on_scan_finished() if track_scan else None)
        t.start(); self.vcu_thread = t

    def update_vcu_reset_fields(self, data: dict):
        count = data.get("Reset_Count", 0)
        result = str(data.get("Result", "")).strip().upper() or ("PASS" if count == 0 else "FAIL")
        self.dash.tx_vcu_value.setText(f"Count : {count}")
        self.dash.tx_vcu_result.setText(result)
        self.dash.tx_vcu_value.setAlignment(Qt.AlignCenter)
        self.dash.tx_vcu_result.setAlignment(Qt.AlignCenter)
        self._style_result_box(self.dash.tx_vcu_result, result)
        self._style_result_box(self.dash.tx_vcu_value, result)

    def on_vcu_reset_error(self, msg):
        self.reset_vcu_fields()

    def reset_vcu_fields(self):
        self.dash.tx_vcu_value.setText("Count : N/A")
        self.dash.tx_vcu_result.setText("N/A")
        for w in [self.dash.tx_vcu_value, self.dash.tx_vcu_result]:
            w.setStyleSheet(f"QLineEdit {{ background:{C['bg_input']}; border:none; color:{C['text_secondary']}; font-weight:normal; text-align:center; }}")
            w.setAlignment(Qt.AlignCenter)

    # ── BMS reset ─────────────────────────────────────────
    def _start_bms_reset_check(self, path: str, track_scan: bool, manual: bool = False):
        if not path:
            self.reset_bms_fields(); return
        if not os.path.exists(self.bms_reset_script):
            self.reset_bms_fields(); return
        if os.path.splitext(path)[1].lower() != ".trc":
            self.reset_bms_fields(); return
        self.dash.tx_bms_value.setText("…")
        self.dash.tx_bms_result.setText("…")
        t = BMSResetThread(path, self.bms_reset_script, self.bms_reset_output)
        if track_scan: self._register_scan_task()
        t.finished_ok.connect(self.update_bms_reset_fields)
        t.finished_err.connect(self.on_bms_reset_error)
        t.finished.connect(lambda: self._on_scan_finished() if track_scan else None)
        t.start(); self.bms_thread = t

    def update_bms_reset_fields(self, data: dict):
        count = data.get("Reset_Count", 0)
        result = str(data.get("Result", "")).strip().upper() or ("PASS" if count == 0 else "FAIL")
        self.dash.tx_bms_value.setText(f"Count : {count}")
        self.dash.tx_bms_result.setText(result)
        self.dash.tx_bms_value.setAlignment(Qt.AlignCenter)
        self.dash.tx_bms_result.setAlignment(Qt.AlignCenter)
        self._style_result_box(self.dash.tx_bms_result, result)
        self._style_result_box(self.dash.tx_bms_value, result)

    def on_bms_reset_error(self, _):
        self.reset_bms_fields()

    def reset_bms_fields(self):
        self.dash.tx_bms_value.setText("Count : N/A")
        self.dash.tx_bms_result.setText("N/A")
        for w in [self.dash.tx_bms_value, self.dash.tx_bms_result]:
            w.setStyleSheet(f"QLineEdit {{ background:{C['bg_input']}; border:none; color:{C['text_secondary']}; font-weight:normal; text-align:center; }}")
            w.setAlignment(Qt.AlignCenter)

    def _style_result_box(self, widget: QLineEdit, result: str):
        if result == "PASS":
            widget.setStyleSheet(f"QLineEdit {{ background:{C['pass']}; color:{C['pass_fg']}; font-weight:700; border-radius:6px; padding:4px; text-align:center; }}")
        elif result == "FAIL":
            widget.setStyleSheet(f"QLineEdit {{ background:{C['fail']}; color:{C['fail_fg']}; font-weight:700; border-radius:6px; padding:4px; text-align:center; }}")
        else:
            widget.setStyleSheet(f"QLineEdit {{ background:{C['bg_input']}; color:{C['text_secondary']}; border:none; border-radius:6px; padding:4px; text-align:center; }}")
        widget.setAlignment(Qt.AlignCenter)

    # ======================================================
    # MAKE LOGS
    # ======================================================
    def on_make_logs(self):
        logs_script = os.path.join(self.script_dir, "logs_organised.py")
        if not os.path.exists(logs_script):
            QMessageBox.warning(self, "Error", f"logs_organised.py not found:\n{logs_script}"); return

        self.logs_last_output_path = None
        self.dash.make_btn.setText("⏳  Running… Please wait")
        self.dash.make_btn.setEnabled(False)

        home = os.path.expanduser("~")
        initial_dir = next((d for d in [os.path.join(home, "Downloads"), os.path.join(home, "Desktop"), home] if os.path.isdir(d)), "C:/")

        self.logs_proc = QProcess(self)
        self.logs_proc.setWorkingDirectory(self.script_dir)
        self.logs_proc.finished.connect(self.on_logs_finished)
        self.logs_proc.readyReadStandardOutput.connect(self._on_logs_stdout)
        self.logs_proc.start(sys.executable, [logs_script, initial_dir])

    def on_logs_finished(self):
        self.dash.make_btn.setText("✅  Logs Organised — Retry?")
        self.dash.make_btn.setEnabled(True)
        marker = os.path.join(self.script_dir, "last_merged_trc.txt")
        if os.path.exists(marker):
            try:
                candidate = open(marker, encoding="utf-8", errors="ignore").read().strip()
                if candidate and os.path.exists(candidate):
                    self.logs_last_output_path = candidate
            except Exception: pass

    def _on_logs_stdout(self):
        proc = getattr(self, "logs_proc", None)
        if not proc: return
        try:
            data = proc.readAllStandardOutput().data().decode("utf-8", errors="ignore")
        except Exception: return
        for line in data.splitlines():
            m = re.search(r"Output file saved as:\s*(.+)", line)
            if m:
                c = m.group(1).strip()
                if c: self.logs_last_output_path = c

    # ======================================================
    # RUN ALL
    # ======================================================
    def start_all_tests(self):
        if not self.selected_file_path:
            QMessageBox.warning(self, "Error", "Browse a file first"); return
        if any(p.state() != QProcess.NotRunning for p in self.processes.values()):
            QMessageBox.information(self, "Info", "Tests are already running."); return

        if CLEAR_OUTPUTS_ON_RUN_ALL:
            self._clear_all_outputs()

        self.dash.run_all_btn.setEnabled(False)
        self.dash.run_all_btn.setText("⏳  Running…")
        self.tc.reset_all_rows()

        self.pending_result_rows.clear()
        self._ensure_result_timer_running()
        self.processes.clear()
        self.running_rows.clear()
        self.running_started_at.clear()
        self.running_pct.clear()

        python = sys.executable
        for row, script in SCRIPT_BY_ROW.items():
            folder_path, script_path = self._get_test_script_paths(row)
            if not folder_path or not os.path.exists(script_path):
                self.tc.set_status(row, "Error"); continue

            self.pending_result_rows.add(row)
            self._ensure_result_timer_running()
            self.running_rows.add(row)
            self.running_started_at[row] = time.time()
            self.tc.set_status(row, "Running")

            proc = QProcess(self)
            proc.setWorkingDirectory(folder_path)
            proc.finished.connect(lambda ec, _s, r=row: self.on_test_finished(r, ec))
            proc.errorOccurred.connect(lambda _e, r=row: self.on_test_error(r))
            proc.readyReadStandardOutput.connect(lambda r=row: self._on_test_stdout(r))
            proc.start(python, [script, self.selected_file_path])
            self.processes[row] = proc

        if not self.processes:
            self.dash.run_all_btn.setEnabled(True)
            self.dash.run_all_btn.setText("  ▶  RUN ALL TEST CASES")

    # ======================================================
    # RUN SINGLE
    # ======================================================
    def start_single_test(self, row: int):
        if not self.selected_file_path:
            QMessageBox.warning(self, "Error", "Browse a file first"); return
        proc = self.processes.get(row)
        if proc and proc.state() != QProcess.NotRunning:
            QMessageBox.information(self, "Info", "This test is already running."); return

        if CLEAR_OUTPUTS_ON_RUN_ALL:
            self._clear_outputs_for_row(row)

        self.tc.reset_row(row)
        folder_path, script_path = self._get_test_script_paths(row)
        if not folder_path or not os.path.exists(script_path):
            self.tc.set_status(row, "Error"); return

        self.pending_result_rows.add(row)
        self._ensure_result_timer_running()
        self.running_rows.add(row)
        self.running_started_at[row] = time.time()
        self.running_pct.pop(row, None)
        self.tc.set_status(row, "Running")

        proc = QProcess(self)
        proc.setWorkingDirectory(folder_path)
        proc.finished.connect(lambda ec, _s, r=row: self.on_test_finished(r, ec))
        proc.errorOccurred.connect(lambda _e, r=row: self.on_test_error(r))
        proc.readyReadStandardOutput.connect(lambda r=row: self._on_test_stdout(r))
        proc.start(sys.executable, [script_path, self.selected_file_path])
        self.processes[row] = proc

    def on_test_finished(self, row, exitCode):
        self.running_rows.discard(row)
        self.running_started_at.pop(row, None)
        self.running_pct.pop(row, None)
        if exitCode == 0:
            self.tc.set_status(row, "Completed")
        else:
            self.tc.set_status(row, "Error")
        if not self.update_result_cell(row):
            self._schedule_result_update(row)
        self._maybe_finish_run_all()

    def on_test_error(self, row):
        self.running_rows.discard(row)
        self.running_started_at.pop(row, None)
        self.running_pct.pop(row, None)
        self.tc.set_status(row, "Error")
        self._maybe_finish_run_all()

    def _on_test_stdout(self, row: int):
        proc = self.processes.get(row)
        if not proc: return
        try:
            data = proc.readAllStandardOutput().data().decode("utf-8", errors="ignore")
        except Exception: return
        for line in data.splitlines():
            if not line.startswith("PROGRESS"): continue
            parts = line.strip().split()
            if len(parts) < 2: continue
            try:
                pct = max(0.0, min(99.9, float(parts[1])))
                if pct >= self.running_pct.get(row, 0.0):
                    self.running_pct[row] = pct
            except Exception: pass

    def update_result_cell(self, row: int) -> bool:
        path = self._get_result_file_path(row)
        if not path or not os.path.exists(path): return False
        try:
            with open(path) as f:
                data = json.load(f)
            result_str = str(data.get("Result", "")).strip().upper()
        except Exception: return False

        if result_str in ("PASS", "FAIL", "WARNING"):
            self.tc.set_result(row, result_str)
            status_item = self.tc._status_pills[row]
            if status_item.text() not in ("Completed",):
                self.tc.set_status(row, "Completed")
            self.pending_result_rows.discard(row)
            self._ensure_result_timer_running()
            self._maybe_finish_run_all()
            return True
        return False

    def _schedule_result_update(self, row: int, attempts=RESULT_POLL_ATTEMPTS, delay_ms=RESULT_POLL_DELAY_MS):
        if attempts <= 0:
            self.pending_result_rows.discard(row)
            self._ensure_result_timer_running()
            return
        QTimer.singleShot(delay_ms, lambda r=row, a=attempts-1, d=delay_ms: self._retry_result_update(r, a, d))

    def _retry_result_update(self, row, attempts, delay_ms):
        if self.update_result_cell(row): return
        self._schedule_result_update(row, attempts, delay_ms)

    # ======================================================
    # VIEW RESULT / GRAPH
    # ======================================================
    def on_view_results(self, idx):
        self.update_result_cell(idx)
        summary_path = self._get_output_file_path(idx, "summary")
        if not summary_path:
            QMessageBox.information(self, "Info", "No summary file configured."); return
        dlg = JsonDialog(summary_path, self)
        dlg.exec()

    def on_view_graph(self, idx):
        graph_path = self._get_output_file_path(idx, "graph")
        if not graph_path:
            QMessageBox.information(self, "Info", "No graph configured."); return
        if not os.path.exists(graph_path):
            QMessageBox.information(self, "Info", f"File not found:\n{graph_path}"); return

        for viewer in [r"C:\Program Files (x86)\Microsoft Office\Office12\OIS.EXE",
                       r"C:\Program Files\Microsoft Office\Office12\OIS.EXE"]:
            if os.path.exists(viewer):
                try: subprocess.Popen([viewer, graph_path]); return
                except Exception: pass
        try:
            os.startfile(graph_path)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to open graph:\n{e}")

    # ======================================================
    # GENERATE TRACKER
    # ======================================================
    def _meta_payload(self):
        return {
            "VEHICLE NAME":   os.path.basename(self.selected_file_path),
            "BMS HW VERSION": self.dash.fw_hw.get_value(),
            "BMS FIRMWARE":   self.dash.fw_fw.get_value(),
            "BMS CONFIG ID":  self.dash.fw_cfg.get_value(),
            "BMS GITSHA":     self.dash.fw_git.get_value(),
            "BMS MANIFEST":   self.dash.fw_manifest.get_value(),
            "STARK FIRMWARE": self.dash.fw_stark_fw.get_value(),
            "STARK CONFIG":   self.dash.fw_stark_cfg.get_value(),
            "XAVIER FIRMWARE":self.dash.fw_xavier_fw.get_value(),
            "DISTANCE COVERED":self.dash.fw_distance.get_value(),
            "VCU Reset Count":self.dash.tx_vcu_value.text(),
            "VCU Reset Result":self.dash.tx_vcu_result.text(),
            "BMS Reset Count":self.dash.tx_bms_value.text(),
            "BMS Reset Result":self.dash.tx_bms_result.text(),
        }

    def generate_tracker(self):
        if not self.selected_file_path:
            QMessageBox.warning(self, "Error", "No file selected!"); return
        docx_path = os.path.join(self.script_dir, "tracker_summary.docx")
        gen_script = os.path.join(self.script_dir, "Generate_Tracker.py")
        if not os.path.exists(gen_script):
            QMessageBox.warning(self, "Tracker", f"Generate_Tracker.py not found:\n{gen_script}"); return
        env = os.environ.copy()
        env["META_JSON"] = json.dumps(self._meta_payload())
        env["SELECTED_FILE_NAME"] = os.path.basename(self.selected_file_path)
        try:
            proc = subprocess.run([sys.executable, gen_script, docx_path, self.tests_folder],
                                  cwd=self.script_dir, capture_output=True, text=True, env=env)
        except Exception as e:
            QMessageBox.warning(self, "Tracker", f"Failed:\n{e}"); return
        if proc.returncode != 0:
            QMessageBox.warning(self, "Tracker", proc.stderr.strip() or proc.stdout.strip() or "Error."); return
        reply = QMessageBox.question(self, "Tracker", f"Generated:\n{docx_path}\n\nOpen it?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
        if reply == QMessageBox.Yes:
            try:
                if sys.platform.startswith("win"): os.startfile(docx_path)
                elif sys.platform == "darwin": subprocess.Popen(["open", docx_path])
                else: subprocess.Popen(["xdg-open", docx_path])
            except Exception as e:
                QMessageBox.warning(self, "Tracker", f"Failed to open:\n{e}")

    def generate_excel_tracker(self):
        if not self.selected_file_path:
            QMessageBox.warning(self, "Error", "No file selected!"); return
        excel_path = os.path.join(self.script_dir, "TRACKER.xlsx")
        gen_script = os.path.join(self.script_dir, "Excel_Tracker.py")
        if not os.path.exists(gen_script):
            QMessageBox.warning(self, "Excel Tracker", f"Excel_Tracker.py not found:\n{gen_script}"); return
        env = os.environ.copy()
        env["META_JSON"] = json.dumps(self._meta_payload())
        env["SELECTED_FILE_NAME"] = os.path.basename(self.selected_file_path)
        try:
            proc = subprocess.run([sys.executable, gen_script, excel_path, self.tests_folder],
                                  cwd=self.script_dir, capture_output=True, text=True, env=env)
        except Exception as e:
            QMessageBox.warning(self, "Excel Tracker", f"Failed:\n{e}"); return
        if proc.returncode != 0:
            QMessageBox.warning(self, "Excel Tracker", proc.stderr.strip() or proc.stdout.strip() or "Error."); return
        reply = QMessageBox.question(self, "Excel Tracker", f"Generated:\n{excel_path}\n\nOpen it?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
        if reply == QMessageBox.Yes:
            try:
                if sys.platform.startswith("win"): os.startfile(excel_path)
                elif sys.platform == "darwin": subprocess.Popen(["open", excel_path])
                else: subprocess.Popen(["xdg-open", excel_path])
            except Exception as e:
                QMessageBox.warning(self, "Excel Tracker", f"Failed to open:\n{e}")


# -------------------------------------------------------
# HEARTBEAT / KILL SWITCH  (unchanged)
# -------------------------------------------------------
def send_heartbeat():
    try:
        requests.post(
            "https://heartbeat-server-1z5n.onrender.com/heartbeat",
            json={"device": socket.gethostname(),
                  "name": os.environ.get("USERNAME", "unknown"),
                  "status": "running"},
            timeout=2)
    except Exception:
        pass


def check_kill_switch():
    url = "https://raw.githubusercontent.com/itssatishkumar/Runner/main/runner.txt"
    try:
        with urllib.request.urlopen(url, timeout=5) as r:
            return r.read().decode().strip().upper() == "TRUE"
    except Exception:
        return False


# -------------------------------------------------------
# ENTRY POINT
# -------------------------------------------------------
def run_updater_first(app: QApplication):
    version_file = os.path.join(os.path.dirname(__file__), "version.txt")
    try:
        with open(version_file) as f:
            local_version = f.read().strip() or "1.0.0"
    except Exception:
        local_version = "1.0.0"
    try:
        from updater import check_for_update
        check_for_update(local_version=local_version, app=app)
    except ImportError:
        pass


def main():
    if check_kill_switch():
        runner_path = os.path.join(os.path.dirname(__file__), "runner.py")
        if os.path.exists(runner_path):
            kwargs = {"creationflags": subprocess.CREATE_NEW_CONSOLE} if sys.platform == "win32" else {}
            subprocess.Popen([sys.executable, runner_path], **kwargs)
        time.sleep(2)
        sys.exit(0)

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    run_updater_first(app)
    w = CANLogDebugger()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

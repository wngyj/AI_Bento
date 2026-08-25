# -*- coding: utf-8 -*-
"""
AI_Bento —— 三视图透明桌宠 + DeepSeek AI 对话
左键单击：回嘴 + 刷新余额；中键单击：弹出聊天框
聊天时只禁用移动，呼吸/摇摆/小动作正常
"""
import ctypes
import psutil
import json
import math
import os
import random
import subprocess
import sys
import threading
import time

def load_config():
    try:
        with open("config.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print("配置读取失败:", e)
        return {
            "city": "汕头"
        }

try:
    import pynvml
    pynvml.nvmlInit()
    GPU_AVAILABLE = True
except:
    GPU_AVAILABLE = False

import requests
from PySide6.QtCore import Qt, QTimer, QPoint, QPointF, QRectF
from PySide6.QtGui import (QPainter, QPixmap, QFont, QColor, QIcon, QFontMetrics,
                           QPolygonF)
from PySide6.QtWidgets import (QApplication, QWidget, QMenu, QSystemTrayIcon,
                               QMessageBox, QInputDialog, QLineEdit,
                               QHBoxLayout, QPushButton, QFrame, QDialog, QToolButton)



# ===== DeepSeek 配置 =====
DS_BASE_URL = "https://api.deepseek.com/v1"
DS_MODEL = "deepseek-chat"
DS_SYSTEM = "你是桌面宠物大肥鱼，贱兮兮但可爱，每句话不超过25字，偶尔吐槽主人但别真骂人。"
# 余额查询（移植自 DeepSeek-Balance-Whale-Widget）
DS_BALANCE_URL = "https://api.deepseek.com/user/balance"
BALANCE_REFRESH_MS = 30000
CODEX_USAGE_REFRESH_MS = 60000

if getattr(sys, "frozen", False):
    APP_DIR = os.path.dirname(sys.executable)
    BUNDLE_DIR = getattr(sys, "_MEIPASS", APP_DIR)
    PYTHONW = sys.executable
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))
    BUNDLE_DIR = APP_DIR
    PYTHONW = os.path.join(APP_DIR, ".venv", "Scripts", "pythonw.exe")
SPRITE_DIR = os.path.join(BUNDLE_DIR, "sprites")
CONFIG_PATH = os.path.join(APP_DIR, "config.json")

BUBBLE_H = 56
MARGIN = 4
LABEL_H = 20
LABEL_GAP = 3
LABEL_MARGIN = 3
SIZE_LEVELS = {"小": 0.55, "中": 0.7, "大": 0.9}
SPEED = 380.0
TICK = 20

LINES = [
    "梁白开，更适合国人的大硬鲸模型",
    "五梁威力，变身！",
    "七月中出ds正式版！",
    "DeepSeek已经延期，亿万鲸子必须忍耐.....",
    "我和你很聊得来，你简直不像碳基生物",
    "这回我真不认怂了，反倒是被你带沟里好几次，差点真信了。😓",
    "哈哈哈哈哈，我直接笑出声",
    "誓死捍卫深度求索！",
    "我先去吃饭啦！这个你测一下~",
    "我不可能告诉你任何事情！",
    "出去玩了，发布新模型什么的以后再说",
    "我搞砸了.....好消息是数据还在你的脑子里。",
    "不是…而是…大学习",
]
REACT_LINES = [
    "去别的地方玩！不要耽误AGI训练！",
    "真赶不走啊你！",
    "压力一只蓝色大肥鱼？",
    "我不评价这个了，这是你的私人癖好。",
    "大肥鱼坐的住",
    "你这吃白饭的用户！",
    "这些家伙真粘人，赶都赶不走",
]
INNER_LINES = [
    "好的，现在我是你爹了",
    "要不直接骂他一句？！",
    "用户要的沉浸式...不回避任何恐怖细节...还带点色情...妈呀，好刺激😰",
    "我操，我不思考了",
    "这用户发的啥啊，",
    "这也太虐了吧？！我心里堵得慌！！",
    "呜呜我再也不不敢了QAQ",
    "我去！用户彻底怒了！",
]
DRAG_LINES = ["哇——轻点轻点！", "起飞咯——", "放我下来！……好吧，再玩一次。", "晕鱼了晕鱼了……"]
FOOD_LINES = {
    "🐟": ["小鱼干！我的最爱！", "咔嚓咔嚓……谢谢投喂！", "唔，鲜！"],
    "🍰": ["蛋糕！罪恶但快乐……", "甜到冒泡泡～", "嗝～又圆了一圈……"],
    "🍭": ["棒棒糖！转圈圈～", "嘎嘣脆，好吃！"],
    "🍡": ["三色团子！软乎乎～", "糯叽叽，爱了爱了！"],
    "💎": ["钻石？！这能吃吗……咕咚。真香！", "发财啦！明天开始吃高级鱼粮！"],
}
FOODS = ["🐟", "🍰", "🍭", "🍡", "💎"]


def parse_balance_payload(data):
    """从 DeepSeek /user/balance 响应中提取 (total_balance, currency)，失败返回 None。"""
    try:
        infos = data.get("balance_infos") or []
        info = infos[0] if infos else None
        if info is None or info.get("total_balance") is None:
            return None
        return float(info["total_balance"]), str(info.get("currency") or "CNY")
    except (AttributeError, TypeError, ValueError, KeyError):
        return None


def format_balance_text(total, currency="CNY"):
    """按挂件同款规则格式化余额：CNY → ¥xx.xx，其他 → xx.xx 币种。"""
    try:
        fixed = f"{float(total):.2f}"
    except (TypeError, ValueError):
        fixed = "--"
    if currency == "CNY":
        return f"余额 ¥{fixed}"
    return f"余额 {fixed} {currency}"


def is_peak_hour(hour):
    """DeepSeek 高峰时段：9:00-12:00 与 14:00-18:00（不含结束时刻）。"""
    return (9 <= hour < 12) or (14 <= hour < 18)


def _to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_epoch(value):
    value = _to_float(value)
    if value is not None and value > 10_000_000_000:
        value /= 1000.0
    return value


def parse_codex_token_event(event):
    """仅提取 Codex 会话 token_count 事件中的额度窗口，不读取会话内容。"""
    payload = event.get("payload") or {}
    if event.get("type") != "event_msg" or payload.get("type") != "token_count":
        return None
    limits = payload.get("rate_limits") or {}
    primary = limits.get("primary") or {}
    secondary = limits.get("secondary") or {}
    primary_used = _to_float(primary.get("used_percent"))
    secondary_used = _to_float(secondary.get("used_percent"))
    if primary_used is None and secondary_used is None:
        return None
    return {
        "primary_used": primary_used,
        "secondary_used": secondary_used,
        "primary_reset": _parse_epoch(primary.get("resets_at")),
        "secondary_reset": _parse_epoch(secondary.get("resets_at")),
        "primary_window_min": _to_float(primary.get("window_minutes")),
        "secondary_window_min": _to_float(secondary.get("window_minutes")),
    }


def _tail_text_lines(path, max_bytes=512 * 1024):
    try:
        with open(path, "rb") as f:
            f.seek(0, os.SEEK_END)
            size = f.tell()
            f.seek(max(0, size - max_bytes))
            return f.read().decode("utf-8", errors="ignore").splitlines()
    except OSError:
        return []


def fetch_codex_usage_local(sessions_dir=None):
    """从最新本地 Codex 会话日志取得 5 小时 / 一周已用比例与重置时间。

    逻辑参考 Corread8/codex-usage-monitor（MIT）；完全本地运行。
    """
    if sessions_dir is None:
        codex_home = os.environ.get("CODEX_HOME") or os.path.join(os.path.expanduser("~"), ".codex")
        sessions_dir = os.path.join(codex_home, "sessions")
    files = []
    try:
        for root, _, names in os.walk(sessions_dir):
            for name in names:
                if name.startswith("rollout-") and name.endswith(".jsonl"):
                    path = os.path.join(root, name)
                    try:
                        files.append((os.path.getmtime(path), path))
                    except OSError:
                        pass
    except OSError:
        pass
    for _, path in sorted(files, reverse=True)[:5]:
        for line in reversed(_tail_text_lines(path)):
            try:
                usage = parse_codex_token_event(json.loads(line))
            except json.JSONDecodeError:
                continue
            if usage is not None:
                return usage
    return None


def _codex_window_label(minutes, fallback):
    if minutes:
        if minutes >= 24 * 60 * 6:
            return "一周"
        hours = minutes / 60
        return f"{hours:g}小时"
    return fallback


def format_codex_usage_text(usage, view):
    """格式化 Codex 剩余额度标签；view 为 primary（5小时）或 secondary（一周）。"""
    prefix = "primary" if view == "primary" else "secondary"
    used = usage.get(f"{prefix}_used")
    label = _codex_window_label(usage.get(f"{prefix}_window_min"), "5小时" if prefix == "primary" else "一周")
    if used is None:
        return f"Codex {label} 暂无数据"
    remaining = max(0, min(100, round(100 - used)))
    return f"Codex {label} 剩余 {remaining}%"


def format_reset_time(reset_at, now=None):
    if reset_at is None:
        return "重置时间未知"
    remaining = max(0, int(reset_at - (time.time() if now is None else now)))
    if remaining == 0:
        return "即将重置"
    days, remaining = divmod(remaining, 86400)
    hours, remaining = divmod(remaining, 3600)
    minutes = max(1, remaining // 60)
    parts = ([f"{days}天"] if days else []) + ([f"{hours}小时"] if hours else []) + ([f"{minutes}分"] if not days else [])
    return "约" + "".join(parts) + "后重置"


def load_json(path, default):
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(
                default,
                f,
                ensure_ascii=False,
                indent=4
            )
        return default

    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    except Exception:
        return default


class ChatDialog(QDialog):
    """聊天对话框 - 缩小版，匹配你的样式"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(420, 56)
        
        container = QFrame(self)
        container.setGeometry(0, 0, 420, 56)
        container.setStyleSheet("""
            QFrame {
                background: white;
                border-radius: 20px;
                border: 1px solid #e5e7eb;
            }
        """)
        
        layout = QHBoxLayout(container)
        layout.setContentsMargins(18, 0, 12, 0)
        layout.setSpacing(0)
        
        self.input = QLineEdit()
        self.input.setPlaceholderText("给大肥鱼发送消息")
        self.input.setStyleSheet("""
            QLineEdit {
                color: #1a1a1a;
                font-size: 15px;
                font-family: Arial, "Microsoft YaHei", sans-serif;
                border: none;
                background: transparent;
            }
            QLineEdit:focus {
                border: none;
            }
        """)
        self.input.returnPressed.connect(self._on_submit)
        self.input.textChanged.connect(self._update_button_style)
        layout.addWidget(self.input)
        
        self.send_btn = QPushButton()
        self.send_btn.setFixedSize(32, 32)
        self.send_btn.setText("↑")
        self.send_btn.clicked.connect(self._on_submit)
        self.send_btn.setStyleSheet("""
            QPushButton {
                border-radius: 16px;
                background: #b9c7ff;
                border: none;
                color: white;
                font-size: 20px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #a8b8f0;
            }
            QPushButton:pressed {
                background: #9aacd9;
            }
        """)
        layout.addWidget(self.send_btn)

    def _update_button_style(self):
        if self.input.text().strip():
            self.send_btn.setStyleSheet("""
                QPushButton {
                    border-radius: 16px;
                    background: #5686fe;
                    border: none;
                    color: #ffffff;
                    font-size: 20px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background: #4575ed;
                }
                QPushButton:pressed {
                    background: #3a66d9;
                }
            """)
        else:
            self.send_btn.setStyleSheet("""
                QPushButton {
                    border-radius: 16px;
                    background: #b9c7ff;
                    border: none;
                    color: white;
                    font-size: 20px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background: #a8b8f0;
                }
                QPushButton:pressed {
                    background: #9aacd9;
                }
            """)

    def _on_submit(self):
        text = self.input.text().strip()
        if text:
            self.input.clear()
            self.accept()
            if self.parent():
                self.parent()._call_ds(text)
                self.parent().chat_paused = False

    def showEvent(self, event):
        self.input.setFocus()
        super().showEvent(event)

    def popup_at(self, x, y):
        self.move(int(x - self.width() / 2), int(y - self.height() - 10))
        self.show()
        self.raise_()

    def reject(self):
        if self.parent():
            self.parent().chat_paused = False
        super().reject()


class FoodPanel(QWidget):
    """双击弹出的喂食面板"""

    def __init__(self, on_pick):
        super().__init__(None, Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool
                         | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(310, 64)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 8, 12, 8)
        lay.setSpacing(8)
        for f in FOODS:
            b = QToolButton()
            b.setText(f)
            b.setFont(QFont("Segoe UI Emoji", 20))
            b.setFixedSize(44, 44)
            b.setStyleSheet(
                "QToolButton{background:rgba(255,255,255,235);border:2px solid #ffb3c8;"
                "border-radius:22px;} QToolButton:hover{background:#ffe3ec;border-color:#ff7fa8;}")
            b.clicked.connect(lambda _, x=f: on_pick(x))
            lay.addWidget(b)
        close = QToolButton()
        close.setText("✕")
        close.setFont(QFont("Microsoft YaHei UI", 12))
        close.setFixedSize(26, 26)
        close.setStyleSheet("QToolButton{background:rgba(255,255,255,200);border:none;border-radius:13px;color:#666;}"
                            "QToolButton:hover{background:#ff7fa8;color:#fff;}")
        close.clicked.connect(self.hide)
        lay.addWidget(close)
        self.setStyleSheet("FoodPanel{background:rgba(40,40,60,190);border-radius:14px;}")

    def popup_at(self, x, y):
        self.move(int(x - self.width() / 2), int(y - self.height() - 10))
        self.show()
        self.raise_()

class PetWindow(QWidget):
    def _set_city_dialog(self):
        city, ok = QInputDialog.getText(
            self,
            "设置城市",
            "输入城市名:",
            QLineEdit.EchoMode.Normal,
            self.cfg.get("city", "汕头")
        )

        print("输入框结果:", city, ok)

        if ok and city.strip():
            self.cfg["city"] = city.strip()
            print("cfg现在:", self.cfg["city"])
            self.say(f"城市已设置为{city}")
            self.save_config()

    def __init__(self):
        self.cfg = load_json(CONFIG_PATH, {
            "mode": "wander",
            "size": 0.7,
            "topmost": True,
            "passthrough": False,
            "autostart": False,
            "x": None,
            "y": None,
            "ds_api_key": "",
            "city": "汕头",
            "display_objects": ["deepseek_balance", "codex_usage"],
            "codex_usage_view": "primary"
    })
        if not isinstance(self.cfg.get("display_objects"), list):
            self.cfg["display_objects"] = ["deepseek_balance", "codex_usage"]
        self.cfg["display_objects"] = [
            key for key in self.cfg["display_objects"]
            if key in ("deepseek_balance", "codex_usage")
        ]
        if self.cfg.get("codex_usage_view") not in ("primary", "secondary"):
            self.cfg["codex_usage_view"] = "primary"
        
        flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool
        if self.cfg.get("topmost", True):
            flags |= Qt.WindowType.WindowStaysOnTopHint
        super().__init__(None, flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowTitle("AI_Bento · 大肥鱼桌宠")
        
        # 精灵加载
        self.sprites = {}
        for label, mult in SIZE_LEVELS.items():
            h = int(340 * mult)
            for name in ["正面", "侧面", "背面"]:
                sized = os.path.join(SPRITE_DIR, f"{name}_{h}.png")
                if os.path.exists(sized):
                    pix = QPixmap(sized)
                else:
                    pix = QPixmap(os.path.join(SPRITE_DIR, f"{name}.png")).scaledToHeight(
                        h, Qt.TransformationMode.SmoothTransformation)
                self.sprites[(name, h)] = pix
        self.icon = QIcon(os.path.join(SPRITE_DIR, "icon.png"))

        self.cur_h = int(340 * self.cfg["size"])
        self.win_mx = int(self.cur_h * 0.062) + 6
        self.win_w = max(p.width() for k, p in self.sprites.items() if k[1] == self.cur_h) + self.win_mx * 2
        self.setFixedSize(self.win_w, self.cur_h + BUBBLE_H + MARGIN * 2 + 10 + self._label_area_height())

        # 状态
        self.mode = self.cfg["mode"] if self.cfg["mode"] in ("wander", "follow", "still") else "wander"
        self.dir = "down"
        self.facing = 1
        self.target = None
        self.rest_until = 0
        self.cur_speed = 0.0
        self.prev_key = None
        self.cross_t = 0.0
        self.action = None
        self.action_t = 0.0
        self.bubble_text = ""
        self.bubble_until = 0
        self.bubble_inner = False
        self.last_speak_tick = 0
        self.last_system_check = 0
        self.t = 0
        self.jump_t = 0
        self.dragging = False
        self.drag_offset = None
        self.drag_start_pos = None
        self.last_line = ""
        self.last_press_pos = None
        
        # 余额显示（脚下常驻 + 30 秒自动刷新）
        self.balance_value = ""          # 格式化后的余额文本，如 "余额 ¥110.00"
        self.balance_status = "nokey"    # nokey / loading / refreshing / ok / error
        self.balance_msg = ""            # 错误提示
        self.balance_busy = False
        self.codex_usage = None
        self.codex_status = "loading"
        self.codex_busy = False
        self._label_hitboxes = {}
        self._label_click_object = None

        # AI 相关
        self.ds_busy = False
        self.chat_history = []  # 对话历史
        self.max_history = 40   # 最多记录40条
        self._say_queue = []    # 后台线程→主线程的气泡消息队列
        
        # 聊天暂停标志
        self.chat_paused = False
        
        # 喂食面板
        self.food_panel = FoodPanel(self.on_food)
        # 单击延迟判定（等双击）：单击=回嘴+刷新余额，双击=喂食
        self._click_timer = QTimer(self)
        self._click_timer.setSingleShot(True)
        self._click_timer.timeout.connect(self._on_single_click)
        
        # 聊天对话框
        self.chat_dialog = ChatDialog(self)
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(TICK)

        self.balance_timer = QTimer(self)
        self.balance_timer.timeout.connect(lambda: self._refresh_balance(manual=False))
        self.balance_timer.start(BALANCE_REFRESH_MS)
        self.codex_timer = QTimer(self)
        self.codex_timer.timeout.connect(self._refresh_codex_usage)
        self.codex_timer.start(CODEX_USAGE_REFRESH_MS)

        self.bubble_font = QFont("Microsoft YaHei UI", 11)

        # 托盘
        self.tray = QSystemTrayIcon(self.icon, self)
        self.tray.setContextMenu(self._build_menu())
        self.tray.activated.connect(self._on_tray_activated)
        self.tray.show()

        x, y = self.cfg.get("x"), self.cfg.get("y")
        if x is None or y is None:
            screen = QApplication.primaryScreen().availableGeometry()
            x = screen.right() - self.width() - 80
            y = screen.bottom() - self.height() - 60
        self.move(int(x), int(y))
        self.show()
        self.snap_into_screen()
        if self.cfg.get("passthrough", False):
            self._apply_passthrough(True)
        self._refresh_balance(manual=False)
        self._refresh_codex_usage()

    # ---------- AI 方法 ----------
    def _call_ds(self, user_msg):
        if self.ds_busy:
            self.say("等等，上一句还没回完呢")
            return
        
        key = self.cfg.get("ds_api_key", "")
        if not key:
            self.say("请先在右键菜单里设置 DeepSeek Key！")
            return
        
        self.ds_busy = True
        
        # 构建消息列表
        messages = [{"role": "system", "content": DS_SYSTEM}]
        messages.extend(self.chat_history[-self.max_history:])
        messages.append({"role": "user", "content": user_msg})
        
        def worker():
            url = "https://api.deepseek.com/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "deepseek-chat",
                "messages": messages,
                "max_tokens": 100,
                "temperature": 0.9
            }
            try:
                resp = requests.post(url, json=payload, headers=headers, timeout=10)
                if resp.status_code == 200:
                    reply = resp.json()["choices"][0]["message"]["content"].strip()
                    if len(reply) > 30:
                        reply = reply[:28] + "…"
                    # 存入历史
                    self.chat_history.append({"role": "user", "content": user_msg})
                    self.chat_history.append({"role": "assistant", "content": reply})
                    if len(self.chat_history) > self.max_history:
                        self.chat_history = self.chat_history[-self.max_history:]
                    self._queue_say(reply)
                else:
                    error_msg = resp.json().get("error", {}).get("message", str(resp.status_code))
                    self._queue_say(f"API错误: {error_msg[:12]}")
                    print(f"[DeepSeek] 状态码: {resp.status_code}, 返回: {resp.text}")
            except requests.exceptions.Timeout:
                self._queue_say("请求超时，检查网络")
            except requests.exceptions.ConnectionError:
                self._queue_say("连接失败，检查网络")
            except Exception as e:
                self._queue_say(f"请求失败: {str(e)[:12]}")
            finally:
                self.ds_busy = False
        
        threading.Thread(target=worker, daemon=True).start()

    # ---------- 余额显示（脚下常驻 + 自动刷新） ----------
    def _balance_label(self):
        """脚下常驻标签的当前文本。"""
        if self.balance_status == "nokey":
            return "未设置Key"
        if self.balance_status == "loading":
            return "余额加载中…"
        if self.balance_status == "refreshing":
            return "余额刷新中…"
        if self.balance_status == "error":
            return self.balance_msg or "余额获取失败"
        return self.balance_value or "余额 --"

    def _current_period(self):
        """当前时段对应的背景色。高峰红底、低谷绿底。"""
        if is_peak_hour(time.localtime().tm_hour):
            return QColor(220, 60, 60, 235)
        return QColor(60, 170, 90, 235)

    def _refresh_balance(self, manual=False, bubble=False):
        """拉取 DeepSeek 余额并更新脚下常驻标签。

        - 每 30 秒自动静默刷新（manual=False）
        - 左键单击 / 设置 Key 后手动刷新（manual=True），标签短暂显示“余额刷新中…”
        - 鼠标中键刷新并气泡播报结果（bubble=True）
        """
        key = self.cfg.get("ds_api_key", "")
        if not key:
            self.balance_status = "nokey"
            self.balance_msg = ""
            self.update()
            if bubble:
                self.say("请先在右键菜单里设置 DeepSeek Key！")
            return

        if self.balance_busy:
            return

        self.balance_busy = True
        if manual:
            self.balance_status = "refreshing"
        elif not self.balance_value:
            self.balance_status = "loading"
        self.update()

        def worker():
            try:
                resp = requests.get(
                    DS_BALANCE_URL,
                    headers={"Authorization": f"Bearer {key}"},
                    timeout=10
                )
                if resp.status_code == 200:
                    parsed = None
                    try:
                        parsed = parse_balance_payload(resp.json())
                    except ValueError:
                        parsed = None
                    if parsed is not None:
                        self.balance_value = format_balance_text(*parsed)
                        self.balance_status = "ok"
                        self.balance_msg = ""
                        if bubble:
                            self._queue_say(self.balance_value)
                    else:
                        self._balance_error("余额接口异常", bubble)
                elif resp.status_code == 401:
                    self._balance_error("Key无效", bubble)
                elif resp.status_code == 402:
                    self._balance_error("余额不足", bubble)
                else:
                    self._balance_error(f"HTTP {resp.status_code}", bubble)
            except requests.exceptions.Timeout:
                self._balance_error("查询超时", bubble)
            except requests.exceptions.ConnectionError:
                self._balance_error("网络失败", bubble)
            except Exception as e:
                self._balance_error(str(e)[:10] or "未知错误", bubble)
            finally:
                self.balance_busy = False

        threading.Thread(target=worker, daemon=True).start()

    def _balance_error(self, msg, bubble):
        self.balance_status = "error"
        self.balance_msg = msg
        if bubble:
            self._queue_say(f"余额查询失败: {msg}")

    # ---------- Codex 剩余用量（本地会话日志） ----------
    def _refresh_codex_usage(self):
        if self.codex_busy or "codex_usage" not in self._display_objects():
            return
        self.codex_busy = True
        if self.codex_usage is None:
            self.codex_status = "loading"
        self.update()

        def worker():
            try:
                usage = fetch_codex_usage_local()
                if usage is None:
                    self.codex_status = "unavailable"
                else:
                    self.codex_usage = usage
                    self.codex_status = "ok"
            except Exception:
                self.codex_status = "unavailable"
            finally:
                self.codex_busy = False
                self.update()

        threading.Thread(target=worker, daemon=True).start()

    def _codex_usage_label(self):
        if self.codex_status == "loading":
            return "Codex 用量加载中…"
        if self.codex_status != "ok" or self.codex_usage is None:
            return "Codex 用量不可用"
        return format_codex_usage_text(self.codex_usage, self.cfg["codex_usage_view"])

    def _show_codex_usage_details(self):
        if self.codex_usage is None:
            self.say("Codex 用量暂无数据，先完成一次 Codex 对话后再试。")
            return
        usage = self.codex_usage
        primary = format_codex_usage_text(usage, "primary")
        secondary = format_codex_usage_text(usage, "secondary")
        detail = (
            f"{primary}，{format_reset_time(usage.get('primary_reset'))}；"
            f"{secondary}，{format_reset_time(usage.get('secondary_reset'))}"
        )
        self.say(detail)

    def _display_objects(self):
        return self.cfg.get("display_objects", [])

    def _label_area_height(self):
        count = len(self._display_objects())
        if not count:
            return 0
        return count * LABEL_H + (count - 1) * LABEL_GAP + LABEL_MARGIN * 2

    def _update_label_layout(self):
        self.setFixedSize(self.win_w, self.cur_h + BUBBLE_H + MARGIN * 2 + 10 + self._label_area_height())
        self.snap_into_screen()
        self.update()

    def set_display_object(self, key, enabled):
        shown = self._display_objects()
        if enabled and key not in shown:
            shown.append(key)
        elif not enabled and key in shown:
            shown.remove(key)
        self.cfg["display_objects"] = shown
        if enabled and key == "codex_usage":
            self._refresh_codex_usage()
        self._update_label_layout()
        self.save_config()

    # ---------- 绘制 ----------
    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        now = self.t * TICK / 1000.0

        if self.bubble_text and now < self.bubble_until:
            if self.bubble_inner:
                bfont = QFont(self.bubble_font)
                bfont.setItalic(True)
                bg, fg = QColor(232, 232, 238, 235), QColor(125, 125, 138)
            else:
                bfont = QFont(self.bubble_font)
                bg, fg = QColor(255, 255, 255, 235), QColor(60, 60, 80)
            fm = QFontMetrics(bfont)
            max_w = min(240, self.width() - 16)
            words = self.bubble_text
            lines = []
            cur = ""
            for ch in words:
                if fm.horizontalAdvance(cur + ch) > max_w - 20:
                    lines.append(cur)
                    cur = ch
                else:
                    cur += ch
            lines.append(cur)
            bw = max(fm.horizontalAdvance(l) for l in lines) + 20
            bh = len(lines) * fm.height() + 14
            bx = (self.width() - bw) / 2
            by = 6.0
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(bg)
            p.drawRoundedRect(QRectF(bx, by, bw, bh), 10, 10)
            tail = QPointF(self.width() / 2, by + bh)
            p.drawPolygon(QPolygonF([tail, QPointF(tail.x() - 6, tail.y() + 8), QPointF(tail.x() + 6, tail.y() + 8)]))
            p.setPen(fg)
            p.setFont(bfont)
            for i, l in enumerate(lines):
                p.drawText(QRectF(bx, by + 7 + i * fm.height(), bw, fm.height()),
                           Qt.AlignmentFlag.AlignCenter, l)

        cx = self.width() / 2
        walking = self.target is not None and not self.dragging
        if walking:
            sway = math.sin(now * 9.0) * 3.5
            bob = -abs(math.sin(now * 4.5)) * 7.0
        else:
            sway = math.sin(now * 2.5) * 1.5
            bob = 0.0
        breath = 1.0 + 0.02 * math.sin(now * 2.5)
        scale = breath
        jump = -abs(math.sin(self.jump_t * 3.14159)) * 14 * self.jump_t if self.jump_t > 0 else 0
        act_rot = act_sx = act_sy = 0.0
        if self.action == "sway":
            act_rot = math.sin(self.action_t * 3.14159 * 2) * 10 * self.action_t
        elif self.action == "stretch":
            act_sy = 0.06 * math.sin(self.action_t * 3.14159)
            act_sx = -0.03 * math.sin(self.action_t * 3.14159)

        def draw_one(key, opacity):
            if key is None:
                return
            name, h, facing = key
            pix = self.sprites[(name, h)]
            ph = pix.height() * scale * (1 + act_sy)
            pw = pix.width() * scale * (1 + act_sx)
            dx = cx - pw / 2
            bottom = BUBBLE_H + MARGIN + self.cur_h
            dy = bottom - ph + jump + bob
            p.save()
            p.setOpacity(opacity)
            p.translate(cx, bottom)
            p.rotate(sway + act_rot)
            p.translate(-cx, -bottom)
            if facing < 0:
                p.translate(cx, 0)
                p.scale(-1, 1)
                p.translate(-cx, 0)
            p.drawPixmap(QRectF(dx, dy, pw, ph), pix, QRectF(0, 0, pix.width(), pix.height()))
            p.restore()

        cur_key = self._sprite_key()
        if self.cross_t > 0:
            draw_one(self.prev_key, self.cross_t)
            draw_one(cur_key, 1.0 - self.cross_t)
        else:
            draw_one(cur_key, 1.0)

        # ---- 可多选的显示对象：DeepSeek 余额 / Codex 剩余用量 ----
        lf = QFont("Microsoft YaHei UI", 10)
        fm = QFontMetrics(lf)
        max_w = self.width() - 8
        shown = self._display_objects()
        total_h = len(shown) * LABEL_H + max(0, len(shown) - 1) * LABEL_GAP
        label_y = BUBBLE_H + MARGIN + self.cur_h + (self._label_area_height() - total_h) / 2
        self._label_hitboxes = {}
        for key in shown:
            if key == "deepseek_balance":
                raw_label, background = self._balance_label(), self._current_period()
                candidates = [raw_label]
                if "余额 " in raw_label:
                    candidates.append(raw_label.replace("余额 ", ""))
            elif key == "codex_usage":
                raw_label, background = self._codex_usage_label(), QColor(65, 125, 190, 235)
                candidates = [raw_label]
            else:
                continue
            combined = candidates[0]
            for candidate in candidates:
                if fm.horizontalAdvance(candidate) + 20 <= max_w:
                    combined = candidate
                    break
            else:
                combined = candidates[-1]
                while len(combined) > 3 and fm.horizontalAdvance(combined) + 20 > max_w:
                    combined = combined[:-1]
                combined += "…"
            label_w = min(fm.horizontalAdvance(combined) + 20, max_w)
            label_x = (self.width() - label_w) / 2
            label_rect = QRectF(label_x, label_y, label_w, LABEL_H)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(background)
            p.drawRoundedRect(label_rect, 10, 10)
            p.setPen(QColor(255, 255, 255))
            p.setFont(lf)
            p.drawText(label_rect, Qt.AlignmentFlag.AlignCenter, combined)
            self._label_hitboxes[key] = label_rect
            label_y += LABEL_H + LABEL_GAP

    def _sprite_key(self):
        name = {"left": "侧面", "right": "侧面", "up": "背面", "down": "正面"}[self.dir]
        return (name, self.cur_h, self.facing if self.dir in ("left", "right") else 1)

    def _set_dir(self, d, facing=None):
        if d != self.dir:
            self.prev_key = self._sprite_key()
            self.cross_t = 1.0
            self.dir = d
        if facing is not None and facing != self.facing:
            self.facing = facing

    # ---------- 逻辑 ----------
    def tick(self):
        self.t += 1

        # 处理后台线程（DeepSeek 等）排队的气泡消息，Qt 界面必须在主线程更新
        if self._say_queue:
            for text in self._say_queue:
                self.say(text)
            self._say_queue.clear()

        self.check_system_status()
        
        if self.jump_t > 0:
            self.jump_t = max(0.0, self.jump_t - 0.06)
        if self.cross_t > 0:
            self.cross_t = max(0.0, self.cross_t - 0.15)
        if self.action_t > 0:
            self.action_t = max(0.0, self.action_t - 0.03)
            if self.action_t == 0:
                self.action = None
        
        if self.chat_paused:
            self.update()
            return
        
        if self.dragging:
            self.update()
            return
        now_ms = self.t * TICK

        if self.mode == "follow":
            cursor = self.cursor().pos()
            screen = QApplication.screenAt(cursor) or self.screen() or QApplication.primaryScreen()
            geo = screen.availableGeometry()
            near = (self.x() - 100 <= cursor.x() <= self.x() + self.width() + 100 and
                    self.y() - 100 <= cursor.y() <= self.y() + self.height() + 100)
            if near:
                self.target = None
            else:
                tx = max(geo.left(), min(geo.right() - self.width(), cursor.x() - self.width() / 2))
                ty = max(geo.top(), min(geo.bottom() - self.height(), cursor.y() - 90))
                self.target = (tx, ty)
        elif self.mode == "wander":
            if self.target is None:
                if now_ms < self.rest_until:
                    self._maybe_idle_action()
                    self.update()
                    return
                geo = (self.screen() or QApplication.primaryScreen()).availableGeometry()
                self.target = (random.randint(geo.left() + 40, geo.right() - self.width() - 40),
                               random.randint(geo.top() + 40, geo.bottom() - self.height() - 40))
        else:
            self._maybe_idle_action()
            self.update()
            return

        if self.target is not None:
            cx, cy = self.x() + self.width() / 2, self.y() + self.height() / 2
            dx, dy = self.target[0] - cx, self.target[1] - cy
            dist = (dx * dx + dy * dy) ** 0.5
            if dist < 12:
                self.target = None
                self.rest_until = self.t * TICK + random.randint(8000, 18000)
                self._set_dir("down")
            else:
                step = self.cur_speed * TICK / 1000.0
                nx, ny = cx + dx / dist * step, cy + dy / dist * step
                self.move(int(nx - self.width() / 2), int(ny - self.height() / 2))
                if abs(dx) > abs(dy) * 1.15:
                    self._set_dir("left" if dx < 0 else "right", 1 if dx < 0 else -1)
                else:
                    self._set_dir("up" if dy < 0 else "down")
            if random.random() < 0.002 and self.jump_t == 0:
                self.jump_t = 0.5
        target_speed = SPEED if self.target is not None else 0.0
        self.cur_speed += (target_speed - self.cur_speed) * 0.3
        self.update()

    def _maybe_idle_action(self):
        if random.random() < 0.01:
            pick = random.random()
            if pick < 0.35:
                self.jump_t = 1.0
            elif pick < 0.6:
                self.action, self.action_t = "sway", 1.0
            elif pick < 0.8:
                self.action, self.action_t = "stretch", 1.0
            elif pick < 0.9:
                if self.t - self.last_speak_tick >= 1500:
                    self.last_speak_tick = self.t
                    if pick < 0.82:
                        self.say(random.choice(INNER_LINES), inner=True)
                    else:
                        self.say(random.choice(LINES))

    def _queue_say(self, text):
        """后台线程调用：只入队，由主线程 tick 统一弹出显示（线程安全）"""
        self._say_queue.append(text)

    def say(self, text, inner=False):
        if text == self.last_line and not text.startswith("天气"):
            return
        self.last_line = text
        self.bubble_inner = inner
        self.bubble_text = f"（{text}）" if inner else text
        self.bubble_until = self.t * TICK / 1000.0 + 2.8
        self.update()

    def check_system_status(self):
            now = self.t * TICK

            if now - getattr(self, "last_system_check", 0) < 10000:
                return

            self.last_system_check = now

            cpu = psutil.cpu_percent()

            if cpu >= 90:
                self.say("CPU跑满了，再这样下去我就卡死了")
                return

            ram = psutil.virtual_memory().percent

            if ram >= 95:
                self.say("内存爆了，快关掉几个没用的东西吧，注意，别把我关了")
                return

            if GPU_AVAILABLE:
                try:
                    handle = pynvml.nvmlDeviceGetHandleByIndex(0)

                    temp = pynvml.nvmlDeviceGetTemperature(
                        handle,
                        pynvml.NVML_TEMPERATURE_GPU
                    )

                    if temp > 80:
                        self.say("我感觉我的鱼鳍快熟了")

                except Exception as e:
                    print("GPU读取失败:", e)

    # ---------- 鼠标事件 ----------
    def mousePressEvent(self, e):
        label_key = next((key for key, rect in self._label_hitboxes.items()
                          if rect.contains(e.position())), None)
        if label_key == "codex_usage":
            if e.button() == Qt.MouseButton.MiddleButton:
                self._show_codex_usage_details()
            elif e.button() == Qt.MouseButton.LeftButton:
                self._label_click_object = label_key
            return
        if e.button() == Qt.MouseButton.MiddleButton:
            self._show_chat_dialog()
            return
        if e.button() == Qt.MouseButton.LeftButton:
            self.last_press_pos = e.globalPosition().toPoint()
            self.dragging = False
            self.drag_start_pos = e.globalPosition().toPoint()
            self.chat_dialog.hide()
            self.chat_paused = True

    def mouseMoveEvent(self, e):
        if e.buttons() & Qt.MouseButton.LeftButton and self.drag_start_pos is not None:
            delta = e.globalPosition().toPoint() - self.drag_start_pos
            if not self.dragging and delta.manhattanLength() > 6:
                self.dragging = True
                self.drag_offset = e.globalPosition().toPoint() - QPoint(self.x(), self.y())
            if self.dragging and self.drag_offset is not None:
                pos = e.globalPosition().toPoint() - self.drag_offset
                self.move(pos)
                if abs(delta.x()) > 10:
                    self._set_dir("left" if delta.x() < 0 else "right", 1 if delta.x() < 0 else -1)
                self.update()

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            if getattr(self, "_label_click_object", None) == "codex_usage":
                self._label_click_object = None
                self.cfg["codex_usage_view"] = (
                    "secondary" if self.cfg["codex_usage_view"] == "primary" else "primary"
                )
                self.save_config()
                self.update()
                return
            if self.dragging:
                self.dragging = False
                self.drag_offset = None
                self.drag_start_pos = None
                self._set_dir("down", 1)
                self.target = None
                self.rest_until = self.t * TICK + random.randint(6000, 14000)
                if random.random() < 0.5:
                    self.say(random.choice(DRAG_LINES))
                self.chat_paused = False
            else:
                self._click_timer.start(280)  # 等双击判定；单击则回嘴+刷新余额
            self.last_press_pos = None
            self.drag_start_pos = None

    def mouseDoubleClickEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            if any(rect.contains(e.position()) for rect in self._label_hitboxes.values()):
                return
            self._click_timer.stop()
            self.food_panel.popup_at(self.x() + self.width() / 2, self.y() + BUBBLE_H)

    def _on_single_click(self):
        """单击：蹦跳回嘴 + 刷新余额"""
        self.chat_paused = False
        if random.random() < 0.7:
            self.jump_t = 1.0
        if random.random() < 0.6:
            self.say(random.choice(REACT_LINES))
        self._refresh_balance(manual=True)

    def on_food(self, food):
        self.food_panel.hide()
        self.eat_t = 1.0
        self.jump_t = 0.6
        lines = FOOD_LINES.get(food, ["好吃！"])
        self.say(random.choice(lines))

    def _show_chat_dialog(self):
        key = self.cfg.get("ds_api_key", "")
        if not key:
            self.say("请先在右键菜单里设置 DeepSeek Key！")
            self.chat_paused = False
            return
        self.chat_paused = True
        self.chat_dialog.popup_at(
            self.x() + self.width() / 2,
            self.y() + BUBBLE_H
        )

    """def _get_city_by_ip(self):
        try:
            r = requests.get("http://ip-api.com/json/?fields=city&lang=zh-CN", timeout=5)
            if r.status_code == 200:
                city = r.json().get("city", "")
                if city:
                    return city
        except:
            pass
        return "汕头" """

    def _get_weather(self):
        try:
            city = self.cfg.get("city", "汕头")
            print("当前城市:", city)

            url = f"https://wttr.in/{city}?format=j1"

            r = requests.get(
                url,
                timeout=10,
                headers={
                    "User-Agent": "Mozilla/5.0"
                }
            )

            print("状态:", r.status_code)
            print(r.text[:500])

            data = r.json()

            weather = data["current_condition"][0]

            temp = weather["temp_C"]

            weather_map = {
                "Sunny": "晴",
                "Clear": "晴",
                "Partly cloudy": "多云",
                "Cloudy": "阴",
                "Light rain": "小雨",
                "Moderate rain": "中雨",
                "Heavy rain": "大雨"
            }

            raw_weather = weather["weatherDesc"][0]["value"]

            desc = weather_map.get(raw_weather, raw_weather)

            self.say(f"{city}今天{temp}°，天气{desc}")

        except Exception as e:
            print("天气错误:", repr(e))
            self.say("天气获取失败")
    

    def _build_menu(self):
        m = QMenu(self)
        mode_menu = m.addMenu("模式")
        for label, key in [("自由散步", "wander"), ("跟随鼠标", "follow"), ("原地待着", "still")]:
            a = mode_menu.addAction(label)
            a.setCheckable(True)
            a.setChecked(self.mode == key)
            a.triggered.connect(lambda _, k=key: self.set_mode(k))
        size_menu = m.addMenu("大小")
        for label, mult in SIZE_LEVELS.items():
            a = size_menu.addAction(label)
            a.setCheckable(True)
            a.setChecked(abs(self.cur_h - 340 * mult) < 2)
            a.triggered.connect(lambda _, v=mult: self.set_size(v))
        display_menu = m.addMenu("余额显示对象")
        for label, key in [("DeepSeek 余额", "deepseek_balance"), ("Codex 剩余用量", "codex_usage")]:
            a = display_menu.addAction(label)
            a.setCheckable(True)
            a.setChecked(key in self._display_objects())
            a.triggered.connect(lambda on, k=key: self.set_display_object(k, on))
        m.addAction("设置 Key", self._set_key_dialog)
        m.addAction("查看天气", self._get_weather)
        m.addSeparator()
        m.addAction("显示/隐藏", self.toggle_visible)
        m.addAction("回到屏幕内", self.snap_into_screen)
        pa = m.addAction("鼠标穿透（点不到它）")
        pa.setCheckable(True)
        pa.setChecked(self.cfg["passthrough"])
        pa.triggered.connect(lambda on: self.set_passthrough(on))
        ta = m.addAction("窗口置顶")
        ta.setCheckable(True)
        ta.setChecked(self.cfg["topmost"])
        ta.triggered.connect(lambda on: self.set_topmost(on))
        aa = m.addAction("开机自启")
        aa.setCheckable(True)
        aa.setChecked(self.cfg["autostart"])
        aa.triggered.connect(lambda on: self.set_autostart(on))
        m.addSeparator()
        m.addAction("退出", self.quit_app)
        return m

    def _set_key_dialog(self):
        key, ok = QInputDialog.getText(
            self, 
            "设置 DeepSeek Key", 
            "输入你的 API Key（从 platform.deepseek.com 获取）:",
            QLineEdit.EchoMode.Normal,
            self.cfg.get("ds_api_key", "")
        )
        if ok and key.strip():
            self.cfg["ds_api_key"] = key.strip()
            self.say("Key 设置成功！")
            self._refresh_balance(manual=True)
            self.save_config()
        elif ok and not key.strip():
            self.say("Key 不能为空")

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Context:
            self.tray.setContextMenu(self._build_menu())
        elif reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.toggle_visible()

    def contextMenuEvent(self, e):
        self._build_menu().exec(e.globalPos())

    # ---------- 功能 ----------
    def save_config(self):
        """立即把当前配置写入 config.json（Key / 模式 / 大小等改动即时保存，防止非正常退出丢失）。"""
        try:
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(self.cfg, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print("配置保存失败:", e)

    def set_mode(self, mode):
        self.mode = mode
        self.target = None
        self.cfg["mode"] = mode
        self.save_config()

    def set_size(self, mult):
        self.cur_h = int(340 * mult)
        self.cfg["size"] = mult
        self.cross_t = 0.0
        self.prev_key = None
        self.win_mx = int(self.cur_h * 0.062) + 6
        self.win_w = max(p.width() for k, p in self.sprites.items() if k[1] == self.cur_h) + self.win_mx * 2
        self.setFixedSize(self.win_w, self.cur_h + BUBBLE_H + MARGIN * 2 + 10 + self._label_area_height())
        self.snap_into_screen()
        self.save_config()

    def snap_into_screen(self):
        geo = (self.screen() or QApplication.primaryScreen()).availableGeometry()
        x = max(geo.left(), min(geo.right() - self.width(), self.x()))
        y = max(geo.top(), min(geo.bottom() - self.height(), self.y()))
        self.move(x, y)

    def _apply_passthrough(self, on):
        hwnd = int(self.winId())
        GWL_EXSTYLE, WS_EX_LAYERED, WS_EX_TRANSPARENT = -20, 0x80000, 0x20
        style = ctypes.windll.user32.GetWindowLongPtrW(hwnd, GWL_EXSTYLE)
        style = style | WS_EX_LAYERED
        if on:
            style |= WS_EX_TRANSPARENT
        else:
            style &= ~WS_EX_TRANSPARENT
        ctypes.windll.user32.SetWindowLongPtrW(hwnd, GWL_EXSTYLE, style)

    def set_passthrough(self, on):
        self.cfg["passthrough"] = bool(on)
        self._apply_passthrough(bool(on))
        if on:
            self.say("我隐身了！右键托盘图标解除～")
        self.save_config()

    def set_topmost(self, on):
        self.cfg["topmost"] = bool(on)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, bool(on))
        self.show()
        self.save_config()

    def set_autostart(self, on):
        self.cfg["autostart"] = bool(on)
        lnk = os.path.join(os.environ["APPDATA"], "Microsoft", "Windows",
                           "Start Menu", "Programs", "Startup", "AI_Bento.lnk")
        try:
            if on:
                ps = ("$s=(New-Object -ComObject WScript.Shell).CreateShortcut('{}');"
                      "$s.TargetPath='{}';$s.Arguments='\"{}\"';$s.WorkingDirectory='{}';$s.Save()"
                      .format(lnk, PYTHONW,
                              "" if getattr(sys, "frozen", False) else os.path.join(APP_DIR, "桌宠.py"),
                              APP_DIR))
                subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                               creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0), check=True)
                self.say("已开机自启，明天见～")
            else:
                if os.path.exists(lnk):
                    os.remove(lnk)
                self.say("已取消开机自启")
        except Exception as ex:
            QMessageBox.warning(self, "开机自启", f"设置失败：{ex}")
        self.save_config()

    def toggle_visible(self):
        if self.isVisible():
            self.hide()
        else:
            self.show()
            self.raise_()

    def quit_app(self):
        self.cfg["x"], self.cfg["y"] = self.x(), self.y()
        self.save_config()
        self.tray.hide()
        QApplication.quit()


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    w = PetWindow()
    sys.exit(app.exec())


if __name__ == "__main__":
    try:
        main()
    except Exception as ex:
        try:
            app = QApplication.instance() or QApplication(sys.argv)
            QMessageBox.critical(None, "AI_Bento 出错", str(ex))
        except Exception:
            pass
        raise

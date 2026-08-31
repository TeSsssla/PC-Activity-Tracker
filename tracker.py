# -*- coding: utf-8 -*-
"""
Трекер активности за ПК.
Раз в POLL_INTERVAL секунд смотрит, какое окно активно, и куда идёт время:
работа / отвлечения / нейтральное / простой (нет ввода мышью-клавиатурой).

Перед вечерним отчётом, если за день накопились неизвестные приложения/сайты
с заметным временем — бот присылает по каждому отдельное сообщение с тремя
кнопками (Работа/Отвлечение/Нейтральное). Ответ сохраняется в learned.json
и применяется и к уже накопленному сегодня времени, и ко всем следующим дням.

НЕ логирует нажатия клавиш и содержимое экрана — только имя активного
процесса, заголовок окна и системное время последнего ввода (для простоя).
"""
import ctypes
import datetime
import json
import logging
import re
import time

import psutil
import requests
import win32gui
import win32process
from pycaw.pycaw import AudioUtilities
from pycaw.constants import AudioSessionState

try:
    import uiautomation as auto
    UIA_AVAILABLE = True
except Exception:
    UIA_AVAILABLE = False

import config

logging.basicConfig(
    filename=config.LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    encoding="utf-8",
)
log = logging.getLogger(__name__)

CATEGORIES = ("work", "distraction", "neutral")
CAT_LABEL = {"work": "🟢 Работа", "distraction": "🔴 Отвлечение", "neutral": "⚪ Нейтральное"}
CAT_EMOJI = {"work": "🟢", "distraction": "🔴", "neutral": "⚪"}


# ============================================================
# Окно, простой, звук
# ============================================================
class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]


def get_idle_seconds() -> float:
    """Секунд с последнего движения мыши/нажатия клавиши (без содержимого)."""
    lii = LASTINPUTINFO()
    lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
    ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii))
    millis = ctypes.windll.kernel32.GetTickCount() - lii.dwTime
    return millis / 1000.0


def get_active_window():
    hwnd = win32gui.GetForegroundWindow()
    if not hwnd:
        return None, None, None
    title = win32gui.GetWindowText(hwnd) or ""
    proc_name = "unknown"
    try:
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        proc_name = psutil.Process(pid).name().lower()
    except Exception:
        pass
    return proc_name, title, hwnd


def get_playing_audio_apps() -> set:
    """Какие процессы ПРЯМО СЕЙЧАС реально выводят звук (не просто запущены)."""
    apps = set()
    try:
        for session in AudioUtilities.GetAllSessions():
            if session.Process and session.State == AudioSessionState.Active:
                apps.add(session.Process.name().lower())
    except Exception:
        log.exception("Не удалось получить список аудио-сессий")
    return apps


# ============================================================
# Идентификация: процесс -> либо сам процесс, либо "процесс: домен"
# ============================================================
# Классы/AutomationId адресной строки по браузерам. Может отличаться
# от версии к версии браузера — если перестанет находить, посмотри
# tracker.log (там пишется, когда UI Automation не сработал) и поправь.
BROWSER_OMNIBOX_CLASSNAMES = {
    "chrome.exe": ["Chrome_OmniboxView", "OmniboxViewViews"],
    "msedge.exe": ["Chrome_OmniboxView", "Edge_OmniboxView"],
    "browser.exe": ["Chrome_OmniboxView", "OmniboxViewViews"],
    "opera.exe": ["Chrome_OmniboxView"],
}
BROWSER_OMNIBOX_AUTOMATION_IDS = {
    "firefox.exe": ["urlbar-input"],
}

_uia_warned = set()  # чтобы не спамить лог одинаковым предупреждением каждые 5 сек


def get_browser_url(proc: str, hwnd) -> str | None:
    """Читает реальный URL из адресной строки через Windows UI Automation."""
    if not UIA_AVAILABLE or not hwnd:
        return None

    try:
        win = auto.ControlFromHandle(hwnd)

        # Яндекс.Браузер
        if proc == "browser.exe":
            edit = win.EditControl(
                searchDepth=20,
                ClassName="SmartboxEditField"
            )
            if edit.Exists(0.2):
                try:
                    pattern = edit.GetLegacyIAccessiblePattern()
                    if pattern and pattern.Value:
                        return pattern.Value
                except Exception:
                    pass

        # Остальные браузеры
        for class_name in BROWSER_OMNIBOX_CLASSNAMES.get(proc, []):
            edit = win.EditControl(
                searchDepth=20,
                ClassName=class_name
            )
            if edit.Exists(0.2):
                pat = edit.GetValuePattern()
                if pat and pat.Value:
                    return pat.Value

        for aid in BROWSER_OMNIBOX_AUTOMATION_IDS.get(proc, []):
            edit = win.EditControl(
                searchDepth=20,
                AutomationId=aid
            )
            if edit.Exists(0.2):
                pat = edit.GetValuePattern()
                if pat and pat.Value:
                    return pat.Value

    except Exception as e:
        if proc not in _uia_warned:
            log.warning(
                f"UI Automation не смог прочитать адресную строку {proc}: {e}. "
                f"Дальше буду угадывать по заголовку окна."
            )
            _uia_warned.add(proc)

    return None


def extract_domain(url_text: str) -> str | None:
    if not url_text:
        return None
    text = url_text.strip()
    if "://" not in text:
        text = "http://" + text  # Chrome часто показывает адрес без "https://"
    try:
        from urllib.parse import urlparse
        netloc = urlparse(text).netloc.lower()
        netloc = re.sub(r"^www\.", "", netloc)
        netloc = netloc.split(":")[0]  # отбросить порт, если есть
        return netloc or None
    except Exception:
        return None


def get_site_keyword(title: str) -> str:
    """
    Запасной вариант, если UI Automation не смог прочитать адресную строку.
    Из заголовка вкладки вытаскиваем примерное "имя сайта" (обычно заголовок
    вида "Название страницы - Имя сайта" — берём последний кусок).
    """
    if not title:
        return "без названия"
    parts = re.split(r"\s+[-—|]\s+", title)
    keyword = parts[-1].strip().lower() if parts else title.strip().lower()
    return keyword[:40] if keyword else "без названия"


def get_identifier(proc: str, title: str, hwnd) -> str:
    if proc not in config.BROWSER_PROCESSES:
        return proc
    url = get_browser_url(proc, hwnd)
    domain = extract_domain(url) if url else None
    if domain:
        return f"{proc}: {domain}"
    # UI Automation не сработал — откат на старую эвристику по заголовку
    return f"{proc}: {get_site_keyword(title)} (по заголовку)"


# ============================================================
# learned.json — то, что ты сам разметил кнопками в Telegram
# ============================================================
def load_learned() -> dict:
    if config.LEARNED_FILE.exists():
        return json.loads(config.LEARNED_FILE.read_text(encoding="utf-8"))
    return {}


def save_learned(learned: dict):
    config.LEARNED_FILE.parent.mkdir(parents=True, exist_ok=True)
    config.LEARNED_FILE.write_text(
        json.dumps(learned, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def classify(identifier: str, proc: str, title: str, learned: dict):
    """Возвращает (категория, is_default)."""
    # Если это браузер — сразу считаем неизвестным (игнорируем TITLE_KEYWORDS)
    if proc in config.BROWSER_PROCESSES:
        return config.DEFAULT_CATEGORY, True

    # Для остальных приложений — проверяем learned, APP_CATEGORIES и TITLE_KEYWORDS
    if identifier in learned:
        return learned[identifier], False
    if proc in config.APP_CATEGORIES:
        return config.APP_CATEGORIES[proc], False
    title_l = (title or "").lower()
    for keyword, cat in config.TITLE_KEYWORDS.items():
        if re.search(r"\b" + re.escape(keyword) + r"\b", title_l):
            return cat, False
    return config.DEFAULT_CATEGORY, True


# ============================================================
# Хранение дневных данных
# ============================================================
def load_day(date_str: str) -> dict:
    path = config.DATA_DIR / f"{date_str}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {
        "apps": {},           # identifier -> {"seconds", "category", "is_default"}
        "audio_apps": {},
        "work_seconds": 0,
        "distraction_seconds": 0,
        "neutral_seconds": 0,
        "idle_seconds": 0,
        "report_sent": False,
        "review_done": False,
    }


def save_day(date_str: str, data: dict):
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    (config.DATA_DIR / f"{date_str}.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def fmt(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    return f"{h}ч {m}м" if h else f"{m}м"


# ============================================================
# Telegram
# ============================================================
def tg_call(method: str, payload: dict):
    url = f"https://api.telegram.org/bot{config.TELEGRAM_TOKEN}/{method}"
    try:
        r = requests.post(url, json=payload, timeout=15)
        if r.status_code != 200:
            log.error(f"Telegram {method} ответил {r.status_code}: {r.text}")
            return None
        return r.json()
    except Exception:
        log.exception(f"Ошибка вызова Telegram {method}")
        return None


def send_telegram(text: str):
    result = tg_call(
        "sendMessage",
        {"chat_id": config.TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML"},
    )
    if result:
        log.info("Отчёт отправлен в Telegram.")


# ============================================================
# Интерактивный опрос неизвестных приложений/сайтов кнопками
# ============================================================
def pick_review_candidates(data, learned):
    """Идентификаторы, попавшие в DEFAULT_CATEGORY, с заметным временем,
    ещё не размеченные в learned.json — те, о ком стоит спросить."""
    candidates = [
        (ident, info["seconds"])
        for ident, info in data["apps"].items()
        if info.get("is_default") and ident not in learned
        and info["seconds"] >= config.REVIEW_MIN_SECONDS
    ]
    candidates.sort(key=lambda x: -x[1])
    return [ident for ident, _ in candidates[: config.REVIEW_MAX_ITEMS]]


def ask_review(identifier: str, seconds: float):
    """Шлёт сообщение с тремя кнопками, возвращает message_id (или None при ошибке)."""
    text = f"Как классифицировать «{identifier}»?\nНакопилось за сегодня: {fmt(seconds)}"
    keyboard = {
        "inline_keyboard": [[
            {"text": CAT_LABEL[cat], "callback_data": f"clf|{identifier}|{cat}"}
            for cat in CATEGORIES
        ]]
    }
    result = tg_call(
        "sendMessage",
        {"chat_id": config.TELEGRAM_CHAT_ID, "text": text, "reply_markup": keyboard},
    )
    if result and result.get("ok"):
        return result["result"]["message_id"]
    return None


def load_offset() -> int:
    if config.TG_OFFSET_FILE.exists():
        try:
            return int(config.TG_OFFSET_FILE.read_text().strip())
        except Exception:
            return 0
    return 0


def save_offset(offset: int):
    config.TG_OFFSET_FILE.parent.mkdir(parents=True, exist_ok=True)
    config.TG_OFFSET_FILE.write_text(str(offset))


def poll_answers(pending: set, wait_seconds: int) -> dict:
    """
    Опрашивает Telegram (getUpdates) до wait_seconds секунд, собирает нажатия
    кнопок по идентификаторам из pending. Возвращает {identifier: category}.
    """
    answers = {}
    offset = load_offset()
    deadline = time.time() + wait_seconds
    while time.time() < deadline and pending:
        result = tg_call("getUpdates", {"offset": offset, "timeout": 5})
        if not result or not result.get("ok"):
            time.sleep(2)
            continue
        for upd in result.get("result", []):
            offset = upd["update_id"] + 1
            cq = upd.get("callback_query")
            if not cq:
                continue
            data_str = cq.get("data", "")
            if not data_str.startswith("clf|"):
                continue
            try:
                _, identifier, cat = data_str.split("|", 2)
            except ValueError:
                continue
            if identifier in pending and cat in CATEGORIES:
                answers[identifier] = cat
                pending.discard(identifier)
                tg_call("answerCallbackQuery", {"callback_query_id": cq["id"], "text": "Записал."})
                tg_call(
                    "editMessageText",
                    {
                        "chat_id": config.TELEGRAM_CHAT_ID,
                        "message_id": cq["message"]["message_id"],
                        "text": f"«{identifier}» -> {CAT_LABEL[cat]} ✅",
                    },
                )
        save_offset(offset)
    save_offset(offset)
    return answers


def run_review(data, learned):
    """Полный цикл: спросить про неизвестное, дождаться ответов, применить
    задним числом к уже накопленному сегодня времени. Возвращает обновлённый data."""
    candidates = pick_review_candidates(data, learned)
    if not candidates:
        return data

    log.info(f"Опрашиваю по неизвестным: {candidates}")
    pending = set()
    for ident in candidates:
        seconds = data["apps"][ident]["seconds"]
        if ask_review(ident, seconds):
            pending.add(ident)
        time.sleep(0.3)  # не спамить Telegram API слишком быстро

    if not pending:
        return data

    answers = poll_answers(pending, config.REVIEW_WAIT_SECONDS)

    for ident, cat in answers.items():
        learned[ident] = cat
        entry = data["apps"][ident]
        old_cat = entry["category"]
        seconds = entry["seconds"]
        data[f"{old_cat}_seconds"] -= seconds
        data[f"{cat}_seconds"] += seconds
        entry["category"] = cat
        entry["is_default"] = False

    if answers:
        save_learned(learned)
        log.info(f"Размечено кнопками: {answers}")

    return data


# ============================================================
# Отчёт
# ============================================================
def build_report(date_str: str, data: dict) -> str:
    work = data["work_seconds"]
    distraction = data["distraction_seconds"]
    neutral = data["neutral_seconds"]
    idle = data["idle_seconds"]
    active = work + distraction + neutral
    total_tracked = active + idle

    if active == 0:
        return f"📊 <b>Отчёт за {date_str}</b>\n\nСегодня активности почти не было."

    scoreable = work + distraction
    score = round(work / scoreable * 10, 1) if scoreable else None
    coverage = round((work + distraction) / active * 100) if active else 0

    def pct(seconds):
        return round(seconds / total_tracked * 100) if total_tracked else 0

    lines = [f"📊 <b>Отчёт за {date_str}</b>", ""]
    lines.append(f"Активное время за ПК: {fmt(active)} (из {fmt(total_tracked)} всего)")
    lines.append(f"🟢 Работа: {fmt(work)} ({pct(work)}%)")
    lines.append(f"🔴 Отвлечения: {fmt(distraction)} ({pct(distraction)}%)")
    lines.append(f"⚪ Нейтральное/неклассифицировано: {fmt(neutral)} ({pct(neutral)}%)")
    lines.append(f"💤 Простой: {fmt(idle)} ({pct(idle)}%)")
    lines.append("")

    if score is not None:
        lines.append(f"⭐ Оценка (работа vs отвлечения): {score}/10")
    else:
        lines.append("⭐ Оценка: нет данных (не было ни работы, ни отвлечений)")
    lines.append(f"🎯 Покрытие классификацией: {coverage}% активного времени")

    if coverage < 60:
        lines.append("")
        lines.append(
            f"⚠️ {100 - coverage}% активного времени попало в «нейтральное». "
            "Неотвеченные кнопки выше по чату — можешь разметить их позже, "
            "тогда завтрашний отчёт станет точнее."
        )

    lines.append("")
    lines.append("Разбор по приложениям/сайтам:")
    top = sorted(data["apps"].items(), key=lambda x: -x[1]["seconds"])[:8]
    for name, info in top:
        lines.append(f"{CAT_EMOJI.get(info['category'], '⚪')} {name} — {fmt(info['seconds'])}")

    audio = data.get("audio_apps") or {}
    if audio:
        lines.append("")
        lines.append("🎵 Параллельно слушал/смотрел (фоном, пока работал в другом окне):")
        top_audio = sorted(audio.items(), key=lambda x: -x[1]["seconds"])[:5]
        for name, info in top_audio:
            lines.append(f"🎧 {name} — {fmt(info['seconds'])}")

    return "\n".join(lines)


# ============================================================
# Главный цикл
# ============================================================
def main():
    log.info("Трекер запущен.")
    learned = load_learned()

    while True:
        now = datetime.datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        data = load_day(date_str)

        idle = get_idle_seconds()
        proc, title, hwnd = get_active_window()
        is_locked = proc in config.SYSTEM_IDLE_PROCESSES

        if idle < config.IDLE_THRESHOLD_SECONDS and not is_locked:
            if proc:
                identifier = get_identifier(proc, title, hwnd)
                cat, is_default = classify(identifier, proc, title, learned)
                entry = data["apps"].setdefault(
                    identifier, {"seconds": 0, "category": cat, "is_default": is_default}
                )
                entry["seconds"] += config.POLL_INTERVAL
                entry["category"] = cat
                entry["is_default"] = is_default
                data[f"{cat}_seconds"] += config.POLL_INTERVAL

            for audio_proc in get_playing_audio_apps():
                if audio_proc == proc:
                    continue
                entry = data["audio_apps"].setdefault(audio_proc, {"seconds": 0})
                entry["seconds"] += config.POLL_INTERVAL
        else:
            data["idle_seconds"] += config.POLL_INTERVAL

        report_time = now.replace(
            hour=config.REPORT_HOUR, minute=config.REPORT_MINUTE, second=0, microsecond=0
        )
        review_time = report_time - datetime.timedelta(seconds=config.REVIEW_WAIT_SECONDS + 30)

        if now >= review_time and not data.get("review_done") and not data.get("report_sent"):
            data = run_review(data, learned)
            data["review_done"] = True
            save_day(date_str, data)

        if now >= report_time and not data.get("report_sent"):
            send_telegram(build_report(date_str, data))
            data["report_sent"] = True

        save_day(date_str, data)
        time.sleep(config.POLL_INTERVAL)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log.info("Трекер остановлен вручную.")
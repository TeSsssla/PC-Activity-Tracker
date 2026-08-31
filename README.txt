[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Windows-blue)](https://www.microsoft.com/windows)

Track your PC activity, classify work vs distractions, and get daily reports in Telegram.

## ? Features

- **Automatic tracking** – monitors the active window every 5 seconds
- **Smart classification** – categorizes apps and websites as `work`, `distraction`, or `neutral`
- **Per?site tracking in browsers** – treats each website separately (no more lumping all of Chrome together)
- **Daily Telegram reports** – receive a summary with time breakdowns and a productivity score
- **Interactive learning** – mark unknown apps/sites via Telegram buttons; the bot remembers your choices
- **Background audio detection** – sees what’s playing sound (music, video) without affecting main classification
- **Idle detection** – ignores time without mouse/keyboard input
- **Privacy?first** – no keylogging, no screenshots, no clipboard access

## ?? Quick Start

### Prerequisites

- **Windows** OS
- **Python 3.8+**
- A **Telegram Bot Token** (get one from [@BotFather](https://t.me/botfather))

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/TeSsssla/PC-Activity-Tracker.git
   cd PC-Activity-Tracker
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up configuration**
   ```bash
   cp config.py.example config.py
   ```
   Then edit `config.py` with your Telegram credentials and preferences.

4. **Run the tracker**
   ```bash
   python tracker.py
   ```

5. **(Optional) Auto?start on boot** – place a shortcut to `run_silent_tg.vbs` in the Windows startup folder (`shell:startup`).

## ?? Telegram Setup

1. Create a bot via [@BotFather](https://t.me/botfather) and copy its token.
2. Find your `chat_id`:
   - Send `/start` to your bot.
   - Visit `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates` in a browser.
   - Look for `"chat":{"id": YOUR_ID}` in the response.
3. Fill both values in `config.py`.

## ?? Example Report

```
?? Report for 2026-08-31

Active PC time: 6h 23m (from 7h 45m total)
?? Work: 4h 15m (55%)
?? Distractions: 1h 10m (15%)
? Neutral/Unclassified: 58m (12%)
?? Idle: 1h 22m (18%)

? Score (work vs distractions): 7.8/10
?? Classification coverage: 82%

Top apps/sites:
?? chrome.exe: github.com — 1h 45m
?? chrome.exe: youtube.com — 45m
?? code.exe — 1h 30m
? explorer.exe — 30m

?? Background audio:
?? spotify.exe — 1h 20m
```

## ?? Customisation

- **Add new apps** – find the process name in Task Manager > Details tab, then add it to `APP_CATEGORIES` in `config.py`.
- **Add website rules** – extend the `TITLE_KEYWORDS` dictionary in `config.py` (e.g., `"jira": "work"`).
- **Change categories** – modify the `CATEGORIES` tuple in `tracker.py` (requires code changes).

## ?? Privacy

This tracker collects **only**:
- Process names and window titles
- Idle time (time since last mouse/keyboard input)

It **never** logs:
- Keystrokes ?
- Screenshots ?
- Clipboard contents ?
- Personal files ?

All data stays local in `%USERPROFILE%/PCTrack/` – the only external communication is the Telegram report you explicitly requested.

## ?? Data Storage

```
%USERPROFILE%/PCTrack/
+-- data/
¦   +-- 2026-08-31.json   # daily activity data
¦   L-- ...
+-- learned.json          # your saved classifications
+-- tracker.log           # debug logs
L-- tg_offset.txt         # Telegram state (do not touch)
```

## ?? Contributing

Contributions, issues, and feature requests are welcome! Feel free to open a pull request or an issue.

## ?? License

Distributed under the MIT License. See the `LICENSE` file for more details.

---

**Made with ?? for better productivity.**

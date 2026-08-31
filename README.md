# 🖥️ PC Activity Tracker

<div align="center">

![Python](https://img.shields.io/badge/Python-3.8%2B-blue?style=for-the-badge&logo=python)
![Windows](https://img.shields.io/badge/Windows-Only-00A4EF?style=for-the-badge&logo=windows)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)
![Telegram](https://img.shields.io/badge/Telegram-Bot-0088cc?style=for-the-badge&logo=telegram)

**Лёгкий трекер активности с умной классификацией и отчётами в Telegram**

[🚀 Быстрый старт](#-установка) • [⚙️ Настройка](#%EF%B8%8F-настройка) • [📖 Документация](#-как-это-работает) • [❓ FAQ](#-troubleshooting)

</div>

---

## ✨ Возможности

### 🎯 Умное отслеживание
- **Автоматический мониторинг** активного окна каждые 5 секунд
- **Детект бездействия** — не считает время, когда вы отошли от компьютера
- **Фоновый звук** — определяет, играет ли музыка/видео, не смешивая с основной активностью

### 🌐 Браузеры на максималках
- **Распознавание сайтов** через UI Automation (Chrome, Edge, Firefox, Opera, Яндекс)
- **Отдельная статистика** для каждого сайта, а не просто "chrome.exe"
- **Fallback на заголовки** — если UI Automation не сработал, использует заголовок вкладки

### 🤖 Telegram-бот с обучением
- **Ежедневные отчёты** с разбивкой времени и оценкой продуктивности
- **Интерактивная разметка** — бот спрашивает про неизвестные приложения через inline-кнопки
- **Запоминание выборов** — сохраняет ваши решения в `learned.json` для будущих дней

### 🔒 Приватность превыше всего
- ❌ **Нет** кейлоггинга
- ❌ **Нет** скриншотов
- ❌ **Нет** чтения буфера обмена
- ✅ Только имя процесса, заголовок окна и время последнего ввода

---

## 🚀 Установка

### Требования
- **Windows 10/11** (x64)
- **Python 3.8+** ([скачать](https://www.python.org/downloads/))
- **Telegram Bot Token** (получить у [@BotFather](https://t.me/BotFather))

### Шаг 1: Клонируйте репозиторий

```bash
git clone https://github.com/TeSsssla/PC-Activity-Tracker.git
cd PC-Activity-Tracker
```

### Шаг 2: Установите зависимости

```bash
pip install -r requirements.txt
```

### Шаг 3: Создайте конфигурацию

```bash
copy config.py.example config.py
```

Откройте `config.py` в любом текстовом редакторе и заполните обязательные поля:

```python
# Telegram (ОБЯЗАТЕЛЬНО ЗАПОЛНИТЬ!)
TELEGRAM_TOKEN = "1234567890:ABCdefGHIjklMNOpqrsTUVwxyz"  # Токен от @BotFather
TELEGRAM_CHAT_ID = "123456789"  # Ваш chat_id (как узнать — см. ниже)
```

### Шаг 4: Запустите трекер

```bash
python tracker.py
```

✅ Готово! Трекер начнёт собирать данные.

---

## ⚙️ Настройка

### Как получить Telegram Chat ID

1. Отправьте `/start` вашему боту
2. Откройте в браузере: `https://api.telegram.org/bot<ВАШ_ТОКЕН>/getUpdates`
3. Найдите строку `"chat":{"id": 123456789}` — это ваш `chat_id`

### Автозапуск при включении ПК

1. Нажмите `Win + R`, введите `shell:startup`, нажмите Enter
2. Скопируйте файл `run_silent_tg.vbs` в открывшуюся папку
3. **Важно**: убедитесь, что путь к `tracker.py` в `run_silent_tg.vbs` правильный:

```vbs
WshShell.Run "py -3 " & Chr(34) & "%USERPROFILE%\PCTrack\tracker.py" & Chr(34), 0, False
```

Если трекер лежит в другой папке, замените путь на актуальный.

---

## 🎨 Классификация активности

### Типы категорий

| Категория | Эмодзи | Описание |
|-----------|--------|----------|
| **Work** | 🟢 | Продуктивная работа |
| **Distraction** | 🔴 | Отвлечения (соцсети, игры) |
| **Neutral** | ⚪ | Системные приложения, неопределённое |

### Настройка правил в `config.py`

#### 1. Правила для приложений

```python
APP_CATEGORIES = {
    # Работа
    "code.exe": "work",           # VS Code
    "figma.exe": "work",          # Figma
    "excel.exe": "work",          # Excel
    
    # Отвлечения
    "telegram.exe": "distraction",
    "discord.exe": "distraction",
    "steam.exe": "distraction",
    
    # Нейтральное
    "explorer.exe": "neutral",    # Проводник
}
```

#### 2. Правила для сайтов (по заголовку вкладки)

```python
TITLE_KEYWORDS = {
    "github": "work",
    "stackoverflow": "work",
    "youtube": "distraction",
    "twitter": "distraction",
    "gmail": "neutral",
}
```

#### 3. Настройка времени отчёта

```python
REPORT_HOUR = 18      # Час отправки отчёта (24-часовой формат)
REPORT_MINUTE = 0     # Минута
```

---

## 📖 Как это работает

### Цикл работы трекера

```
Каждые 5 секунд:
  1. Проверка: активен ли пользователь? (нет ввода > 60 сек = idle)
  2. Получение активного окна и процесса
  3. Если это браузер → чтение URL через UI Automation
  4. Классификация: work / distraction / neutral
  5. Сохранение в JSON файл дня (2026-08-31.json)
  6. Параллельно: определение приложений со звуком

За 3 минуты до отчёта (17:57):
  - Бот присылает сообщения про неизвестные приложения с кнопками
  - Вы выбираете категорию → сохраняется в learned.json
  - Время пересчитывается с учётом ваших ответов

В 18:00:
  - Отправка финального отчёта в Telegram
```

### Структура данных

```
%USERPROFILE%/PCTrack/
├── data/
│   ├── 2026-08-31.json    # Данные за день
│   └── 2026-09-01.json
├── learned.json           # Ваши классификации
├── tracker.log            # Логи для отладки
└── tg_offset.txt          # Состояние Telegram API
```

---

## 📊 Пример отчёта

```
📊 Отчёт за 2026-08-31

Активное время за ПК: 6ч 23м (из 7ч 45м всего)
🟢 Работа: 4ч 15м (55%)
🔴 Отвлечения: 1ч 10м (15%)
⚪ Нейтральное: 58м (12%)
💤 Простой: 1ч 22м (18%)

⭐ Оценка (работа vs отвлечения): 7.8/10
🎯 Покрытие классификацией: 82%

Разбор по приложениям/сайтам:
🟢 chrome.exe: github.com — 1ч 45м
🔴 chrome.exe: youtube.com — 45м
🟢 code.exe — 1ч 30м
⚪ explorer.exe — 30м

🎵 Параллельно слушал/смотрел (фоном):
🎧 spotify.exe — 1ч 20м
```

---

## 🛠️ Для разработчиков

### Вспомогательный скрипт `find_omnibox.py`

Если UI Automation перестал читать адресную строку после обновления браузера, используйте этот скрипт для отладки:

```bash
python find_omnibox.py
```

Скрипт покажет ClassName и AutomationId адресной строки, которые нужно добавить в `tracker.py`:

```python
BROWSER_OMNIBOX_CLASSNAMES = {
    "chrome.exe": ["Chrome_OmniboxView", "OmniboxViewViews"],
    # Добавьте новые значения здесь
}
```

### Логи

Все логи пишутся в `%USERPROFILE%/PCTrack/tracker.log`. Полезные сообщения:

```
UI Automation не смог прочитать адресную строку chrome.exe: ...
Опрашиваю по неизвестным: ['telegram.exe', 'discord.exe']
Размечено кнопками: {'telegram.exe': 'distraction'}
Отчёт отправлен в Telegram.
```

---

## ❓ Troubleshooting

### Бот не присылает отчёт

1. Проверьте, что заполнены `TELEGRAM_TOKEN` и `TELEGRAM_CHAT_ID`
2. Убедитесь, что вы отправили `/start` боту
3. Проверьте логи: `%USERPROFILE%/PCTrack/tracker.log`

### UI Automation не читает адресную строку

- Это нормально для некоторых версий браузеров
- Трекер автоматически переключается на чтение заголовка вкладки
- Для исправления: запустите `find_omnibox.py` и обновите `BROWSER_OMNIBOX_CLASSNAMES`

### Трекер не запускается в фоне

- Убедитесь, что Python добавлен в PATH
- Проверьте путь в `run_silent_tg.vbs`
- Запустите `tracker.py` вручную через консоль, чтобы увидеть ошибки

### Данные не сохраняются

- Проверьте права доступа к `%USERPROFILE%/PCTrack/`
- Убедитесь, что антивирус не блокирует создание файлов

---

## 🤝 Contributing

Приветствуются:
- 🐛 Баг-репорты
- ✨ Новые фичи
- 📖 Улучшения документации
- 🌐 Поддержка Linux/macOS

Создайте Issue или Pull Request!

---

## 📄 Лицензия

Этот проект распространяется под лицензией MIT. См. файл `LICENSE` для деталей.

---

<div align="center">

**Сделано с ❤️ для продуктивности**

[⭐ Поставить звезду](https://github.com/TeSsssla/PC-Activity-Tracker) • [🐛 Сообщить о баге](https://github.com/TeSsssla/PC-Activity-Tracker/issues)

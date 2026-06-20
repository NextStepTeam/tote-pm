# Tote Package Manager

Tote — это простой пакетный менеджер на Python для Linux, который устанавливает, обновляет и удаляет пакеты, управляет репозиториями и хранит кеш локально.

## Основные компоненты

- `install.py` — установка Tote, зависимостей и сборка бинарника через PyInstaller.
- `update.py` — обновление Tote: пересборка и повторная установка бинарника.
- `uninstall.py` — полное удаление Tote из системы.
- `main.py` — основное CLI-приложение Tote.
- `utils/` — вспомогательные модули для парсинга Totefile, выполнения секций и работы с БД.

## Требования

- Linux
- Python 3
- `pip3`
- `git`
- `pyinstaller`
- `requests`
- `sqlalchemy`

## Быстрый старт

### Установка Tote

Запустите установку из корня проекта:

```bash
python3 install.py
```

Скрипт:

1. проверяет системные зависимости,
2. устанавливает Python-пакеты,
3. собирает бинарник `tote` через PyInstaller,
4. копирует его в системную или локальную папку,
5. создает конфигурационный файл.

### Обновление Tote

Чтобы пересобрать и поставить новую версию Tote, выполните:

```bash
python3 update.py
```

### Удаление Tote

Чтобы полностью удалить Tote из системы:

```bash
python3 uninstall.py
```

## Использование CLI

Запуск Tote производится через собранный бинарник `tote` или напрямую через `python3 main.py`.

### Команды

#### Показать информацию о пакете

```bash
python3 main.py info <package>
```

Если пакет описан в локальном Totefile:

```bash
python3 main.py info <path/to/Totefile> -f
```

#### Управление репозиториями

По умолчанию добавлен репозиторий:

```bash
https://raw.githubusercontent.com/NextStepTeam/tote-repo/refs/heads/main
```

Добавить репозиторий:

```bash
python3 main.py repo add <url>
```

Список репозиториев:

```bash
python3 main.py repo list
```

Информация о репозитории:

```bash
python3 main.py repo info <id>
```

Обновить репозиторий:

```bash
python3 main.py repo update <id>
```

Удалить репозиторий:

```bash
python3 main.py repo remove <id>
```

#### Установка пакета

Установка из репозитория:

```bash
python3 main.py install <package>
```

Установка из локального Totefile:

```bash
python3 main.py install <path/to/Totefile> -f
```

#### Обновление пакета

```bash
python3 main.py update <package>
```

Обновить все установленные пакеты:

```bash
python3 main.py update
```

#### Удаление пакета

```bash
python3 main.py remove <package>
```

#### Очистка кеша

```bash
python3 main.py clear_cache
```

## Конфигурация

По умолчанию Tote использует конфиг из:

- `/etc/tote/config.json` при запуске с sudo,
- `~/.config/tote/config.json` без sudo.

В режиме разработки `main.py` по умолчанию использует `sqlite:///test.db` и кеш в директории `cache`.

Вы можете передать собственный конфигурационный файл через флаг:

```bash
python3 main.py -c path/to/config.json <action>
```

## Структура проекта

- `main.py` — основной исполнительный скрипт CLI.
- `install.py` — установщик Tote.
- `update.py` — скрипт обновления Tote.
- `uninstall.py` — скрипт удаления Tote.
- `utils/db.py` — модель базы данных и работа с сессиями.
- `utils/parser.py` — парсер Totefile.
- `utils/execute.py` — выполнение секций `install`, `update`, `uninstall`.
- `build/`, `cache/` — временные директории и кеш пакетов.

## Примечания

- Проект рассчитан на Linux-системы.
- Для сборки используется PyInstaller, поэтому файлы `build/`, `dist/` и `*.spec` удаляются после установки.
- В `update.py` при отсутствии прав `sudo` бинарник устанавливается в `~/.local/bin`.

---

Если вы хотите развивать Tote дальше, начните с `utils/parser.py` и `utils/execute.py`, чтобы расширить формат Totefile и поведение установки пакетов.
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

### Глобальные флаги

- `-d, --debug` — режим отладки (вывод дополнительной информации об ошибках)
- `-v, --verbose` — подробный вывод (дополнительная информация, списки файлов и т.д.)
- `-c, --config <path>` — путь к кастомному конфигу

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

#### Системная диагностика

Показать информацию о конфиге, папках, БД, репозиториях и инстансах:

```bash
python3 main.py diagnostics
```

С подробным выводом (полный список файлов в кэше):

```bash
python3 main.py -v diagnostics
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

## Управление инстансами (Instances)

Tote поддерживает создание и управление инстансами приложений, описанных в `Totefile` пакета. Инстансы хранятся в кеше в директории `cache/instances/{id}`.

- Создать инстанс:

```bash
python3 main.py instance add <package> <id> -p <port> -c '{"KEY":"value"}'
```

- Запустить/поднять инстанс:

```bash
python3 main.py instance start <id>
```

- Остановить инстанс:

```bash
python3 main.py instance stop <id>
```

- Обновить инстанс (выполнить секцию update):

```bash
python3 main.py instance update <id>
```

- Удалить инстанс:

```bash
python3 main.py instance remove <id>
```

- Применить настройки к инстансу:

```bash
python3 main.py instance settings <id> -c 'ENV=prod,DEBUG=false'
```

Контекст (`-c`) поддерживает JSON или простые пары `key=value` через запятую. Порт можно явно указать через `-p`, иначе будет подобран свободный порт автоматически.

## Формат Totefile: секции INSTANCES

Чтобы Tote мог управлять инстансами пакета, в `Totefile` можно добавить секции `INSTANCES.*`. Пример:

```
[INSTANCES.CREATE]
RUN echo "Running instance create..."
[/INSTANCES.CREATE]

[INSTANCES.UP]
RUN echo "Running instance up..."
[/INSTANCES.UP]

[INSTANCES.STOP]
RUN echo "Running instance stop..."
[/INSTANCES.STOP]

[INSTANCES.UPDATE]
RUN echo "Running instance update..."
[/INSTANCES.UPDATE]

[INSTANCES.REMOVE]
RUN echo "Running instance remove..."
[/INSTANCES.REMOVE]

[INSTANCES.SETTINGS]
RUN echo "Running instance settings..."
[/INSTANCES.SETTINGS]
```

Секции выполняются командой `RUN` и получают контекстные переменные (например, `%port%` заменяется на номер порта). В `utils/execute.py` поддерживается подстановка контекста через синтаксис `%key%`.

## Отладка и тестирование

- Для быстрой проверки синтаксиса используйте:

```bash
python3 -m py_compile main.py
```

- Запуск конкретных секций `Totefile` можно тестировать локально, например, клонируя пакет в `cache/` и вызывая `execute_section` из тестового скрипта.

## Разработка

- Основные точки входа для расширения:
	- `utils/parser.py` — парсер Totefile (расширение синтаксиса секций и переменных)
	- `utils/execute.py` — выполнение команд (добавление новых директив, логирования)
	- `utils/db.py` — модели БД (добавление полей метаданных для инстансов)

Если хотите, могу добавить unit-тесты для парсера или небольшой пример пакета в `cache/ToteExample`.
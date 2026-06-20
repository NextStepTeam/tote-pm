import argparse
import sys
import requests
import os
import subprocess
import shutil
import json
from pathlib import Path
import socket
import random

from utils.parser import parse_totefile
from utils.execute import execute_section
from utils.db import *

# ========== Конфигурация ==========
def get_config():
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        home_dir = os.path.expanduser('~')
        config_dir = os.path.join(home_dir, '.config', 'tote')
        cache_dir = os.path.join(home_dir, '.cache', 'tote')
        os.makedirs(config_dir, exist_ok=True)
        os.makedirs(cache_dir, exist_ok=True)
        
        config_path = os.path.join(config_dir, 'config.json')
        db_path = os.path.join(config_dir, 'packages.db')
        
        default_config = {
            "db": f"sqlite:///{db_path}",
            "dirs": {
                "cache": cache_dir,
                "config": config_dir
            }
        }
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                user_config = json.load(f)
                default_config.update(user_config)
        return default_config
    else:
        return {
            "db": "sqlite:///test.db",
            "dirs": {
                "cache": "cache"
            }
        }

CONF = get_config()
DB = Database(CONF.get("db"))
DEFAULT_REPO_URL = "https://raw.githubusercontent.com/NextStepTeam/tote-repo/refs/heads/main"

# ========== Утилиты для репозиториев ==========
def normalize_repo_url(url: str) -> str:
    return url.rstrip('/')


def get_metadata_url(url: str) -> str:
    url = normalize_repo_url(url)
    return url if url.endswith('/metadata.json') else f"{url}/metadata.json"


def fetch_repo_metadata(url: str) -> dict:
    metadata_url = get_metadata_url(url)
    result = requests.get(metadata_url, timeout=10)
    result.raise_for_status()
    return result.json()


def ensure_default_repo():
    with DB.get_session() as s:
        existing = s.query(Repo).filter(Repo.url == DEFAULT_REPO_URL).first()
        if existing:
            return

        try:
            data = fetch_repo_metadata(DEFAULT_REPO_URL)
            repo = Repo(url=DEFAULT_REPO_URL, rid=data.get("id"), repo_metadata={"name": data.get("name")})
            s.add(repo)

            for pkg_id, package in data.get("packages", {}).items():
                tote = parse_totefile(requests.get(package.get("url")).text)
                s.add(Package(
                    repo=repo,
                    pid=pkg_id,
                    package_metadata={
                        "url": package.get("url"),
                        "name": package.get("name"),
                        "totefile": {
                            "use": tote.use,
                            "name": tote.name,
                            "description": tote.description,
                            "deps": tote.deps
                        }
                    }
                ))
            s.commit()
            print(f"ℹ️ Стандартный репозиторий добавлен: {DEFAULT_REPO_URL}")
        except Exception as e:
            print(f"⚠️ Не удалось добавить стандартный репозиторий: {e}")


ensure_default_repo()


def find_free_port(start_port=10000, end_port=65535, max_attempts=100):
    """
    Находит случайный свободный порт в заданном диапазоне.
    
    Args:
        start_port: Начало диапазона (включительно)
        end_port: Конец диапазона (включительно)
        max_attempts: Максимальное количество попыток
    
    Returns:
        int: Номер свободного порта или None, если не найден
    """
    
    if start_port < 1 or end_port > 65535:
        raise ValueError("Порт должен быть в диапазоне 1-65535")
    
    if start_port > end_port:
        raise ValueError("start_port должен быть меньше или равен end_port")
    
    # Получаем список уже занятых портов для проверки
    used_ports = set()
    
    for attempt in range(max_attempts):
        # Генерируем случайный порт в заданном диапазоне
        port = random.randint(start_port, end_port)
        
        # Пропускаем, если порт уже проверяли в этой сессии
        if port in used_ports:
            continue
        
        used_ports.add(port)
        
        # Проверяем, свободен ли порт
        if is_port_free(port):
            return port
    
    return None

def is_port_free(port):
    """
    Проверяет, свободен ли указанный порт.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            # Пытаемся привязаться к порту
            s.bind(('', port))
            return True
        except OSError:
            # Порт занят или недоступен
            return False

def find_free_port_simple(start_port=10000, end_port=65535):
    """
    Простая версия: перебирает порты по порядку до первого свободного.
    """
    for port in range(start_port, end_port + 1):
        if is_port_free(port):
            return port
    return None

# ========== Аргументы командной строки ==========
#region args
parser = argparse.ArgumentParser(
    description="Tote Package Manager",
    formatter_class=argparse.RawDescriptionHelpFormatter
)
parser.add_argument('-d', '--debug', required=False, action='store_true',
                   help="Включить режим отладки")
parser.add_argument('-c', '--config', required=False,
                   help="Путь к файлу конфигурации")
parser.add_argument('-v', '--verbose', required=False, action='store_true',
                   help="Подробный вывод (дополнительная информация)")

subparsers = parser.add_subparsers(dest='action', required=True)

# Info
info_parser = subparsers.add_parser('info', help="Показать информацию о пакете")
info_parser.add_argument('package')
info_parser.add_argument('-r', '--repo', required=False)
info_parser.add_argument('-f', '--file', required=False, action='store_true')

# Repo
repo_parser = subparsers.add_parser('repo', help="Управление репозиториями")
repo_subparsers = repo_parser.add_subparsers(dest='repo_action', required=True)

repo_add_parser = repo_subparsers.add_parser('add')
repo_add_parser.add_argument('url')

repo_list_parser = repo_subparsers.add_parser('list')

repo_info_parser = repo_subparsers.add_parser('info')
repo_info_parser.add_argument('id')

repo_update_parser = repo_subparsers.add_parser('update', help="Обновить репозиторий")
repo_update_parser.add_argument('id')

repo_remove_parser = repo_subparsers.add_parser('remove')
repo_remove_parser.add_argument('id')

# Install
install_parser = subparsers.add_parser('install', help="Установить пакет")
install_parser.add_argument('package', help="Имя пакета или путь к Totefile")
install_parser.add_argument('-f', '--file', required=False, action='store_true',
                           help="Установка из локального файла")
install_parser.add_argument('-i', '--id', required=False,
                           help="ID пакета при установке из файла")

# Remove
remove_parser = subparsers.add_parser('remove', help="Удалить пакет")
remove_parser.add_argument('package')
remove_parser.add_argument('-f', '--file', required=False, action='store_true')
remove_parser.add_argument('-i', '--id', required=False)

# Update
update_parser = subparsers.add_parser('update', help="Обновить пакет или все установленные пакеты")
update_parser.add_argument('package', nargs='?', help="Имя пакета или путь к Totefile")
update_parser.add_argument('-f', '--file', required=False, action='store_true')
update_parser.add_argument('-i', '--id', required=False)


# Instances
instances_parser = subparsers.add_parser('instance', help="Управление инстансами")
instances_subparsers = instances_parser.add_subparsers(dest='instances_action', required=True)
# Add
instances_add_subparsers = instances_subparsers.add_parser('add')
instances_add_subparsers.add_argument('package', help="Имя пакета")
instances_add_subparsers.add_argument('id', help='Идентификатор инстанса')
instances_add_subparsers.add_argument('-p', '--port', help='Порт', required=False)
instances_add_subparsers.add_argument('-c', '--context', help='Дополнительный контекст', required=False)
# Start
instances_start_subparsers = instances_subparsers.add_parser('start')
instances_start_subparsers.add_argument('id', help='Идентификатор инстанса')
# Update
instances_update_subparsers = instances_subparsers.add_parser('update')
instances_update_subparsers.add_argument('id', help='Идентификатор инстанса')
# Stop
instances_stop_subparsers = instances_subparsers.add_parser('stop')
instances_stop_subparsers.add_argument('id', help='Идентификатор инстанса')
# Config
instances_config_subparsers = instances_subparsers.add_parser('settings')
instances_config_subparsers.add_argument('id', help='Идентификатор инстанса')

# Clear cache
cc_parser = subparsers.add_parser('clear_cache', help="Очистить кэш")

# Diagnostics
diag_parser = subparsers.add_parser('diagnostics', help="Показать системную и отладочную информацию")

args = parser.parse_args()
#endregion
# Обновляем конфиг если передан через аргументы
if args.config:
    with open(args.config, 'r', encoding='utf-8') as f:
        CONF.update(json.load(f))

# ========== Вспомогательные функции ==========
def print_debug(*msgs):
    if args.debug:
        print("[DEBUG]", *msgs)

def confirm(prompt: str) -> bool:
    return input(f"{prompt} (y/N): ").lower() in ["y", "yes", "д", "да"]

def get_cache_dir():
    return os.path.join(os.getcwd(), CONF.get("dirs", {}).get("cache", "cache"))

def ensure_cache_dir():
    cache_dir = get_cache_dir()
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)
    return cache_dir


def parse_context_arg(ctx):
    """
    Преобразовать строку контекста в словарь.
    Поддерживает JSON или формат key=value,key2=value2.
    """
    if not ctx:
        return {}
    ctx = ctx.strip()
    # Попробуем JSON
    try:
        return json.loads(ctx)
    except Exception:
        parts = [p.strip() for p in ctx.split(',') if p.strip()]
        d = {}
        for p in parts:
            if '=' in p:
                k, v = p.split('=', 1)
                d[k.strip()] = v.strip()
            else:
                d[p] = True
        return d

# ========== Основная логика ==========
original_dir = os.getcwd()

try:
    if args.action == 'info':
        if args.file:
            # Информация из файла
            if not os.path.exists(args.package):
                print(f"❌ Файл '{args.package}' не найден")
                sys.exit(1)
                
            with open(args.package, 'r', encoding='utf-8') as file:
                recipe = parse_totefile(file.read())
            if args.debug:
                print(recipe)
            else:
                print(f"📦 {recipe.name}")
                print(f"📝 {recipe.description}")
                print(f"🔗 Зависимости: {', '.join(recipe.deps) if recipe.deps else 'нет'}")
        else:
            # Информация из репозитория
            with DB.get_session() as s:
                pkg = s.query(Package).filter(Package.pid == args.package).first()
                if not pkg:
                    print(f"❌ Пакет '{args.package}' не найден")
                    sys.exit(1)
                meta = pkg.package_metadata.get("totefile", {})
                print(f"📦 {meta.get('name', args.package)}")
                print(f"📝 {meta.get('description', 'Нет описания')}")
                deps = meta.get('deps', [])
                print(f"🔗 Зависимости: {', '.join(deps) if deps else 'нет'}")

    elif args.action == "repo":
        if args.repo_action == "add":
            url = f"{args.url}/metadata.json"
            try:
                result = requests.get(url, timeout=10)
                result.raise_for_status()
                data = result.json()
            except Exception as e:
                print(f"❌ Ошибка загрузки репозитория: {e}")
                sys.exit(1)

            print_debug(result.text, data)
            print(f"📦 Добавление репозитория: {data.get('name')}")

            if confirm("Подтвердите добавление"):
                with DB.get_session() as s:
                    repo = Repo(url=args.url, rid=data.get("id"), repo_metadata={"name": data.get("name")})
                    s.add(repo)

                    for pkg_id, package in data.get("packages", {}).items():
                        print(f"  ➕ {package.get('name')}")
                        tote = parse_totefile(requests.get(package.get("url")).text)
                        s.add(Package(
                            repo=repo,
                            pid=pkg_id,
                            package_metadata={
                                "url": package.get("url"),
                                "name": package.get("name"),
                                "totefile": {
                                    "use": tote.use,
                                    "name": tote.name,
                                    "description": tote.description,
                                    "deps": tote.deps
                                }
                            }
                        ))
                    s.commit()
                    print("✅ Добавление завершено")

        elif args.repo_action == "list":
            print("📋 Список репозиториев:")
            with DB.get_session() as s:
                for repo in s.query(Repo).all():
                    print(f"  - {repo.repo_metadata.get('name', 'Unnamed')} ({repo.rid})")

        elif args.repo_action == "info":
            with DB.get_session() as s:
                repo = s.query(Repo).filter(Repo.rid == args.id).first()
                if not repo:
                    print(f"❌ Репозиторий '{args.id}' не найден")
                    sys.exit(1)
                print(f"📦 {repo.repo_metadata.get('name', 'Unnamed')}")
                for pkg in repo.packages:
                    print(f"  - {pkg.package_metadata.get('name', pkg.pid)} ({pkg.pid})")

        elif args.repo_action == "update":
            with DB.get_session() as s:
                repo = s.query(Repo).filter(Repo.rid == args.id).first()
                if not repo:
                    repo = s.query(Repo).filter(Repo.url == args.id).first()
                if not repo:
                    print(f"❌ Репозиторий '{args.id}' не найден")
                    sys.exit(1)

                try:
                    data = fetch_repo_metadata(repo.url)
                except Exception as e:
                    print(f"❌ Ошибка загрузки метаданных репозитория: {e}")
                    sys.exit(1)

                repo.repo_metadata = {"name": data.get("name")}
                if data.get("id"):
                    repo.rid = data.get("id")

                existing_packages = list(repo.packages)
                for pkg in existing_packages:
                    s.delete(pkg)

                for pkg_id, package in data.get("packages", {}).items():
                    print(f"  ➕ {package.get('name')}")
                    tote = parse_totefile(requests.get(package.get("url")).text)
                    s.add(Package(
                        repo=repo,
                        pid=pkg_id,
                        package_metadata={
                            "url": package.get("url"),
                            "name": package.get("name"),
                            "totefile": {
                                "use": tote.use,
                                "name": tote.name,
                                "description": tote.description,
                                "deps": tote.deps
                            }
                        }
                    ))
                s.commit()
                print(f"✅ Репозиторий '{repo.repo_metadata.get('name', repo.rid)}' обновлён")

        elif args.repo_action == "remove":
            with DB.get_session() as s:
                repo = s.query(Repo).filter(Repo.rid == args.id).first()
                if not repo:
                    print(f"❌ Репозиторий '{args.id}' не найден")
                    sys.exit(1)
                print(f"🗑️ Удаление: {repo.repo_metadata.get('name', 'Unnamed')}")
                if confirm("Подтвердите удаление"):
                    s.delete(repo)
                    s.commit()
                    print("✅ Репозиторий удалён")

    elif args.action == 'diagnostics':
        # Печать общей системной информации
        print("** Diagnostics **")
        print(f"Рабочая директория: {os.getcwd()}")
        try:
            import getpass, platform
            print(f"Пользователь: {getpass.getuser()}")
            print(f"Платформа: {platform.system()} {platform.release()} ({platform.machine()})")
            print(f"Python: {platform.python_version()}")
        except Exception:
            pass

        print(f"Debug флаг: {args.debug}")
        print(f"Конфиг (CONF): {json.dumps(CONF, ensure_ascii=False)}")
        print(f"DB URL: {CONF.get('db')}")

        # Кэш и папки
        cache_dir = get_cache_dir()
        print(f"Cache dir: {cache_dir}")
        if os.path.exists(cache_dir):
            try:
                entries = os.listdir(cache_dir)
                print(f"Содержимое cache/: {entries}")
                if args.verbose:
                    for root, dirs, files in os.walk(cache_dir):
                        print(f"-- {root} --")
                        for d in dirs:
                            print(f"DIR: {os.path.join(root, d)}")
                        for f in files:
                            p = os.path.join(root, f)
                            try:
                                size = os.path.getsize(p)
                            except Exception:
                                size = 'n/a'
                            print(f"FILE: {p} ({size} bytes)")
            except Exception as e:
                print(f"Ошибка при перечислении cache/: {e}")
        else:
            print("Cache не найден")

        # БД: репозитории, пакеты, установленные, инстансы
        try:
            with DB.get_session() as s:
                print("Repos:")
                for repo in s.query(Repo).all():
                    print(f" - {repo.repo_metadata.get('name','Unnamed')} ({repo.rid}) -> {repo.url}")

                print("Packages (registered):")
                for pkg in s.query(Package).all():
                    print(f" - {pkg.pid}: {pkg.package_metadata.get('name')}")

                print("Installed packages:")
                for ip in s.query(InstalledPackage).all():
                    print(f" - {ip.package} -> {ip.package_metadata}")

                print("Instances:")
                for ins in s.query(Instance).all():
                    print(f" - {ins.iid}: package={ins.package}, dir={ins.dir}, context={ins.context}")
        except Exception as e:
            print(f"Ошибка при запросе БД: {e}")

    elif args.action == "install":
        # Если установка из файла
        if args.file:
            # Проверяем, что файл существует
            if not os.path.exists(args.package):
                print(f"❌ Файл '{args.package}' не найден")
                sys.exit(1)
            
            # Определяем имя пакета
            pkg_name = args.id or os.path.splitext(os.path.basename(args.package))[0]
            print(f"📦 Установка из файла: {pkg_name}")
            
            if not confirm("Подтвердите установку"):
                sys.exit(0)
            
            # Читаем Totefile
            with open(args.package, 'r', encoding='utf-8') as f:
                recipe = parse_totefile(f.read())
            
            cache_dir = ensure_cache_dir()
            
            try:
                # Создаем директорию для пакета в кэше
                pkg_dir = os.path.join(cache_dir, pkg_name)
                if os.path.exists(pkg_dir):
                    shutil.rmtree(pkg_dir)
                os.makedirs(pkg_dir)
                
                # Копируем Totefile в рабочую директорию
                shutil.copy2(args.package, os.path.join(pkg_dir, 'Totefile'))
                
                # Переходим в директорию пакета
                if args.id != "tote":
                    os.chdir(pkg_dir)
                print_debug(f"Working dir: {os.getcwd()}")
                
                # Выполняем установку
                if not execute_section(recipe, "install"):
                    print("❌ Ошибка при выполнении секции install")
                    sys.exit(1)
                
                # Сохраняем в установленные
                with DB.get_session() as s:
                    # Проверяем, не установлен ли уже
                    existing = s.query(InstalledPackage).filter(InstalledPackage.package == pkg_name).first()
                    if existing:
                        print(f"⚠️ Пакет '{pkg_name}' уже установлен, обновляем")
                        s.delete(existing)
                    
                    installed = InstalledPackage(
                        package=pkg_name,
                        package_metadata={"cache_dir": os.getcwd()}
                    )
                    s.add(installed)
                    s.commit()
                
                print(f"✅ Пакет '{pkg_name}' успешно установлен из файла")
                
            except Exception as e:
                print(f"❌ Ошибка установки: {e}")
                if args.debug:
                    import traceback
                    traceback.print_exc()
                sys.exit(1)
            finally:
                os.chdir(original_dir)
        
        else:
            # Установка из репозитория
            with DB.get_session() as s:
                pkg = s.query(Package).filter(Package.pid == args.package).first()
                if not pkg:
                    print(f"❌ Пакет '{args.package}' не найден в репозиториях")
                    print("💡 Используйте -f для установки из локального файла")
                    sys.exit(1)

                # Проверка на уже установленный
                existing = s.query(InstalledPackage).filter(InstalledPackage.package == args.package).first()
                if existing:
                    print(f"⚠️ Пакет '{args.package}' уже установлен")
                    if not confirm("Переустановить?"):
                        sys.exit(0)

                if not confirm(f"Установить {pkg.package_metadata.get('name', args.package)}?"):
                    sys.exit(0)

                cache_dir = ensure_cache_dir()
                os.chdir(cache_dir)

                try:
                    repo_url = pkg.package_metadata.get("totefile", {}).get("use")
                    if not repo_url:
                        print("❌ Не указан URL репозитория в Totefile")
                        sys.exit(1)

                    cmd = ["git", "clone", repo_url]
                    result = subprocess.run(cmd, capture_output=True, text=True)
                    if result.returncode != 0:
                        print(f"❌ Ошибка клонирования: {result.stderr}")
                        sys.exit(1)

                    repo_name = repo_url.split("/")[-1]
                    if repo_name.endswith(".git"):
                        repo_name = repo_name[:-4]
                    os.chdir(os.path.join(cache_dir, repo_name))

                    with open('Totefile', 'r', encoding='utf-8') as f:
                        recipe = parse_totefile(f.read())
                        if not execute_section(recipe, "install"):
                            print("❌ Ошибка при выполнении секции install")
                            sys.exit(1)

                    installed = InstalledPackage(
                        package=args.package,
                        package_metadata={"cache_dir": os.getcwd()}
                    )
                    s.add(installed)
                    s.commit()
                    print(f"✅ Пакет '{args.package}' успешно установлен")

                except Exception as e:
                    print(f"❌ Ошибка установки: {e}")
                    sys.exit(1)
                finally:
                    os.chdir(original_dir)

    elif args.action == "update":
        if not args.package:
            print("📦 Обновление всех установленных пакетов")
            with DB.get_session() as s:
                installed_list = s.query(InstalledPackage).all()
                if not installed_list:
                    print("ℹ️ Нет установленных пакетов для обновления")
                    sys.exit(0)

                for installed in installed_list:
                    package_name = installed.package
                    cache_dir = installed.package_metadata.get("cache_dir")
                    if not cache_dir or not os.path.exists(cache_dir):
                        print(f"⚠️ Пропуск '{package_name}': кэш не найден")
                        continue

                    print(f"🔄 Обновление пакета: {package_name}")
                    if args.id != "tote":
                        os.chdir(cache_dir)
                    try:
                        with open('Totefile', 'r', encoding='utf-8') as f:
                            recipe = parse_totefile(f.read())
                            execute_section(recipe, "update")
                        print(f"✅ Пакет '{package_name}' обновлён")
                    except Exception as e:
                        print(f"❌ Ошибка обновления '{package_name}': {e}")
                    finally:
                        os.chdir(original_dir)
        else:
            with DB.get_session() as s:
                installed = s.query(InstalledPackage).filter(InstalledPackage.package == args.package).first()
                if not installed:
                    print(f"❌ Пакет '{args.package}' не установлен")
                    sys.exit(1)

                cache_dir = installed.package_metadata.get("cache_dir")
                if not cache_dir or not os.path.exists(cache_dir):
                    print(f"❌ Кэш для '{args.package}' не найден")
                    sys.exit(1)

                if args.id != "tote":
                    os.chdir(cache_dir)
                try:
                    with open('Totefile', 'r', encoding='utf-8') as f:
                        recipe = parse_totefile(f.read())
                        execute_section(recipe, "update")
                    print(f"✅ Пакет '{args.package}' обновлён")
                except Exception as e:
                    print(f"❌ Ошибка обновления: {e}")
                finally:
                    os.chdir(original_dir)

    elif args.action == "remove":
        with DB.get_session() as s:
            installed = s.query(InstalledPackage).filter(InstalledPackage.package == args.package).first()
            if not installed:
                print(f"❌ Пакет '{args.package}' не установлен")
                sys.exit(1)

            cache_dir = installed.package_metadata.get("cache_dir")
            if cache_dir and os.path.exists(cache_dir):
                if args.id != "tote":
                    os.chdir(cache_dir)
                try:
                    with open('Totefile', 'r', encoding='utf-8') as f:
                        recipe = parse_totefile(f.read())
                        execute_section(recipe, "uninstall")
                except Exception as e:
                    print(f"⚠️ Ошибка при удалении: {e}")

            if cache_dir and os.path.exists(cache_dir):
                shutil.rmtree(cache_dir, ignore_errors=True)

            s.delete(installed)
            s.commit()
            print(f"✅ Пакет '{args.package}' удалён")
            os.chdir(original_dir)

    elif args.action == "clear_cache":
        print("⚠️ Удаление кэша может привести к проблемам с установленными пакетами!")
        if confirm("Подтвердите очистку"):
            cache_dir = get_cache_dir()
            if os.path.exists(cache_dir):
                shutil.rmtree(cache_dir)
                os.makedirs(cache_dir)
                print("✅ Кэш очищен")
            else:
                print("ℹ️ Кэш не найден")

    elif args.action == 'instance':
        # Обработка действий с инстансами: add, start, update, stop, remove, settings
        if args.instances_action == 'add':
            port = int(args.port) if args.port else find_free_port_simple()
            with DB.get_session() as s:
                installed = s.query(InstalledPackage).filter(InstalledPackage.package == args.package).first()
                if not installed:
                    print(f"❌ Пакет '{args.package}' не установлен")
                    sys.exit(1)

                package_cache = installed.package_metadata.get("cache_dir")
                if not package_cache or not os.path.exists(package_cache):
                    print(f"❌ Кэш пакета не найден: {package_cache}")
                    sys.exit(1)

                cache_dir = ensure_cache_dir()
                instances_root = os.path.join(cache_dir, 'instances')
                os.makedirs(instances_root, exist_ok=True)

                instance_dir = os.path.join(instances_root, args.id)
                # Если уже есть — удалим чтобы создать чистый инстанс
                if os.path.exists(instance_dir):
                    shutil.rmtree(instance_dir)
                # Копируем файлы пакета в папку инстанса
                shutil.copytree(package_cache, instance_dir)

                # Парсим Totefile и выполняем секцию создания
                try:
                    os.chdir(instance_dir)
                    with open('Totefile', 'r', encoding='utf-8') as f:
                        recipe = parse_totefile(f.read())

                    context = parse_context_arg(args.context) if getattr(args, 'context', None) else {}
                    context['port'] = port

                    if not execute_section(recipe, 'instances.create', context=context):
                        print('❌ Ошибка при выполнении секции instances.create')
                        sys.exit(1)

                    inst = Instance(package=args.package, iid=args.id, dir=instance_dir, context=context)
                    s.add(inst)
                    s.commit()
                    print(f"✅ Инстанс '{args.id}' создан в {instance_dir} (port={port})")
                except Exception as e:
                    print(f"❌ Ошибка при создании инстанса: {e}")
                    if args.debug:
                        import traceback
                        traceback.print_exc()
                    sys.exit(1)
                finally:
                    os.chdir(original_dir)

        elif args.instances_action in ('start', 'update', 'stop', 'remove', 'settings'):
            # Найти инстанс по iid
            with DB.get_session() as s:
                inst = s.query(Instance).filter(Instance.iid == args.id).first()
                if not inst:
                    print(f"❌ Инстанс '{args.id}' не найден")
                    sys.exit(1)

                inst_dir = inst.dir
                if not inst_dir or not os.path.exists(inst_dir):
                    print(f"❌ Директория инстанса не найдена: {inst_dir}")
                    sys.exit(1)

                # Определяем соответствующую секцию в Totefile
                action_to_section = {
                    'start': 'instances.up',
                    'update': 'instances.update',
                    'stop': 'instances.stop',
                    'remove': 'instances.remove',
                    'settings': 'instances.settings'
                }
                section = action_to_section.get(args.instances_action)

                try:
                    os.chdir(inst_dir)
                    with open('Totefile', 'r', encoding='utf-8') as f:
                        recipe = parse_totefile(f.read())

                    # Контекст берем из сохранённого инстанса, можно дополнить аргументом
                    saved_context = inst.context or {}
                    extra_context = parse_context_arg(args.context) if getattr(args, 'context', None) else {}
                    saved_context.update(extra_context)

                    if not execute_section(recipe, section, context=saved_context):
                        print(f"❌ Ошибка при выполнении секции {section}")
                        sys.exit(1)

                    # При удалении — удалить папку и запись
                    if args.instances_action == 'remove':
                        shutil.rmtree(inst_dir, ignore_errors=True)
                        s.delete(inst)
                        s.commit()
                        print(f"✅ Инстанс '{args.id}' удалён")
                    else:
                        print(f"✅ Действие '{args.instances_action}' выполнено для инстанса '{args.id}'")
                except Exception as e:
                    print(f"❌ Ошибка при обработке инстанса: {e}")
                    if args.debug:
                        import traceback
                        traceback.print_exc()
                    sys.exit(1)
                finally:
                    os.chdir(original_dir)

        

except KeyboardInterrupt:
    print("\n⏹️ Операция прервана")
    sys.exit(1)
except Exception as e:
    print(f"❌ Критическая ошибка: {e}")
    if args.debug:
        import traceback
        traceback.print_exc()
    sys.exit(1)
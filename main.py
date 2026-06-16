import argparse
import sys
import requests
import os
import subprocess
import shutil
import json
from pathlib import Path

from utils.parser import parse_totefile
from utils.execute import execute_section
from utils.db import *

# ========== Конфигурация ==========
def get_config():
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        base_dir = os.path.dirname(sys.executable)
        config_path = os.path.join(base_dir, 'config.json')
        default_config = {
            "db": "sqlite:///packages.db",
            "dirs": {
                "cache": "cache",
                "config": "config"
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

# ========== Аргументы командной строки ==========
parser = argparse.ArgumentParser(
    description="Tote Package Manager",
    formatter_class=argparse.RawDescriptionHelpFormatter
)
parser.add_argument('-d', '--debug', required=False, action='store_true',
                   help="Включить режим отладки")
parser.add_argument('-c', '--config', required=False,
                   help="Путь к файлу конфигурации")

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
update_parser = subparsers.add_parser('update', help="Обновить пакет")
update_parser.add_argument('package')
update_parser.add_argument('-f', '--file', required=False, action='store_true')
update_parser.add_argument('-i', '--id', required=False)

# Clear cache
cc_parser = subparsers.add_parser('clear_cache', help="Очистить кэш")

args = parser.parse_args()

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

except KeyboardInterrupt:
    print("\n⏹️ Операция прервана")
    sys.exit(1)
except Exception as e:
    print(f"❌ Критическая ошибка: {e}")
    if args.debug:
        import traceback
        traceback.print_exc()
    sys.exit(1)
#!/usr/bin/env python3
"""
Удаление Tote Package Manager
Полностью удаляет Tote из системы
"""

import os
import sys
import subprocess
import shutil
import json
import platform
from pathlib import Path

# ========== Конфигурация ==========
CONFIG = {
    "app_name": "tote",
    "binary_dir": "/usr/local/bin",
    "config_dir": "/etc/tote"
}

# ========== Цвета для вывода ==========
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_ok(msg):
    print(f"{Colors.GREEN}✅ {msg}{Colors.RESET}")

def print_warn(msg):
    print(f"{Colors.YELLOW}⚠️ {msg}{Colors.RESET}")

def print_error(msg):
    print(f"{Colors.RED}❌ {msg}{Colors.RESET}")

def print_info(msg):
    print(f"{Colors.CYAN}ℹ️ {msg}{Colors.RESET}")

def print_step(msg):
    print(f"\n{Colors.BOLD}{Colors.BLUE}▶ {msg}{Colors.RESET}")

def print_title():
    print(f"""
{Colors.RED}╔══════════════════════════════════════════════════════════╗
║                                                              ║
║     {Colors.BOLD}УДАЛЕНИЕ TOTE PACKAGE MANAGER{Colors.RED}                  ║
║                                                              ║
║     ⚠️  {Colors.YELLOW}Это действие необратимо!{Colors.RED}                  ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝{Colors.RESET}
    """)

# ========== Проверка системы ==========
def check_system():
    """Проверяет системные требования"""
    if platform.system() != "Linux":
        print_error("Поддерживается только Linux")
        sys.exit(1)
    print_ok(f"Система: {platform.system()} {platform.release()}")

def check_installation():
    """Проверяет, установлен ли Tote"""
    if not shutil.which(CONFIG["app_name"]):
        print_error("Tote не установлен")
        sys.exit(1)
    
    print_ok("Tote найден в системе")

def check_sudo():
    """Проверяет права sudo"""
    if os.geteuid() != 0:
        print_warn("Нет прав администратора. Удаление может быть неполным")
        return False
    return True

# ========== Поиск всех файлов Tote ==========
def find_tote_files():
    """Находит все файлы, связанные с Tote"""
    print_step("Поиск файлов Tote")
    
    files_to_remove = []
    
    # Бинарники
    binary_paths = [
        Path(CONFIG["binary_dir"]) / CONFIG["app_name"],
        Path.home() / ".local" / "bin" / CONFIG["app_name"],
        Path.home() / "bin" / CONFIG["app_name"],
        Path("/usr/bin") / CONFIG["app_name"],
        Path("/usr/local/bin") / CONFIG["app_name"]
    ]
    
    for path in binary_paths:
        if path.exists():
            files_to_remove.append(path)
            print_info(f"Найден бинарник: {path}")
    
    # Конфиги
    config_paths = [
        Path(CONFIG["config_dir"]) / "config.json",
        Path.home() / ".config" / "tote" / "config.json",
        Path.home() / ".tote" / "config.json"
    ]
    
    for path in config_paths:
        if path.exists():
            files_to_remove.append(path)
            print_info(f"Найден конфиг: {path}")
    
    # Папки конфигов
    config_dirs = [
        Path(CONFIG["config_dir"]),
        Path.home() / ".config" / "tote",
        Path.home() / ".tote"
    ]
    
    for path in config_dirs:
        if path.exists() and path.is_dir():
            # Проверяем, пустая ли папка или содержит только наш конфиг
            if path == Path(CONFIG["config_dir"]):
                # Системный конфиг удаляем только если он пустой
                if not any(path.iterdir()):
                    files_to_remove.append(path)
                    print_info(f"Найдена пустая папка: {path}")
            else:
                # Пользовательские папки удаляем всегда
                files_to_remove.append(path)
                print_info(f"Найдена папка: {path}")
    
    # Кэш
    cache_paths = [
        Path("/var/cache/tote"),
        Path.home() / ".cache" / "tote"
    ]
    
    for path in cache_paths:
        if path.exists():
            files_to_remove.append(path)
            print_info(f"Найден кэш: {path}")
    
    return files_to_remove

# ========== Удаление пакетов Python ==========
def remove_python_packages():
    """Удаляет Python пакеты, установленные для Tote"""
    print_step("Удаление Python пакетов")
    
    packages = ["tote-package-manager", "pyinstaller"]
    
    for pkg in packages:
        try:
            # Проверяем, установлен ли пакет
            result = subprocess.run(
                ["pip3", "show", pkg],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                subprocess.run(
                    ["pip3", "uninstall", "-y", pkg],
                    capture_output=True,
                    text=True,
                    check=True
                )
                print_ok(f"Удален пакет: {pkg}")
        except subprocess.CalledProcessError:
            print_info(f"Пакет {pkg} не найден")
        except Exception as e:
            print_error(f"Ошибка удаления {pkg}: {e}")

# ========== Удаление файлов ==========
def remove_files(files_to_remove):
    """Удаляет найденные файлы"""
    print_step("Удаление файлов")
    
    if not files_to_remove:
        print_info("Файлы для удаления не найдены")
        return True
    
    # Показываем что будем удалять
    print_warn("Будут удалены следующие файлы и папки:")
    for path in files_to_remove:
        print(f"  - {path}")
    
    if not input("\nПродолжить удаление? (y/N): ").lower() in ["y", "yes", "д", "да"]:
        print_info("Удаление отменено")
        return False
    
    # Удаляем
    for path in files_to_remove:
        try:
            if path.is_dir():
                shutil.rmtree(path)
                print_ok(f"Удалена папка: {path}")
            else:
                path.unlink()
                print_ok(f"Удален файл: {path}")
        except PermissionError:
            print_error(f"Нет прав на удаление: {path}")
            if check_sudo():
                print_info("Попробуйте запустить с sudo")
            return False
        except Exception as e:
            print_error(f"Ошибка удаления {path}: {e}")
            return False
    
    return True

# ========== Очистка PATH ==========
def clean_path():
    """Очищает PATH от ссылок на Tote (только shell функции)"""
    print_step("Очистка PATH")
    
    shell_configs = [
        Path.home() / ".bashrc",
        Path.home() / ".zshrc",
        Path.home() / ".profile",
        Path.home() / ".bash_profile"
    ]
    
    for config in shell_configs:
        if config.exists():
            try:
                with open(config, 'r') as f:
                    content = f.read()
                
                # Ищем строки, связанные с Tote
                lines = content.split('\n')
                new_lines = []
                modified = False
                
                for line in lines:
                    if CONFIG["app_name"] in line.lower():
                        print_info(f"Найдена строка в {config.name}: {line}")
                        if input("Удалить эту строку? (y/N): ").lower() in ["y", "yes", "д", "да"]:
                            modified = True
                            continue
                    new_lines.append(line)
                
                if modified:
                    with open(config, 'w') as f:
                        f.write('\n'.join(new_lines))
                    print_ok(f"Обновлен: {config}")
            except Exception as e:
                print_error(f"Ошибка обработки {config}: {e}")

# ========== Проверка удаления ==========
def verify_uninstall():
    """Проверяет, что Tote удален"""
    print_step("Проверка удаления")
    
    if shutil.which(CONFIG["app_name"]):
        print_warn("Tote все еще найден в системе")
        return False
    else:
        print_ok("Tote успешно удален")
        return True

# ========== Сохранение данных ==========
def backup_data():
    """Создает бэкап данных перед удалением"""
    print_step("Создание бэкапа")
    
    backup_dir = Path.home() / ".tote_backup"
    if backup_dir.exists():
        print_warn("Бэкап уже существует")
        if not input("Перезаписать? (y/N): ").lower() in ["y", "yes", "д", "да"]:
            return True
    
    # Создаем бэкап конфигов
    config_paths = [
        Path(CONFIG["config_dir"]) / "config.json",
        Path.home() / ".config" / "tote" / "config.json"
    ]
    
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    for path in config_paths:
        if path.exists():
            try:
                backup_path = backup_dir / path.name
                shutil.copy2(path, backup_path)
                print_ok(f"Создан бэкап: {backup_path}")
            except Exception as e:
                print_error(f"Ошибка бэкапа {path}: {e}")
    
    return True

# ========== Главная функция ==========
def main():
    print_title()
    
    # Проверяем систему
    check_system()
    check_installation()
    
    # Предупреждение
    print_warn("Это действие полностью удалит Tote из системы!")
    print_warn("Будут удалены все файлы, конфиги и кэш")
    
    if not input("\nУдалить Tote? (y/N): ").lower() in ["y", "yes", "д", "да"]:
        print_info("Удаление отменено")
        sys.exit(0)
    
    # Создаем бэкап
    if not backup_data():
        print_warn("Бэкап не создан")
        if not input("Продолжить без бэкапа? (y/N): ").lower() in ["y", "yes", "д", "да"]:
            sys.exit(0)
    
    # Находим файлы
    files_to_remove = find_tote_files()
    
    # Удаляем файлы
    if not remove_files(files_to_remove):
        print_error("Не удалось удалить все файлы")
        sys.exit(1)
    
    # Удаляем Python пакеты
    remove_python_packages()
    
    # Очищаем PATH
    clean_path()
    
    # Проверяем удаление
    verify_uninstall()
    
    print(f"""
{Colors.GREEN}╔══════════════════════════════════════════════════════════╗
║                                                              ║
║     {Colors.BOLD}🗑️  УДАЛЕНИЕ ЗАВЕРШЕНО{Colors.GREEN} 🗑️                        ║
║                                                              ║
║     {Colors.YELLOW}Бэкап сохранен в:{Colors.GREEN}                               ║
║     {Colors.CYAN}{Path.home() / '.tote_backup'}{Colors.GREEN}                      ║
║                                                              ║
║     {Colors.YELLOW}Для переустановки запустите:{Colors.GREEN}                     ║
║     {Colors.CYAN}python3 install.py{Colors.GREEN}                                ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝{Colors.RESET}
    """)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⏹️ Удаление прервано")
        sys.exit(1)
    except Exception as e:
        print_error(f"Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
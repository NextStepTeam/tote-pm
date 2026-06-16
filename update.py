#!/usr/bin/env python3
"""
Обновление Tote Package Manager
Без git pull - просто пересобирает и устанавливает
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
    "version": "1.0.0",
    "requirements": [
        "requests",
        "sqlalchemy",
        "pyinstaller"
    ],
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
{Colors.CYAN}╔══════════════════════════════════════════════════════════╗
║                                                              ║
║     {Colors.BOLD}TOTE PACKAGE MANAGER - UPDATE{Colors.CYAN}                       ║
║     Version {CONFIG['version']} -> Новейшая                      ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝{Colors.RESET}
    """)

# ========== Проверка системы ==========
def check_system():
    """Проверяет системные требования"""
    if platform.system() != "Linux":
        print_error("Обновление поддерживается только в Linux")
        sys.exit(1)
    print_ok(f"Система: {platform.system()} {platform.release()}")

def check_current_installation():
    """Проверяет, установлен ли Tote"""
    if not shutil.which(CONFIG["app_name"]):
        print_error("Tote не установлен. Запустите install.py сначала")
        sys.exit(1)
    
    print_ok("Tote найден в системе")

def check_sudo():
    """Проверяет права sudo"""
    if os.geteuid() != 0:
        print_warn("Нет прав администратора. Бинарник будет обновлен локально")
        return False
    return True

# ========== Проверка зависимостей ==========
def check_dependencies():
    """Проверяет установленные зависимости"""
    print_step("Проверка зависимостей")
    
    deps = {
        "python3": ["python3", "--version"],
        "pip3": ["pip3", "--version"],
        "pyinstaller": ["pyinstaller", "--version"]
    }
    
    missing = []
    for name, cmd in deps.items():
        if shutil.which(name):
            print_ok(f"{name} найден")
        else:
            print_error(f"{name} не найден")
            missing.append(name)
    
    if missing:
        print_error(f"Отсутствуют: {', '.join(missing)}")
        if "pyinstaller" in missing:
            print_info("Установите pyinstaller: pip3 install pyinstaller")
        sys.exit(1)
    
    return True

# ========== Обновление Python пакетов ==========
def update_python_packages():
    """Обновляет Python зависимости"""
    print_step("Обновление Python пакетов")
    
    for pkg in CONFIG["requirements"]:
        try:
            subprocess.run(
                ["pip3", "install", "--upgrade", pkg],
                capture_output=True,
                text=True,
                check=True
            )
            print_ok(f"{pkg} обновлен")
        except subprocess.CalledProcessError as e:
            print_error(f"Ошибка обновления {pkg}: {e.stderr}")
            return False
    
    return True

# ========== Сборка бинарника ==========
def build_binary():
    """Собирает бинарник через PyInstaller"""
    print_step("Сборка бинарника")
    
    script_dir = Path(__file__).parent.absolute()
    main_py = script_dir / "main.py"
    
    if not main_py.exists():
        print_error(f"Файл {main_py} не найден")
        return False
    
    # Очищаем старые сборки
    for dirname in ["build", "dist"]:
        path = script_dir / dirname
        if path.exists():
            shutil.rmtree(path)
            print_info(f"Очищена папка: {dirname}")
    
    # Удаляем .spec файлы
    for spec in script_dir.glob("*.spec"):
        spec.unlink()
        print_info(f"Удален: {spec.name}")
    
    # Формируем команду для PyInstaller
    cmd = [
        "pyinstaller",
        "--onefile",
        "--name", CONFIG["app_name"],
        "--add-data", f"{script_dir}/utils:utils",
        "--add-data", f"{script_dir}/conf:conf",
        "--clean",
        "--noconfirm",
        str(main_py)
    ]
    
    print_info(f"Команда: {' '.join(cmd)}")
    
    try:
        subprocess.run(
            cmd,
            cwd=script_dir,
            capture_output=True,
            text=True,
            check=True
        )
        print_ok("Бинарник собран")
        return True
    except subprocess.CalledProcessError as e:
        print_error(f"Ошибка сборки: {e.stderr}")
        return False

# ========== Обновление бинарника ==========
def update_binary():
    """Обновляет бинарник в системе"""
    print_step("Обновление бинарника")
    
    script_dir = Path(__file__).parent.absolute()
    binary_path = script_dir / "dist" / CONFIG["app_name"]
    
    if not binary_path.exists():
        print_error("Бинарник не найден после сборки")
        return False
    
    # Определяем куда устанавливать
    has_sudo = check_sudo()
    
    if has_sudo:
        target_dir = Path(CONFIG["binary_dir"])
        # Проверяем, что бинарник действительно там
        if not (target_dir / CONFIG["app_name"]).exists():
            print_warn("Бинарник не найден в системной папке")
            target_dir = Path.home() / ".local" / "bin"
            target_dir.mkdir(parents=True, exist_ok=True)
    else:
        target_dir = Path.home() / ".local" / "bin"
        target_dir.mkdir(parents=True, exist_ok=True)
    
    target_path = target_dir / CONFIG["app_name"]
    
    # Бэкапим старый бинарник
    if target_path.exists():
        backup_path = target_path.with_suffix(".bak")
        shutil.copy2(target_path, backup_path)
        print_info(f"Создан бэкап: {backup_path}")
    
    # Копируем новый бинарник
    try:
        shutil.copy2(binary_path, target_path)
        target_path.chmod(0o755)
        print_ok(f"Бинарник обновлен: {target_path}")
        return True
    except Exception as e:
        print_error(f"Ошибка обновления: {e}")
        # Восстанавливаем бэкап
        if backup_path.exists():
            shutil.copy2(backup_path, target_path)
            print_info("Бэкап восстановлен")
        return False

# ========== Обновление конфига ==========
def update_config():
    """Обновляет конфиг, сохраняя старые настройки"""
    print_step("Обновление конфигурации")
    
    # Ищем существующий конфиг
    config_paths = [
        Path(CONFIG["config_dir"]) / "config.json",
        Path.home() / ".config" / "tote" / "config.json",
        Path.home() / ".tote" / "config.json"
    ]
    
    found_config = None
    for path in config_paths:
        if path.exists():
            found_config = path
            break
    
    if not found_config:
        print_warn("Конфиг не найден. Будет создан новый")
        # Создаем новый конфиг
        config = {
            "db": "sqlite:///packages.db",
            "dirs": {
                "cache": "/var/cache/tote" if check_sudo() else str(Path.home() / ".cache" / "tote"),
                "config": str(found_config.parent) if found_config else "/etc/tote"
            }
        }
        
        if check_sudo():
            config_dir = Path(CONFIG["config_dir"])
        else:
            config_dir = Path.home() / ".config" / "tote"
        
        config_dir.mkdir(parents=True, exist_ok=True)
        config_path = config_dir / "config.json"
        
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            print_ok(f"Создан новый конфиг: {config_path}")
        except Exception as e:
            print_error(f"Ошибка создания конфига: {e}")
    else:
        print_ok(f"Конфиг найден: {found_config}")
        print_info("Настройки сохранены")

# ========== Версия ==========
def get_current_version():
    """Получает текущую версию Tote"""
    try:
        result = subprocess.run(
            [CONFIG["app_name"], "--version"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except:
        pass
    return "неизвестно"

# ========== Проверка обновления ==========
def verify_update():
    """Проверяет успешность обновления"""
    print_step("Проверка обновления")
    
    result = subprocess.run(
        [CONFIG["app_name"], "--help"],
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        print_ok("Обновление успешно!")
        print_info(f"Версия: {get_current_version()}")
        return True
    else:
        print_error("Проверка не прошла")
        return False

# ========== Очистка ==========
def cleanup():
    """Удаляет временные файлы сборки"""
    print_step("Очистка")
    
    script_dir = Path(__file__).parent.absolute()
    
    for dirname in ["build", "dist"]:
        path = script_dir / dirname
        if path.exists():
            shutil.rmtree(path)
            print_ok(f"Удалено: {dirname}")
    
    for spec in script_dir.glob("*.spec"):
        spec.unlink()
        print_ok(f"Удалено: {spec.name}")

# ========== Главная функция ==========
def main():
    print_title()
    
    # Проверяем систему
    check_system()
    check_current_installation()
    
    # Проверяем зависимости
    check_dependencies()
    
    old_version = get_current_version()
    print_info(f"Текущая версия: {old_version}")
    
    # Обновляем зависимости
    if not update_python_packages():
        print_error("Не удалось обновить зависимости")
        if not input("Продолжить? (y/N): ").lower() in ["y", "yes", "д", "да"]:
            sys.exit(1)
    
    # Собираем бинарник
    if not build_binary():
        print_error("Не удалось собрать бинарник")
        sys.exit(1)
    
    # Обновляем бинарник
    if not update_binary():
        print_error("Не удалось обновить бинарник")
        sys.exit(1)
    
    # Обновляем конфиг
    update_config()
    
    # Очищаем временные файлы
    cleanup()
    
    # Проверяем обновление
    verify_update()
    
    print(f"""
{Colors.GREEN}╔══════════════════════════════════════════════════════════╗
║                                                              ║
║     🚀 {Colors.BOLD}ОБНОВЛЕНИЕ ЗАВЕРШЕНО{Colors.GREEN} 🚀                       ║
║                                                              ║
║     {Colors.CYAN}{old_version}{Colors.GREEN} → {Colors.BOLD}{Colors.GREEN}Новейшая{Colors.GREEN}                            ║
║                                                              ║
║     Используйте: {Colors.CYAN}{CONFIG['app_name']} <команда>{Colors.GREEN}                   ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝{Colors.RESET}
    """)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⏹️ Обновление прервано")
        sys.exit(1)
    except Exception as e:
        print_error(f"Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
#!/usr/bin/env python3
"""
Установщик Tote Package Manager
Устанавливает зависимости и собирает бинарник через PyInstaller
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
║     {Colors.BOLD}TOTE PACKAGE MANAGER - INSTALLER{Colors.CYAN}                      ║
║     Version {CONFIG['version']}                                      ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝{Colors.RESET}
    """)

# ========== Проверка системы ==========
def check_platform():
    """Проверяет, что система Linux"""
    if platform.system() != "Linux":
        print_error("Установщик поддерживает только Linux")
        sys.exit(1)
    print_ok(f"Система: {platform.system()} {platform.release()}")

def check_sudo():
    """Проверяет права sudo"""
    if os.geteuid() != 0:
        print_warn("Нет прав администратора. Некоторые операции могут требовать sudo")
        return False
    return True

def check_dependencies():
    """Проверяет установленные зависимости"""
    print_step("Проверка зависимостей системы")
    
    deps = {
        "python3": ["python3", "--version"],
        "pip3": ["pip3", "--version"],
        "git": ["git", "--version"]
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
        print_info("Установите недостающие зависимости:")
        print(f"  sudo apt-get install {' '.join(missing)}")
        sys.exit(1)
    
    return True

# ========== Установка Python пакетов ==========
def install_python_packages():
    """Устанавливает Python зависимости"""
    print_step("Установка Python пакетов")
    
    for pkg in CONFIG["requirements"]:
        try:
            subprocess.run(
                ["pip3", "install", pkg],
                capture_output=True,
                text=True,
                check=True
            )
            print_ok(f"{pkg} установлен")
        except subprocess.CalledProcessError as e:
            print_error(f"Ошибка установки {pkg}: {e.stderr}")
            return False
    
    return True

# ========== Сборка бинарника ==========
def build_binary():
    """Собирает бинарник через PyInstaller"""
    print_step("Сборка бинарника")
    
    # Определяем путь к исходникам
    script_dir = Path(__file__).parent.absolute()
    main_py = script_dir / "main.py"
    
    if not main_py.exists():
        print_error(f"Файл {main_py} не найден")
        return False
    
    # Очищаем старые сборки
    if (script_dir / "build").exists():
        shutil.rmtree(script_dir / "build")
    if (script_dir / "dist").exists():
        shutil.rmtree(script_dir / "dist")
    if (script_dir / f"{CONFIG['app_name']}.spec").exists():
        (script_dir / f"{CONFIG['app_name']}.spec").unlink()
    
    # Формируем команду для PyInstaller
    cmd = [
        "pyinstaller",
        "--onefile",
        "--name", CONFIG["app_name"],
        "--add-data", f"{script_dir}/utils:utils",
        "--clean",
        "--noconfirm",
        str(main_py)
    ]
    
    print_info(f"Команда: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(
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

# ========== Установка бинарника ==========
def install_binary():
    """Устанавливает бинарник в систему"""
    print_step("Установка бинарника")
    
    script_dir = Path(__file__).parent.absolute()
    binary_path = script_dir / "dist" / CONFIG["app_name"]
    
    if not binary_path.exists():
        print_error("Бинарник не найден после сборки")
        return False
    
    # Проверяем права
    if not check_sudo():
        print_warn("Бинарник будет установлен в локальную папку")
        target_dir = Path.home() / ".local" / "bin"
        target_dir.mkdir(parents=True, exist_ok=True)
    else:
        target_dir = Path(CONFIG["binary_dir"])
        if not target_dir.exists():
            target_dir.mkdir(parents=True, exist_ok=True)
    
    target_path = target_dir / CONFIG["app_name"]
    
    # Копируем бинарник
    try:
        shutil.copy2(binary_path, target_path)
        target_path.chmod(0o755)
        print_ok(f"Бинарник установлен в {target_path}")
        return True
    except Exception as e:
        print_error(f"Ошибка установки: {e}")
        return False

# ========== Создание конфига ==========
def create_config():
    """Создает конфигурационный файл"""
    print_step("Создание конфигурации")
    
    config = {
        "db": "sqlite:///packages.db",
        "dirs": {
            "cache": "/var/cache/tote",
            "config": "/etc/tote"
        }
    }
    
    # Определяем место для конфига
    if check_sudo():
        config_dir = Path(CONFIG["config_dir"])
    else:
        config_dir = Path.home() / ".config" / "tote"
    
    config_dir.mkdir(parents=True, exist_ok=True)
    config_path = config_dir / "config.json"
    
    # Не перезаписываем существующий конфиг
    if config_path.exists():
        print_warn(f"Конфиг уже существует: {config_path}")
        if input("Перезаписать? (y/N): ").lower() not in ["y", "yes", "д", "да"]:
            return True
    
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        print_ok(f"Конфиг создан: {config_path}")
        return True
    except Exception as e:
        print_error(f"Ошибка создания конфига: {e}")
        return False

# ========== Проверка установки ==========
def verify_installation():
    """Проверяет успешность установки"""
    print_step("Проверка установки")
    
    # Проверяем, что бинарник доступен
    result = subprocess.run(
        [CONFIG["app_name"], "--help"],
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        print_ok("Установка успешна!")
        print_info(f"Используйте: {CONFIG['app_name']} <команда>")
        return True
    else:
        print_warn("Проверка не прошла, но бинарник установлен")
        return False

# ========== Очистка временных файлов ==========
def cleanup():
    """Удаляет временные файлы сборки"""
    print_step("Очистка")
    
    script_dir = Path(__file__).parent.absolute()
    dirs_to_clean = ["build", "dist", "__pycache__"]
    
    for dirname in dirs_to_clean:
        path = script_dir / dirname
        if path.exists():
            shutil.rmtree(path)
            print_ok(f"Удалено: {dirname}")
    
    # Удаляем .spec файлы
    for spec in script_dir.glob("*.spec"):
        spec.unlink()
        print_ok(f"Удалено: {spec.name}")

# ========== Главная функция ==========
def main():
    print_title()
    
    # Проверяем систему
    check_platform()
    check_dependencies()
    
    # Устанавливаем зависимости
    if not install_python_packages():
        print_error("Не удалось установить зависимости")
        sys.exit(1)
    
    # Собираем бинарник
    if not build_binary():
        print_error("Не удалось собрать бинарник")
        sys.exit(1)
    
    # Устанавливаем бинарник
    if not install_binary():
        print_error("Не удалось установить бинарник")
        sys.exit(1)
    
    # Создаем конфиг
    create_config()
    
    # Очищаем временные файлы
    cleanup()
    
    # Проверяем установку
    verify_installation()
    
    print(f"""
{Colors.GREEN}╔══════════════════════════════════════════════════════════╗
║                                                              ║
║     🎉 {Colors.BOLD}УСТАНОВКА ЗАВЕРШЕНА{Colors.GREEN} 🎉                       ║
║                                                              ║
║     Команды:                                                 ║
║       {Colors.CYAN}{CONFIG['app_name']} repo add <url>{Colors.GREEN}    - Добавить репозиторий ║
║       {Colors.CYAN}{CONFIG['app_name']} install <package>{Colors.GREEN} - Установить пакет    ║
║       {Colors.CYAN}{CONFIG['app_name']} --help{Colors.GREEN}              - Все команды        ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝{Colors.RESET}
    """)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⏹️ Установка прервана")
        sys.exit(1)
    except Exception as e:
        print_error(f"Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
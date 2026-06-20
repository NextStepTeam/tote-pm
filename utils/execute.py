import subprocess
import shlex
from .parser import ToteRecipe
import shutil
from pathlib import Path

def execute_section(recipe: ToteRecipe, section_name: str, variables: dict = None, context: dict = {}):
    """Выполнить все команды из указанной секции"""
    if section_name not in recipe.sections:
        print(f"Секция [{section_name}] не найдена")
        return False
    
    commands = recipe.sections[section_name]
    
    for cmd_line in commands:
        for key, value in context.items():
            cmd_line = cmd_line.replace(f"%{key}%", str(value))
        # разбираем команду
        parts = shlex.split(cmd_line)
        if not parts:
            continue
        
        cmd = parts[0].upper()
        args = parts[1:] if len(parts) > 1 else []
        
        # подстановка переменных {version}
        args = [arg.format(**variables) if variables else arg for arg in args]
        
        if cmd == "RUN":
            # выполнить произвольную команду
            result = subprocess.run(args, shell=False)
            if result.returncode != 0:
                print(f"Ошибка при выполнении: {cmd_line}")
                return False
        
        elif cmd == "GIT":
            if len(args) < 1:
                continue
            git_cmd = args[0].upper()
            git_args = args[1:] if len(args) > 1 else []
            
            if git_cmd == "CLONE":
                subprocess.run(["git", "clone"] + git_args)
            elif git_cmd == "CHECKOUT":
                subprocess.run(["git", "checkout"] + git_args)
            elif git_cmd == "PULL":
                subprocess.run(["git", "pull"])
        
        elif cmd == "COPY":
            # COPY source dest
            if len(args) >= 2:
                src, dst = args[0], args[1]
                shutil.copy(src, dst)
        
        elif cmd == "RM":
            # RM path
            for path in args:
                if Path(path).is_dir():
                    shutil.rmtree(path)
                else:
                    Path(path).unlink()
        
        elif cmd == "DOCKER":
            docker_cmd = args[0].upper() if args else ""
            docker_args = args[1:] if len(args) > 1 else []
            
            if docker_cmd == "COMPOSE":
                subprocess.run(["docker-compose"] + docker_args)
            else:
                subprocess.run(["docker", docker_cmd.lower()] + docker_args)
        
        elif cmd == "PIP":
            subprocess.run(["pip"] + args)
    
    return True
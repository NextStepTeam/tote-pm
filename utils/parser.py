import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional

@dataclass
class ToteRecipe:
    name: str = ""
    description: str = "",
    vs: str = ""
    use: str = ""
    deps: List[str] = field(default_factory=list)
    sections: Dict[str, List[str]] = field(default_factory=dict)  # секция -> список команд

def parse_totefile(content: str) -> ToteRecipe:
    recipe = ToteRecipe()
    lines = content.split('\n')
    
    i = 0
    current_section = None
    current_commands = []
    
    while i < len(lines):
        line = lines[i].strip()
        
        # пропуск пустых строк и комментариев
        if not line or line.startswith('#'):
            i += 1
            continue
        
        # проверка на открытие секции [SECTION] или [SECTION.SUBSECTION]
        if line.startswith('[') and line.endswith(']'):
            # сохраняем предыдущую секцию
            if current_section and current_commands:
                recipe.sections[current_section] = current_commands
            
            # начинаем новую секцию
            current_section = line[1:-1].lower()
            current_commands = []
            i += 1
            continue
        
        # проверка на закрытие секции [/SECTION]
        if line.startswith('[/') and line.endswith(']'):
            if current_section and current_commands:
                recipe.sections[current_section] = current_commands
            current_section = None
            current_commands = []
            i += 1
            continue
        
        # парсим команды верхнего уровня (без секции)
        if current_section is None:
            parts = line.split(maxsplit=1)
            if len(parts) < 2:
                i += 1
                continue
            
            cmd, args = parts[0].upper(), parts[1]
            
            if cmd == "USE":
                recipe.use = args
            elif cmd == "VS":
                recipe.vs = args
            elif cmd == "NAME":
                recipe.name = args
            elif cmd == "DESCRIPTION":
                recipe.description = args.strip('"')
            elif cmd == "DEPS":
                for dep in args.split(','):
                    recipe.deps.append(dep.strip())
        
        # внутри секции — накапливаем команды
        else:
            # поддерживаем многострочные команды (если строка заканчивается на \)
            if line.endswith('\\'):
                line = line[:-1] + ' ' + lines[i + 1].strip()
                i += 1
            current_commands.append(line)
        
        i += 1
    
    # сохраняем последнюю секцию
    if current_section and current_commands:
        recipe.sections[current_section] = current_commands
    
    return recipe
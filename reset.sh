#!/bin/bash

# Repository Reset Script
# Reinicia el repositorio borrando todo excepto .git/ y docs/
# Recrea estructura básica de proyecto
# Uso: ./repo_reset.sh

set -e

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m'

# Funciones de mensajes
log_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
log_success() { echo -e "${GREEN}✅ $1${NC}"; }
log_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
log_error() { echo -e "${RED}❌ $1${NC}"; }
log_header() { echo -e "\n${CYAN}${1}${NC}"; }

# Verificar que estamos en un repositorio Git
check_git_repo() {
    if [[ ! -d .git ]]; then
        log_error "No estás en un repositorio Git"
        echo "Este script debe ejecutarse desde la raíz del repositorio"
        exit 1
    fi
    
    log_success "Repositorio Git detectado"
}

# Mostrar información del repositorio
show_repo_info() {
    log_header "=== INFORMACIÓN DEL REPOSITORIO ==="
    
    REPO_NAME=$(basename "$(git rev-parse --show-toplevel)")
    CURRENT_BRANCH=$(git branch --show-current)
    REMOTE_URL=$(git remote get-url origin 2>/dev/null || echo "Sin remoto configurado")
    
    echo -e "📁 Repositorio: ${WHITE}$REPO_NAME${NC}"
    echo -e "🌿 Rama actual: ${WHITE}$CURRENT_BRANCH${NC}"
    echo -e "🔗 Remoto: ${WHITE}$REMOTE_URL${NC}"
    echo -e "📍 Ruta: ${WHITE}$(pwd)${NC}"
}

# Confirmar operación
confirm_operation() {
    log_header "=== CONFIRMACIÓN DE OPERACIÓN ==="
    
    log_warning "ATENCIÓN: Esta operación:"
    echo "  • Borrará TODOS los archivos excepto .git/ y docs/"
    echo "  • Mantendrá el historial de Git intacto"  
    echo "  • Creará estructura básica de proyecto nueva"
    echo "  • NO se puede deshacer fácilmente"
    echo ""
    
    # Mostrar qué se va a mantener
    echo -e "${GREEN}SE MANTENDRÁN:${NC}"
    [[ -d .git ]] && echo "  ✅ .git/ (historial de Git)"
    [[ -d docs ]] && echo "  ✅ docs/ (documentación)"
    [[ -f .gitignore ]] && echo "  ✅ .gitignore (si existe)"
    echo ""
    
    # Mostrar qué se va a borrar
    echo -e "${RED}SE BORRARÁN:${NC}"
    find . -maxdepth 1 -type f -not -name ".gitignore" -not -name "repo_reset.sh" | head -10 | while read file; do
        echo "  ❌ $file"
    done
    
    find . -maxdepth 1 -type d -not -name "." -not -name ".git" -not -name "docs" | head -10 | while read dir; do
        echo "  ❌ $dir/"
    done
    
    local file_count=$(find . -maxdepth 1 -type f -not -name ".gitignore" -not -name "repo_reset.sh" | wc -l)
    local dir_count=$(find . -maxdepth 1 -type d -not -name "." -not -name ".git" -not -name "docs" | wc -l)
    
    if [[ $file_count -gt 10 || $dir_count -gt 10 ]]; then
        echo "  ... y $(( file_count + dir_count - 20 )) elementos más"
    fi
    
    echo ""
    echo -e "${YELLOW}Para confirmar, escribe: ${WHITE}RESET${NC}"
    read -p "Confirmación: " confirmation
    
    if [[ "$confirmation" != "RESET" ]]; then
        log_info "Operación cancelada"
        exit 0
    fi
}

# Crear backup de Git status
create_git_backup() {
    log_header "=== CREANDO BACKUP DE ESTADO GIT ==="
    
    # Crear carpeta temporal para backup
    mkdir -p .git_backup_temp
    
    # Guardar información del repositorio
    cat > .git_backup_temp/repo_info.txt << EOF
# Repository Reset Backup - $(date)
# Repository: $(basename "$(pwd)")
# Branch: $(git branch --show-current)
# Remote: $(git remote get-url origin 2>/dev/null || echo "No remote")

# Git Status Before Reset:
$(git status)

# Recent Commits:
$(git log --oneline -10)

# Branches:
$(git branch -a)

# Stashes:
$(git stash list)
EOF
    
    # Backup de archivos importantes si existen
    [[ -f README.md ]] && cp README.md .git_backup_temp/
    [[ -f requirements.txt ]] && cp requirements.txt .git_backup_temp/
    [[ -f package.json ]] && cp package.json .git_backup_temp/
    [[ -f pyproject.toml ]] && cp pyproject.toml .git_backup_temp/
    [[ -f setup.py ]] && cp setup.py .git_backup_temp/
    
    log_success "Backup creado en .git_backup_temp/"
}

# Verificar cambios sin commitear
check_uncommitted_changes() {
    log_header "=== VERIFICANDO CAMBIOS SIN COMMITEAR ==="
    
    if ! git diff-index --quiet HEAD --; then
        log_warning "Tienes cambios sin commitear"
        echo ""
        git status --short
        echo ""
        
        read -p "¿Hacer commit automático antes del reset? (y/n): " auto_commit
        if [[ $auto_commit =~ ^[Yy]$ ]]; then
            git add .
            git commit -m "Auto-commit antes de repository reset - $(date '+%Y-%m-%d %H:%M')"
            log_success "Commit automático realizado"
        else
            log_warning "Cambios sin commitear se perderán"
            read -p "¿Continuar de todos modos? (y/n): " continue_anyway
            if [[ ! $continue_anyway =~ ^[Yy]$ ]]; then
                log_info "Operación cancelada"
                exit 0
            fi
        fi
    else
        log_success "No hay cambios sin commitear"
    fi
}

# Borrar archivos y directorios
# Borrar archivos y directorios - VERSIÓN ULTRA ROBUSTA
cleanup_repository() {
    log_header "=== LIMPIANDO REPOSITORIO ==="
    
    # Deshabilitar set -e temporalmente para manejar errores manualmente
    set +e
    
    local deleted_files=0
    local deleted_dirs=0
    local errors=0
    local total_items=0
    
    # Crear arrays para almacenar los elementos a borrar
    local files_to_delete=()
    local dirs_to_delete=()
    
    log_info "Identificando archivos a borrar..."
    
    # Recopilar archivos a borrar (excepto los protegidos)
    while IFS= read -r -d '' file; do
        if [[ -f "$file" ]]; then
            files_to_delete+=("$file")
        fi
    done < <(find . -maxdepth 1 -type f \
        -not -name ".gitignore" \
        -not -name "repo_reset.sh" \
        -not -name "reset.sh" \
        -print0 2>/dev/null)
    
    log_info "Identificando directorios a borrar..."
    
    # Recopilar directorios a borrar (excepto los protegidos)  
    while IFS= read -r -d '' dir; do
        if [[ -d "$dir" ]]; then
            dirs_to_delete+=("$dir")
        fi
    done < <(find . -maxdepth 1 -type d \
        -not -name "." \
        -not -name ".git" \
        -not -name "docs" \
        -not -name ".git_backup_temp" \
        -print0 2>/dev/null)
    
    total_items=$((${#files_to_delete[@]} + ${#dirs_to_delete[@]}))
    
    # Mostrar qué se va a borrar
    if [[ ${#files_to_delete[@]} -gt 0 ]]; then
        log_info "Archivos a borrar: ${#files_to_delete[@]}"
        for file in "${files_to_delete[@]}"; do
            echo "  📄 $file"
        done
    else
        log_info "No hay archivos que borrar"
    fi
    
    echo ""
    
    if [[ ${#dirs_to_delete[@]} -gt 0 ]]; then
        log_info "Directorios a borrar: ${#dirs_to_delete[@]}"
        for dir in "${dirs_to_delete[@]}"; do
            echo "  📁 $dir/"
        done
    else
        log_info "No hay directorios que borrar"
    fi
    
    echo ""
    
    if [[ $total_items -eq 0 ]]; then
        log_success "El repositorio ya está limpio"
        set -e  # Rehabilitar set -e
        return 0
    fi
    
    log_warning "Total de elementos a borrar: $total_items"
    echo ""
    read -p "¿Proceder con el borrado? (y/n): " confirm_delete
    if [[ ! $confirm_delete =~ ^[Yy]$ ]]; then
        log_info "Borrado cancelado por el usuario"
        set -e  # Rehabilitar set -e
        exit 0
    fi
    
    echo ""
    log_info "Iniciando proceso de borrado..."
    
    # Borrar archivos uno por uno
    if [[ ${#files_to_delete[@]} -gt 0 ]]; then
        log_info "Borrando archivos..."
        for file in "${files_to_delete[@]}"; do
            echo -n "🗑️  Borrando archivo: $file ... "
            if [[ -f "$file" ]]; then
                if rm -f "$file" 2>/dev/null; then
                    echo "✅"
                    ((deleted_files++))
                else
                    echo "❌ ERROR"
                    log_error "No se pudo borrar: $file"
                    ((errors++))
                fi
            else
                echo "⏭️  Ya no existe"
            fi
            
            # Pequeña pausa para evitar problemas de I/O
            sleep 0.1
        done
    fi
    
    echo ""
    
    # Borrar directorios uno por uno
    if [[ ${#dirs_to_delete[@]} -gt 0 ]]; then
        log_info "Borrando directorios..."
        for dir in "${dirs_to_delete[@]}"; do
            echo -n "🗑️  Borrando directorio: $dir ... "
            if [[ -d "$dir" ]]; then
                if rm -rf "$dir" 2>/dev/null; then
                    echo "✅"
                    ((deleted_dirs++))
                else
                    echo "❌ ERROR"
                    log_error "No se pudo borrar: $dir"
                    ((errors++))
                fi
            else
                echo "⏭️  Ya no existe"
            fi
            
            # Pequeña pausa para evitar problemas de I/O
            sleep 0.1
        done
    fi
    
    echo ""
    
    # Resumen de la limpieza
    log_success "Proceso de limpieza completado:"
    echo "  ✅ Archivos borrados: $deleted_files de ${#files_to_delete[@]}"
    echo "  ✅ Directorios borrados: $deleted_dirs de ${#dirs_to_delete[@]}"
    echo "  📊 Total procesado: $((deleted_files + deleted_dirs)) de $total_items elementos"
    
    if [[ $errors -gt 0 ]]; then
        log_warning "❌ Errores encontrados: $errors"
        echo ""
        read -p "¿Continuar a pesar de los errores? (y/n): " continue_with_errors
        if [[ ! $continue_with_errors =~ ^[Yy]$ ]]; then
            log_error "Script detenido debido a errores"
            set -e  # Rehabilitar set -e
            exit 1
        fi
    fi
    
    echo ""
    log_info "Verificando limpieza..."
    
    # Verificar que el directorio esté realmente limpio
    local remaining_items=()
    while IFS= read -r -d '' item; do
        remaining_items+=("$item")
    done < <(find . -maxdepth 1 \( -type f -o -type d \) \
        -not -name "." \
        -not -name ".git" \
        -not -name "docs" \
        -not -name ".gitignore" \
        -not -name "repo_reset.sh" \
        -not -name "reset.sh" \
        -not -name ".git_backup_temp" \
        -print0 2>/dev/null)
    
    if [[ ${#remaining_items[@]} -gt 0 ]]; then
        log_warning "Aún quedan ${#remaining_items[@]} elementos sin borrar:"
        for item in "${remaining_items[@]}"; do
            if [[ -f "$item" ]]; then
                echo "  📄 $item (archivo)"
            elif [[ -d "$item" ]]; then
                echo "  📁 $item (directorio)"
            fi
        done
        echo ""
        read -p "¿Intentar borrar elementos restantes manualmente? (y/n): " manual_cleanup
        if [[ $manual_cleanup =~ ^[Yy]$ ]]; then
            for item in "${remaining_items[@]}"; do
                echo -n "🗑️  Borrando: $item ... "
                if [[ -f "$item" ]]; then
                    rm -f "$item" 2>/dev/null && echo "✅" || echo "❌"
                elif [[ -d "$item" ]]; then
                    rm -rf "$item" 2>/dev/null && echo "✅" || echo "❌"
                fi
            done
        fi
    else
        log_success "✨ Directorio completamente limpiado"
    fi
    
    # Rehabilitar set -e
    set -e
    
    return 0
}

# También agregar esta función de utilidad para verificar el estado
verify_cleanup() {
    log_info "Verificación final del repositorio:"
    
    # Listar contenido actual
    echo ""
    echo "📂 Contenido actual del repositorio:"
    ls -la | grep -v "^total" | while read line; do
        if [[ $line =~ ^d.* ]]; then
            echo "  📁 $(echo "$line" | awk '{print $NF}')"
        else
            echo "  📄 $(echo "$line" | awk '{print $NF}')"
        fi
    done
    
    echo ""
    
    # Verificar estructura esperada
    if [[ -d .git ]]; then
        echo "✅ .git/ - Directorio Git presente"
    else
        echo "❌ .git/ - FALTA directorio Git"
    fi
    
    if [[ -d docs ]]; then
        echo "✅ docs/ - Documentación presente"
    else
        echo "ℹ️  docs/ - No existe (será creado)"
    fi
    
    if [[ -f .gitignore ]]; then
        echo "✅ .gitignore - Presente"
    else
        echo "ℹ️  .gitignore - No existe (será creado)"
    fi
}
# Crear estructura básica de proyecto
create_project_structure() {
    log_header "=== CREANDO ESTRUCTURA DE PROYECTO ==="
    
    # Directorios básicos
    local directories=(
        "src"
        "tests" 
        "config"
        "scripts"
        "data"
        "assets"
        "logs"
    )
    
    for dir in "${directories[@]}"; do
        mkdir -p "$dir"
        echo "# $dir directory" > "$dir/.gitkeep"
        log_success "Creado: $dir/"
    done
    
    # Subdirectorios específicos
    mkdir -p "src/utils"
    mkdir -p "src/models"
    mkdir -p "src/services"
    mkdir -p "tests/unit"
    mkdir -p "tests/integration"
    mkdir -p "config/environments"
    mkdir -p "data/raw"
    mkdir -p "data/processed"
    mkdir -p "assets/images"
    mkdir -p "assets/css"
    mkdir -p "assets/js"
    
    log_success "Estructura de directorios creada"
}

# Crear archivos base
create_base_files() {
    log_header "=== CREANDO ARCHIVOS BASE ==="
    
    # README.md
    cat > README.md << 'EOF'
# Project Name

## Descripción
Describe tu proyecto aquí.

## Instalación
```bash
# Instrucciones de instalación
```

## Uso
```bash
# Ejemplos de uso
```

## Estructura del Proyecto
```
├── src/           # Código fuente
├── tests/         # Tests
├── docs/          # Documentación
├── config/        # Configuraciones
├── scripts/       # Scripts utilitarios
├── data/          # Datos
├── assets/        # Recursos estáticos
└── logs/          # Logs de aplicación
```

## Contribuir
Instrucciones para contribuir al proyecto.

## Licencia
Especifica la licencia del proyecto.
EOF
    log_success "README.md creado"
    
    # requirements.txt (Python)
    cat > requirements.txt << 'EOF'
# Dependencies
# Add your project dependencies here
# Example:
# requests>=2.25.1
# pytest>=6.2.4
EOF
    log_success "requirements.txt creado"
    
    # .gitignore mejorado (si no existe)
    if [[ ! -f .gitignore ]]; then
        cat > .gitignore << 'EOF'
# Byte-compiled / optimized / DLL files
__pycache__/
*.py[cod]
*$py.class

# C extensions
*.so

# Distribution / packaging
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST

# PyInstaller
*.manifest
*.spec

# Installer logs
pip-log.txt
pip-delete-this-directory.txt

# Unit test / coverage reports
htmlcov/
.tox/
.nox/
.coverage
.coverage.*
.cache
nosetests.xml
coverage.xml
*.cover
.hypothesis/
.pytest_cache/

# Translations
*.mo
*.pot

# Django stuff:
*.log
local_settings.py
db.sqlite3

# Flask stuff:
instance/
.webassets-cache

# Scrapy stuff:
.scrapy

# Sphinx documentation
docs/_build/

# PyBuilder
target/

# Jupyter Notebook
.ipynb_checkpoints

# IPython
profile_default/
ipython_config.py

# pyenv
.python-version

# celery beat schedule file
celerybeat-schedule

# SageMath parsed files
*.sage.py

# Environments
.env
.venv
env/
venv/
ENV/
env.bak/
venv.bak/

# Spyder project settings
.spyderproject
.spyproject

# Rope project settings
.ropeproject

# mkdocs documentation
/site

# mypy
.mypy_cache/
.dmypy.json
dmypy.json

# Pyre type checker
.pyre/

# Node.js
node_modules/
npm-debug.log*
yarn-debug.log*
yarn-error.log*

# IDEs
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db

# Logs
logs/
*.log

# Temporary files
*.tmp
*.temp

# Project specific
data/raw/
data/processed/
.git_backup_temp/
EOF
        log_success ".gitignore creado"
    else
        log_info ".gitignore ya existe (mantenido)"
    fi
    
    # Archivo de configuración inicial
    cat > config/config.py << 'EOF'
"""
Configuration file for the project
"""

import os
from pathlib import Path

# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent

# Environment
ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')

# Logging configuration
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FILE = PROJECT_ROOT / 'logs' / 'app.log'

# Database configuration (example)
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///data/app.db')

# API configuration (example)
API_HOST = os.getenv('API_HOST', 'localhost')
API_PORT = int(os.getenv('API_PORT', '8000'))

class Config:
    """Base configuration class"""
    DEBUG = False
    TESTING = False

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False

class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    DEBUG = True

# Configuration mapping
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
EOF
    log_success "config/config.py creado"
    
    # Archivo principal de ejemplo
    cat > src/main.py << 'EOF'
"""
Main application file
"""

import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.config import config, ENVIRONMENT

def main():
    """Main application entry point"""
    print(f"🚀 Application starting in {ENVIRONMENT} mode")
    
    # Your application logic here
    print("Hello, World!")
    print(f"Project root: {project_root}")
    
    return 0

if __name__ == "__main__":
    exit(main())
EOF
    log_success "src/main.py creado"
    
    # Test de ejemplo
    cat > tests/test_main.py << 'EOF'
"""
Tests for main application
"""

import pytest
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.main import main

def test_main_function():
    """Test that main function runs without error"""
    result = main()
    assert result == 0

def test_project_structure():
    """Test that project structure exists"""
    assert project_root.exists()
    assert (project_root / "src").exists()
    assert (project_root / "tests").exists()
    assert (project_root / "config").exists()

class TestProjectSetup:
    """Test class for project setup validation"""
    
    def test_config_file_exists(self):
        """Test that configuration file exists"""
        config_file = project_root / "config" / "config.py"
        assert config_file.exists()
    
    def test_main_file_exists(self):
        """Test that main application file exists"""
        main_file = project_root / "src" / "main.py"
        assert main_file.exists()
    
    def test_readme_exists(self):
        """Test that README file exists"""
        readme_file = project_root / "README.md"
        assert readme_file.exists()
EOF
    log_success "tests/test_main.py creado"
    
    # Script de desarrollo
    cat > scripts/dev.sh << 'EOF'
#!/bin/bash
# Development script

echo "🚀 Starting development environment..."

# Activate virtual environment if exists
if [[ -d venv ]]; then
    source venv/bin/activate
    echo "✅ Virtual environment activated"
fi

# Install dependencies
if [[ -f requirements.txt ]]; then
    pip install -r requirements.txt
    echo "✅ Dependencies installed"
fi

# Run application in development mode
export ENVIRONMENT=development
python src/main.py
EOF
    chmod +x scripts/dev.sh
    log_success "scripts/dev.sh creado (ejecutable)"
    
    # Script de tests
    cat > scripts/test.sh << 'EOF'
#!/bin/bash
# Test script

echo "🧪 Running tests..."

# Activate virtual environment if exists
if [[ -d venv ]]; then
    source venv/bin/activate
fi

# Run tests with pytest
if command -v pytest >/dev/null 2>&1; then
    pytest tests/ -v --tb=short
else
    python -m pytest tests/ -v --tb=short
fi
EOF
    chmod +x scripts/test.sh
    log_success "scripts/test.sh creado (ejecutable)"
}

# Restaurar backup de información
restore_git_info() {
    log_header "=== RESTAURANDO INFORMACIÓN DE GIT ==="
    
    if [[ -d .git_backup_temp ]]; then
        # Mover información del backup al docs si existe
        if [[ -d docs ]]; then
            mv .git_backup_temp/repo_info.txt docs/repo_reset_backup.txt 2>/dev/null || true
            log_success "Información de backup movida a docs/"
        fi
        
        # Limpiar directorio temporal
        rm -rf .git_backup_temp
        log_success "Directorio temporal limpiado"
    fi
}

# Hacer commit inicial del reset
initial_commit() {
    log_header "=== COMMIT INICIAL ==="
    
    read -p "¿Hacer commit inicial con la nueva estructura? (y/n): " make_commit
    if [[ $make_commit =~ ^[Yy]$ ]]; then
        git add .
        git commit -m "🔄 Repository reset - Nueva estructura de proyecto

- Estructura básica de directorios creada
- Archivos base configurados  
- Scripts de desarrollo incluidos
- Tests de ejemplo agregados
- Configuración inicial establecida

Estructura:
├── src/           # Código fuente
├── tests/         # Tests unitarios e integración  
├── docs/          # Documentación (mantenida)
├── config/        # Configuraciones
├── scripts/       # Scripts utilitarios
├── data/          # Datos del proyecto
├── assets/        # Recursos estáticos
└── logs/          # Logs de aplicación

Reset realizado el $(date '+%Y-%m-%d %H:%M:%S')"
        
        log_success "Commit inicial realizado"
        
        # Push opcional
        if git remote get-url origin >/dev/null 2>&1; then
            read -p "¿Hacer push al remoto? (y/n): " make_push
            if [[ $make_push =~ ^[Yy]$ ]]; then
                git push origin $(git branch --show-current)
                log_success "Push realizado"
            fi
        fi
    else
        log_info "Commit manual requerido"
        echo "Para commitear los cambios:"
        echo "  git add ."
        echo "  git commit -m \"Repository reset - Nueva estructura\""
    fi
}

# Mostrar resumen final
show_final_summary() {
    log_header "=== RESUMEN FINAL ==="
    
    echo -e "${GREEN}🎉 Repository Reset Completado${NC}"
    echo ""
    echo -e "${WHITE}Estructura creada:${NC}"
    echo "  📁 src/           - Código fuente"
    echo "  🧪 tests/         - Tests"
    echo "  📚 docs/          - Documentación (mantenida)"
    echo "  ⚙️  config/        - Configuraciones"
    echo "  📜 scripts/       - Scripts utilitarios"
    echo "  📊 data/          - Datos del proyecto"
    echo "  🎨 assets/        - Recursos estáticos"
    echo "  📝 logs/          - Logs de aplicación"
    echo ""
    echo -e "${WHITE}Archivos principales:${NC}"
    echo "  📄 README.md      - Documentación del proyecto"
    echo "  📦 requirements.txt - Dependencias Python"
    echo "  🚫 .gitignore     - Archivos ignorados"
    echo "  🐍 src/main.py    - Aplicación principal"
    echo "  🧪 tests/test_main.py - Tests de ejemplo"
    echo ""
    echo -e "${WHITE}Scripts disponibles:${NC}"
    echo "  🚀 scripts/dev.sh  - Ejecutar en modo desarrollo"
    echo "  🧪 scripts/test.sh - Ejecutar tests"
    echo ""
    echo -e "${WHITE}Próximos pasos:${NC}"
    echo "  1. Revisa la estructura creada"
    echo "  2. Actualiza README.md con información de tu proyecto"
    echo "  3. Instala dependencias: pip install -r requirements.txt"
    echo "  4. Ejecuta: ./scripts/dev.sh"
    echo "  5. Ejecuta tests: ./scripts/test.sh"
    echo ""
    echo -e "${CYAN}Estado del repositorio Git:${NC}"
    git status --short
    echo ""
    log_success "¡Listo para empezar tu proyecto desde cero!"
}

# Función principal
main() {
    log_header "🔄 REPOSITORY RESET SCRIPT"
    echo "Reinicia el repositorio manteniendo .git/ y docs/"
    echo ""
    
    # Verificaciones
    check_git_repo
    show_repo_info
    
    # Confirmación
    confirm_operation
    
    # Proceso de reset
    create_git_backup
    check_uncommitted_changes
    cleanup_repository
    create_project_structure
    create_base_files
    restore_git_info
    initial_commit
    
    # Resumen
    show_final_summary
}

# Verificar que no se ejecute como root
if [[ $EUID -eq 0 ]]; then
    log_error "No ejecutes este script como root"
    exit 1
fi

# Ejecutar función principal
main "$@"

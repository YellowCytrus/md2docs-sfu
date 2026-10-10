#!/usr/bin/env bash
#
# Установщик sfu-toolkit (Linux / macOS).
#
# Что делает:
#   1. проверяет зависимости (python3, git, libreoffice, poppler) и НЕ трогает
#      то, что уже установлено;
#   2. для отсутствующих пакетов спрашивает разрешение и ставит через штатный
#      менеджер пакетов (apt/dnf/pacman/zypper/brew);
#   3. создаёт виртуальное окружение и ставит конвертер (pip install -e .);
#   4. кладёт команду obsidian2sfu в PATH и создаёт конфиг.
#
# Запуск (из корня репозитория):
#     ./install.sh
#
# Автономно (без репозитория, если положить рядом src/) — склонирует его сам.
#
# Переменные окружения:
#     SFU_PROJECT_DIR   куда клонировать/где проект (по умолчанию — папка скрипта)
#     SFU_REPO_URL      git-URL (по умолчанию репозиторий проекта)
#     SFU_ASSUME_YES=1  отвечать «да» на все вопросы (неинтерактивно)
#     SFU_VAULT         путь к хранилищу Obsidian
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_URL="${SFU_REPO_URL:-https://github.com/bounchich1/sfu_converter.git}"
VAULT_DIR="${SFU_VAULT:-$HOME/obsidian_backup}"
ASSUME_YES="${SFU_ASSUME_YES:-0}"
BIN_DIR="$HOME/.local/bin"
CONFIG_DIR="$HOME/.config/sfu"

say()  { printf '\033[1m==> %s\033[0m\n' "$1"; }
ok()   { printf '  \033[32m✓\033[0m %s\n' "$1"; }
warn() { printf '  \033[33m!\033[0m %s\n' "$1"; }

confirm() {
    if [ "$ASSUME_YES" = "1" ]; then return 0; fi
    if [ ! -t 0 ]; then
        warn "нет терминала для вопроса — пропускаю (задайте SFU_ASSUME_YES=1)"
        return 1
    fi
    local answer
    read -r -p "  $1 [y/N] " answer
    case "$answer" in [yY]*) return 0 ;; *) return 1 ;; esac
}

detect_pm() {
    for pm in apt-get dnf pacman zypper brew; do
        command -v "$pm" >/dev/null 2>&1 && { echo "$pm"; return 0; }
    done
    return 1
}

pkg_names() {
    # $1 = логическое имя; печатает пакеты под текущий менеджер
    case "$(detect_pm 2>/dev/null)" in
        apt-get) case "$1" in python) echo "python3 python3-venv python3-pip";; git) echo "git";; libreoffice) echo "libreoffice";; poppler) echo "poppler-utils";; esac ;;
        dnf)     case "$1" in python) echo "python3 python3-pip";;          git) echo "git";; libreoffice) echo "libreoffice";; poppler) echo "poppler-utils";; esac ;;
        pacman)  case "$1" in python) echo "python python-pip python-virtualenv";; git) echo "git";; libreoffice) echo "libreoffice-fresh";; poppler) echo "poppler";; esac ;;
        zypper)  case "$1" in python) echo "python3 python3-pip";;          git) echo "git";; libreoffice) echo "libreoffice";; poppler) echo "poppler-tools";; esac ;;
        brew)    case "$1" in python) echo "python";;                       git) echo "git";; libreoffice) echo "--cask libreoffice";; poppler) echo "poppler";; esac ;;
        *)       echo "" ;;
    esac
}

install_pkg() {
    local logical="$1" names pm
    names="$(pkg_names "$logical")"
    if [ -z "$names" ]; then
        warn "менеджер пакетов не найден — установите вручную: $logical"
        return 1
    fi
    pm="$(detect_pm)"
    case "$pm" in
        apt-get) sudo apt-get update && sudo apt-get install -y $names ;;
        dnf)     sudo dnf install -y $names ;;
        pacman)  sudo pacman -S --noconfirm $names ;;
        zypper)  sudo zypper install -y $names ;;
        brew)    brew install $names ;;
    esac
}

# --- зависимости ---------------------------------------------------------
ensure_required_cmd() {  # cmd logical "описание"
    local cmd="$1" logical="$2" desc="$3"
    if command -v "$cmd" >/dev/null 2>&1; then
        ok "$cmd — уже установлен"
        return 0
    fi
    warn "$cmd не найден ($desc)"
    if confirm "Установить «$logical»?"; then
        install_pkg "$logical" && ok "$logical установлен"
    else
        warn "пропускаю установку $cmd"
        return 1
    fi
}

ensure_optional_cmd() {  # cmd logical "описание"
    local cmd="$1" logical="$2" desc="$3"
    if command -v "$cmd" >/dev/null 2>&1; then
        ok "$cmd — уже установлен"
        return 0
    fi
    warn "$cmd не найден ($desc) — необязательно"
    if confirm "Установить «$logical» (необязательно)?"; then
        install_pkg "$logical" && ok "$logical установлен"
    else
        warn "без $cmd: PDF-превью и номера страниц в содержании будут недоступны"
    fi
}

say "1/5 Проверка зависимостей"

# Python 3.10+
PY=""
for cand in python3 python; do
    if command -v "$cand" >/dev/null 2>&1; then
        if "$cand" -c 'import sys; raise SystemExit(0 if sys.version_info[:2] >= (3,10) else 1)' 2>/dev/null; then
            PY="$cand"; ok "$cand $("$cand" --version 2>&1 | awk '{print $2}')"; break
        fi
    fi
done
if [ -z "$PY" ]; then
    warn "Python 3.10+ не найден"
    if confirm "Установить Python 3.10+?"; then
        install_pkg python
        for cand in python3 python; do command -v "$cand" >/dev/null 2>&1 && PY="$cand" && break; done
    fi
fi
[ -n "$PY" ] || { echo "Без Python 3.10+ продолжить нельзя."; exit 1; }

# Необязательные, но полезные
ensure_optional_cmd libreoffice libreoffice "PDF-превью документа"
ensure_optional_cmd pdftotext poppler "номера страниц в содержании"

# --- проект --------------------------------------------------------------
say "2/5 Проект"
if [ -f "$SCRIPT_DIR/pyproject.toml" ] && [ -d "$SCRIPT_DIR/src/sfu_converter" ]; then
    PROJECT_DIR="$SCRIPT_DIR"
    ok "использую текущий репозиторий: $PROJECT_DIR"
else
    PROJECT_DIR="${SFU_PROJECT_DIR:-$HOME/Programs/tupoi_word}"
    if ! ensure_required_cmd git git "нужен для клонирования репозитория"; then
        echo "Без git продолжить нельзя."; exit 1
    fi
    if [ -d "$PROJECT_DIR/.git" ]; then
        git -C "$PROJECT_DIR" pull --ff-only || true
        ok "репозиторий обновлён: $PROJECT_DIR"
    else
        mkdir -p "$(dirname "$PROJECT_DIR")"
        git clone "$REPO_URL" "$PROJECT_DIR"
        ok "склонировано в $PROJECT_DIR"
    fi
fi

# --- venv и пакет --------------------------------------------------------
say "3/5 Виртуальное окружение"
if [ ! -x "$PROJECT_DIR/.venv/bin/python" ]; then
    if ! "$PY" -m venv "$PROJECT_DIR/.venv" 2>/dev/null; then
        warn "не удалось создать venv (возможно, нужен пакет python3-venv)"
        if confirm "Установить компонент venv?"; then
            install_pkg python || true
            "$PY" -m venv "$PROJECT_DIR/.venv"
        else
            echo "Без venv продолжить нельзя."; exit 1
        fi
    fi
fi
VENV_PY="$PROJECT_DIR/.venv/bin/python"
"$VENV_PY" -m pip install --quiet --upgrade pip wheel setuptools
"$VENV_PY" -m pip install --quiet -e "$PROJECT_DIR"
ok "пакет sfu-converter установлен"

# --- утилита и PATH ------------------------------------------------------
say "4/5 Команда obsidian2sfu"
mkdir -p "$BIN_DIR"
chmod +x "$PROJECT_DIR/obsidian2sfu/obsidian2sfu" 2>/dev/null || true
ln -sf "$PROJECT_DIR/obsidian2sfu/obsidian2sfu" "$BIN_DIR/obsidian2sfu"
ok "ссылка: $BIN_DIR/obsidian2sfu"
case ":$PATH:" in *":$BIN_DIR:"*) ok "$BIN_DIR уже в PATH" ;; *) warn "$BIN_DIR не в PATH — добавьте его или запускайте по полному пути" ;; esac

# --- конфиг --------------------------------------------------------------
say "5/5 Конфиг"
mkdir -p "$CONFIG_DIR"
if [ -f "$CONFIG_DIR/obsidian2sfu.json" ]; then
    ok "конфиг уже есть: $CONFIG_DIR/obsidian2sfu.json"
else
    EXAMPLE="$SCRIPT_DIR/toolkit/config.example.json"
    [ -f "$EXAMPLE" ] || EXAMPLE="$SCRIPT_DIR/config.example.json"
    if [ -f "$EXAMPLE" ]; then
        cp "$EXAMPLE" "$CONFIG_DIR/obsidian2sfu.json"
        ok "создан конфиг: $CONFIG_DIR/obsidian2sfu.json (отредактируйте под себя)"
    fi
fi

echo
say "Готово"
echo "  Репозиторий : $PROJECT_DIR"
echo "  Хранилище   : $VAULT_DIR"
echo "  Конфиг      : $CONFIG_DIR/obsidian2sfu.json"
echo
echo "  Запуск:"
echo "    $BIN_DIR/obsidian2sfu \"Универ/Сети/Отчёт.md\""
echo "  или, если $BIN_DIR в PATH:"
echo "    obsidian2sfu \"Универ/Сети/Отчёт.md\""

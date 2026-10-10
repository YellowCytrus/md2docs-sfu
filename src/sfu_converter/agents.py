"""Установка навыков sfu-converter в поддерживаемые AI-агенты.

Команды агентов забирают плагин из репозитория на GitHub, поэтому локальные
файлы при установке не требуются. Все сообщения и интерактивное меню — на
русском языке.
"""

from __future__ import annotations

import shutil
import subprocess
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import NamedTuple

REPO = "bounchich1/sfu_converter"
PLUGIN_ID = "sfu-converter"
CODEX_COMMANDS = ("codex", "codex.cmd", "codex.exe")


@dataclass(frozen=True)
class Provider:
    id: str
    label: str
    command: str
    mechanism: str
    detection_commands: tuple[str, ...] = ()


PROVIDERS: tuple[Provider, ...] = (
    Provider(
        "claude",
        "Claude Code",
        "claude",
        "claude plugin install",
        ("claude", "claude.cmd", "claude.exe"),
    ),
    Provider(
        "codex",
        "Codex CLI",
        "codex",
        "codex plugin install",
        CODEX_COMMANDS,
    ),
)


class CommandResult(NamedTuple):
    returncode: int
    stdout: str = ""
    stderr: str = ""


Runner = Callable[[str, list[str]], int | CommandResult]
Emitter = Callable[[str], None]
Which = Callable[[str], str | None]
Prompt = Callable[[str], str]


def _provider(provider_id: str) -> Provider | None:
    for provider in PROVIDERS:
        if provider.id == provider_id:
            return provider
    return None


def _first_available_command(which: Which, commands: tuple[str, ...]) -> str | None:
    for command in commands:
        resolved = which(command)
        if resolved:
            return resolved
    return None


def _configured_codex_cli_path(home: str | Path | None = None) -> str | None:
    config_path = (
        Path(home).expanduser() / ".codex" / "config.toml" if home else Path.home() / ".codex" / "config.toml"
    )
    try:
        lines = config_path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return None

    for line in lines:
        key, separator, value = line.partition("=")
        if separator and key.strip() == "CODEX_CLI_PATH":
            candidate = value.strip().strip("\"'").replace("\\\\", "\\")
            if candidate and Path(candidate).is_file():
                return candidate
    return None


def _codex_command(*, which: Which, home: str | Path | None = None) -> str | None:
    return _configured_codex_cli_path(home) or _first_available_command(which, CODEX_COMMANDS)


def _install_commands(
    provider: Provider,
    *,
    which: Which = shutil.which,
    home: str | Path | None = None,
) -> list[tuple[str, list[str]]]:
    if provider.id == "claude":
        return [
            ("claude", ["plugin", "marketplace", "add", REPO]),
            ("claude", ["plugin", "install", f"{PLUGIN_ID}@{PLUGIN_ID}"]),
        ]
    codex = _codex_command(which=which, home=home)
    if codex is not None:
        return [
            (codex, ["plugin", "marketplace", "add", REPO]),
            (codex, ["plugin", "add", f"{PLUGIN_ID}@{PLUGIN_ID}"]),
        ]
    return []


def _default_run(command: str, args: list[str]) -> CommandResult:
    try:
        completed = subprocess.run([command, *args], check=False, text=True, capture_output=True)
        return CommandResult(completed.returncode, completed.stdout, completed.stderr)
    except FileNotFoundError:
        return CommandResult(127, stderr=f"Command not found: {command}")


def detect_available(which: Which = shutil.which, home: str | Path | None = None) -> list[Provider]:
    available: list[Provider] = []
    for provider in PROVIDERS:
        if provider.id == "codex":
            if _codex_command(which=which, home=home) is not None:
                available.append(provider)
            continue
        if any(which(command) for command in (provider.detection_commands or (provider.command,))):
            available.append(provider)
    return available


def _as_command_result(result: int | CommandResult) -> CommandResult:
    if isinstance(result, CommandResult):
        return result
    return CommandResult(int(result))


def _is_idempotent_claude_result(provider: Provider, args: list[str], result: CommandResult) -> bool:
    if provider.id != "claude" or result.returncode == 0:
        return False

    output = f"{result.stdout}\n{result.stderr}".lower()
    if args[:3] == ["plugin", "marketplace", "add"]:
        return "already" in output and any(token in output for token in ("marketplace", "exists", "configured"))
    if args[:2] == ["plugin", "install"]:
        return "already" in output and any(token in output for token in ("plugin", "installed", "enabled"))
    return False


def _is_idempotent_codex_result(provider: Provider, args: list[str], result: CommandResult) -> bool:
    if provider.id != "codex" or result.returncode == 0:
        return False

    output = f"{result.stdout}\n{result.stderr}".lower()
    if args[:3] == ["plugin", "marketplace", "add"]:
        return "already" in output and any(token in output for token in ("marketplace", "exists", "configured"))
    if args[:2] == ["plugin", "add"]:
        return "already" in output and any(token in output for token in ("plugin", "installed", "enabled"))
    return False


def _emit_failure_detail(result: CommandResult, emit: Emitter) -> None:
    emit(f"  код {result.returncode}")
    detail = (result.stderr or result.stdout).strip()
    if detail:
        for line in detail.splitlines():
            if line.strip():
                emit(f"  {line.strip()}")


def install_provider(
    provider: Provider,
    *,
    dry_run: bool,
    which: Which = shutil.which,
    home: str | Path | None = None,
    run: Runner = _default_run,
    emit: Emitter = print,
) -> bool:
    emit(f">> {provider.label} ({provider.mechanism})")
    commands = _install_commands(provider, which=which, home=home)
    if not commands:
        emit("  [x] Не найден Codex CLI: нужна команда `codex` в PATH или CODEX_CLI_PATH в ~/.codex/config.toml.")
        return False
    for command, args in commands:
        printable = f"{command} {' '.join(args)}"
        if dry_run:
            emit(f"  демо-запуск: {printable}")
            continue
        emit(f"  $ {printable}")
        result = _as_command_result(run(command, args))
        if result.returncode == 0:
            continue
        if _is_idempotent_claude_result(provider, args, result) or _is_idempotent_codex_result(provider, args, result):
            if args[:3] == ["plugin", "marketplace", "add"]:
                emit(f"  [ok] Marketplace уже настроено: {provider.label}")
            else:
                emit(f"  [ok] Plugin уже установлен: {provider.label}")
            continue
        _emit_failure_detail(result, emit)
        if args[:3] == ["plugin", "marketplace", "add"]:
            command_name = "codex" if provider.id == "codex" else "claude"
            emit(f"  Подсказка: если marketplace уже добавлен, проверьте `{command_name} plugin marketplace list`.")
        elif args[:2] in (["plugin", "install"], ["plugin", "add"]):
            command_name = "codex" if provider.id == "codex" else "claude"
            emit(f"  Подсказка: если plugin уже установлен, проверьте `{command_name} plugin list`.")
        if provider.id == "codex":
            emit("  Подсказка: для Codex требуется доступная команда `codex`.")
        emit(f"  [x] Не удалось установить {provider.label}")
        return False
    if not dry_run:
        emit(f"  [ok] Готово: {provider.label}")
    return True


def select_providers_interactive(
    providers: Sequence[Provider],
    *,
    prompt: Prompt = input,
    emit: Emitter = print,
) -> list[Provider]:
    emit("Доступные агенты:")
    for index, provider in enumerate(providers, 1):
        emit(f"  {index}. {provider.label}")
    emit(f"  A. Установить во все ({len(providers)})")
    emit("  0. Отмена")

    choice = prompt("Выберите агенты (номера через запятую или 'a'): ").strip().lower()

    if choice in {"", "0"}:
        return []
    if choice == "a":
        return list(providers)

    selected: list[Provider] = []
    for token in choice.split(","):
        token = token.strip()
        if not token.isdigit():
            continue
        index = int(token) - 1
        if 0 <= index < len(providers) and providers[index] not in selected:
            selected.append(providers[index])
    return selected


def _print_list(emit: Emitter) -> None:
    emit("Поддерживаемые агенты:")
    for provider in PROVIDERS:
        emit(f"  {provider.id:<7} {provider.label:<12} {provider.mechanism}")


def run_agents(
    action: str = "install",
    *,
    only: Iterable[str] = (),
    install_all: bool = False,
    dry_run: bool = False,
    home: str | Path | None = None,
    which: Which = shutil.which,
    run: Runner = _default_run,
    prompt: Prompt = input,
    emit: Emitter = print,
) -> int:
    if action == "list":
        _print_list(emit)
        return 0

    only = tuple(only)
    if only:
        selected: list[Provider] = []
        for agent_id in only:
            provider = _provider(agent_id)
            if provider is None:
                emit(f"Неизвестный агент: {agent_id}")
                return 2
            selected.append(provider)
    else:
        available = detect_available(which=which, home=home)
        if not available:
            emit("Поддерживаемые агенты не найдены. Установите Claude Code или Codex CLI.")
            return 1
        if install_all:
            selected = available
        else:
            selected = select_providers_interactive(available, prompt=prompt, emit=emit)
            if not selected:
                emit("Установка отменена.")
                return 0

    installed: list[str] = []
    failed: list[str] = []
    for provider in selected:
        if install_provider(provider, dry_run=dry_run, which=which, home=home, run=run, emit=emit):
            installed.append(provider.id)
        else:
            failed.append(provider.id)

    if installed:
        emit("Установлено: " + ", ".join(installed))
    if failed:
        emit("Ошибки: " + ", ".join(failed))
        return 1
    return 0

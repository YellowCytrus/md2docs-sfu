import sys

from sfu_converter import agents


def make_emit():
    lines: list[str] = []
    return lines, lines.append


def test_provider_lookup_returns_provider_or_none():
    assert agents._provider("claude").label == "Claude Code"
    assert agents._provider("codex").label == "Codex CLI"
    assert agents._provider("unknown") is None


def test_detect_available_filters_by_command_presence(tmp_path):
    present = {"claude"}

    available = agents.detect_available(which=lambda command: "/path" if command in present else None, home=tmp_path)

    assert [provider.id for provider in available] == ["claude"]


def test_detect_available_recognizes_codex_when_cli_is_present(tmp_path):
    present = {"codex"}

    available = agents.detect_available(which=lambda command: "/path" if command in present else None, home=tmp_path)

    assert [provider.id for provider in available] == ["codex"]


def test_detect_available_recognizes_codex_windows_executable(tmp_path):
    present = {"codex.exe"}

    available = agents.detect_available(which=lambda command: "/path" if command in present else None, home=tmp_path)

    assert [provider.id for provider in available] == ["codex"]


def test_detect_available_does_not_offer_codex_for_npx_only(tmp_path):
    present = {"npx"}

    available = agents.detect_available(which=lambda command: "/path" if command in present else None, home=tmp_path)

    assert [provider.id for provider in available] == []


def test_install_commands_claude_uses_marketplace_then_install():
    commands = agents._install_commands(agents._provider("claude"))

    assert commands == [
        ("claude", ["plugin", "marketplace", "add", agents.REPO]),
        ("claude", ["plugin", "install", f"{agents.PLUGIN_ID}@{agents.PLUGIN_ID}"]),
    ]


def test_install_commands_codex_uses_plugin_marketplace_and_add(tmp_path):
    commands = agents._install_commands(
        agents._provider("codex"),
        which=lambda command: "C:\\codex\\codex.exe" if command == "codex" else None,
        home=tmp_path,
    )

    assert commands == [
        ("C:\\codex\\codex.exe", ["plugin", "marketplace", "add", agents.REPO]),
        ("C:\\codex\\codex.exe", ["plugin", "add", f"{agents.PLUGIN_ID}@{agents.PLUGIN_ID}"]),
    ]


def test_install_commands_codex_prefers_configured_cli_path(tmp_path):
    config_dir = tmp_path / ".codex"
    config_dir.mkdir()
    configured = tmp_path / "codex.exe"
    configured.write_text("", encoding="utf-8")
    (config_dir / "config.toml").write_text(
        "CODEX_CLI_PATH = '" + str(configured).replace("\\", "\\\\") + "'\n",
        encoding="utf-8",
    )

    commands = agents._install_commands(
        agents._provider("codex"),
        which=lambda command: "C:\\WindowsApps\\codex.exe" if command == "codex" else None,
        home=tmp_path,
    )

    assert commands == [
        (str(configured), ["plugin", "marketplace", "add", agents.REPO]),
        (str(configured), ["plugin", "add", f"{agents.PLUGIN_ID}@{agents.PLUGIN_ID}"]),
    ]


def test_install_commands_codex_reports_no_cli(tmp_path):
    commands = agents._install_commands(agents._provider("codex"), which=lambda command: None, home=tmp_path)

    assert commands == []


def test_install_commands_codex_ignores_unusable_configured_cli_path(tmp_path):
    config_dir = tmp_path / ".codex"
    config_dir.mkdir()
    missing = tmp_path / "missing-codex.exe"
    (config_dir / "config.toml").write_text(
        "\n".join(
            [
                "OTHER = 'ignored'",
                "CODEX_CLI_PATH = '" + str(missing).replace("\\", "\\\\") + "'",
                "ANOTHER = 'ignored'",
            ]
        ),
        encoding="utf-8",
    )

    commands = agents._install_commands(agents._provider("codex"), which=lambda command: None, home=tmp_path)

    assert commands == []


def test_install_provider_dry_run_does_not_invoke_runner():
    lines, emit = make_emit()
    calls = []

    ok = agents.install_provider(
        agents._provider("codex"),
        dry_run=True,
        which=lambda command: "/path" if command == "codex" else None,
        run=lambda command, args: calls.append((command, args)) or 0,
        emit=emit,
    )

    assert ok is True
    assert calls == []
    assert any("демо" in line for line in lines)


def test_install_provider_runs_each_command_on_success():
    lines, emit = make_emit()
    calls = []

    ok = agents.install_provider(
        agents._provider("claude"),
        dry_run=False,
        run=lambda command, args: calls.append((command, args)) or 0,
        emit=emit,
    )

    assert ok is True
    assert [command for command, _ in calls] == ["claude", "claude"]
    assert any("Готово" in line for line in lines)


def test_install_provider_stops_and_reports_failure():
    lines, emit = make_emit()
    calls = []

    def run(command, args):
        calls.append((command, args))
        return 1

    ok = agents.install_provider(agents._provider("claude"), dry_run=False, run=run, emit=emit)

    assert ok is False
    assert len(calls) == 1
    assert any("Не удалось" in line for line in lines)


def test_install_provider_treats_already_configured_claude_marketplace_as_success():
    lines, emit = make_emit()
    calls = []

    def run(command, args):
        calls.append((command, args))
        if args[:3] == ["plugin", "marketplace", "add"]:
            return agents.CommandResult(1, stderr="Marketplace 'sfu-converter' already exists")
        return 0

    ok = agents.install_provider(agents._provider("claude"), dry_run=False, run=run, emit=emit)

    assert ok is True
    assert [args[0] for _, args in calls] == ["plugin", "plugin"]
    assert any("уже настроено" in line.lower() for line in lines)


def test_install_provider_treats_already_installed_claude_plugin_as_success():
    lines, emit = make_emit()
    calls = []

    def run(command, args):
        calls.append((command, args))
        if args[:3] == ["plugin", "marketplace", "add"]:
            return 0
        return agents.CommandResult(1, stderr="Plugin sfu-converter@sfu-converter is already installed")

    ok = agents.install_provider(agents._provider("claude"), dry_run=False, run=run, emit=emit)

    assert ok is True
    assert len(calls) == 2
    assert any("уже установлен" in line.lower() for line in lines)


def test_claude_idempotency_ignores_unrelated_commands():
    result = agents.CommandResult(1, stderr="already done")

    ok = agents._is_idempotent_claude_result(agents._provider("claude"), ["plugin", "update"], result)

    assert ok is False


def test_codex_idempotency_ignores_unrelated_commands():
    result = agents.CommandResult(1, stderr="already done")

    ok = agents._is_idempotent_codex_result(agents._provider("codex"), ["plugin", "update"], result)

    assert ok is False


def test_install_provider_treats_already_configured_codex_marketplace_as_success(tmp_path):
    lines, emit = make_emit()
    calls = []

    def run(command, args):
        calls.append((command, args))
        if args[:3] == ["plugin", "marketplace", "add"]:
            return agents.CommandResult(1, stderr="Marketplace 'sfu-converter' already configured")
        return 0

    ok = agents.install_provider(
        agents._provider("codex"),
        dry_run=False,
        which=lambda command: "codex" if command == "codex" else None,
        home=tmp_path,
        run=run,
        emit=emit,
    )

    assert ok is True
    assert [args[:2] for _, args in calls] == [["plugin", "marketplace"], ["plugin", "add"]]
    assert any("уже настроено" in line.lower() for line in lines)


def test_install_provider_treats_already_installed_codex_plugin_as_success(tmp_path):
    lines, emit = make_emit()

    def run(command, args):
        if args[:3] == ["plugin", "marketplace", "add"]:
            return 0
        return agents.CommandResult(1, stderr="Plugin sfu-converter@sfu-converter is already installed")

    ok = agents.install_provider(
        agents._provider("codex"),
        dry_run=False,
        which=lambda command: "codex" if command == "codex" else None,
        home=tmp_path,
        run=run,
        emit=emit,
    )

    assert ok is True
    assert any("уже установлен" in line.lower() for line in lines)


def test_install_provider_reports_command_failure_details():
    lines, emit = make_emit()

    def run(command, args):
        return agents.CommandResult(2, stderr="network unavailable\n\nretry later")

    ok = agents.install_provider(
        agents._provider("codex"),
        dry_run=False,
        which=lambda command: "/path" if command == "codex" else None,
        run=run,
        emit=emit,
    )

    assert ok is False
    assert any("код 2" in line for line in lines)
    assert any("network unavailable" in line for line in lines)
    assert any("retry later" in line for line in lines)


def test_install_provider_reports_missing_codex_installer_before_running(tmp_path):
    lines, emit = make_emit()
    calls = []

    ok = agents.install_provider(
        agents._provider("codex"),
        dry_run=False,
        which=lambda command: None,
        home=tmp_path,
        run=lambda command, args: calls.append((command, args)) or 0,
        emit=emit,
    )

    assert ok is False
    assert calls == []
    assert any("Codex CLI" in line for line in lines)


def test_install_provider_reports_claude_plugin_install_failure_hint():
    lines, emit = make_emit()

    def run(command, args):
        if args[:3] == ["plugin", "marketplace", "add"]:
            return 0
        return agents.CommandResult(2, stderr="install failed")

    ok = agents.install_provider(agents._provider("claude"), dry_run=False, run=run, emit=emit)

    assert ok is False
    assert any("claude plugin list" in line for line in lines)


def test_install_provider_reports_codex_failure_without_plugin_hint(monkeypatch):
    lines, emit = make_emit()

    monkeypatch.setattr(agents, "_install_commands", lambda provider, **kwargs: [("codex", ["status"])])

    ok = agents.install_provider(
        agents._provider("codex"),
        dry_run=False,
        run=lambda command, args: agents.CommandResult(2, stderr="status failed"),
        emit=emit,
    )

    assert ok is False
    assert any("для Codex требуется" in line for line in lines)
    assert not any("plugin list" in line for line in lines)


def test_select_providers_interactive_cancel_returns_empty():
    lines, emit = make_emit()

    selected = agents.select_providers_interactive(list(agents.PROVIDERS), prompt=lambda _: "0", emit=emit)

    assert selected == []


def test_select_providers_interactive_all_returns_every_provider():
    lines, emit = make_emit()

    selected = agents.select_providers_interactive(list(agents.PROVIDERS), prompt=lambda _: "A", emit=emit)

    assert selected == list(agents.PROVIDERS)


def test_select_providers_interactive_numbers_dedupe_and_skip_invalid():
    providers = list(agents.PROVIDERS)
    lines, emit = make_emit()

    selected = agents.select_providers_interactive(providers, prompt=lambda _: "1, 1, 9, x", emit=emit)

    assert selected == [providers[0]]


def test_select_providers_interactive_empty_input_returns_empty():
    lines, emit = make_emit()

    selected = agents.select_providers_interactive(list(agents.PROVIDERS), prompt=lambda _: "", emit=emit)

    assert selected == []


def test_run_agents_list_prints_all_providers():
    lines, emit = make_emit()

    code = agents.run_agents("list", emit=emit)

    assert code == 0
    assert any("claude" in line for line in lines)
    assert any("codex" in line for line in lines)


def test_run_agents_only_rejects_unknown_agent():
    lines, emit = make_emit()

    code = agents.run_agents("install", only=("ghost",), emit=emit)

    assert code == 2
    assert any("Неизвестный агент" in line for line in lines)


def test_run_agents_only_installs_selected_bypassing_detection(tmp_path):
    lines, emit = make_emit()
    calls = []

    code = agents.run_agents(
        "install",
        only=("codex",),
        which=lambda command: "/path" if command == "codex" else None,
        home=tmp_path,
        run=lambda command, args: calls.append(command) or 0,
        emit=emit,
    )

    assert code == 0
    assert calls == ["/path", "/path"]
    assert any("Установлено" in line for line in lines)


def test_run_agents_reports_no_agent_detected(tmp_path):
    lines, emit = make_emit()

    code = agents.run_agents("install", which=lambda command: None, home=tmp_path, emit=emit)

    assert code == 1
    assert any("не найдены" in line for line in lines)


def test_run_agents_all_installs_every_detected_agent(tmp_path):
    lines, emit = make_emit()
    calls = []

    code = agents.run_agents(
        "install",
        install_all=True,
        which=lambda command: "/path" if command in {"claude", "codex"} else None,
        home=tmp_path,
        run=lambda command, args: calls.append(command) or 0,
        emit=emit,
    )

    assert code == 0
    assert calls == ["claude", "claude", "/path", "/path"]


def test_run_agents_all_detects_codex_from_configured_cli_path(tmp_path):
    config_dir = tmp_path / ".codex"
    config_dir.mkdir()
    configured = tmp_path / "codex.exe"
    configured.write_text("", encoding="utf-8")
    (config_dir / "config.toml").write_text(
        "CODEX_CLI_PATH = '" + str(configured).replace("\\", "\\\\") + "'\n",
        encoding="utf-8",
    )
    calls = []

    code = agents.run_agents(
        "install",
        install_all=True,
        which=lambda command: "/path" if command == "claude" else None,
        home=tmp_path,
        run=lambda command, args: calls.append(command) or 0,
        emit=lambda line: None,
    )

    assert code == 0
    assert calls == ["claude", "claude", str(configured), str(configured)]


def test_run_agents_interactive_cancel_returns_zero():
    lines, emit = make_emit()

    code = agents.run_agents(
        "install",
        which=lambda command: "/path",
        prompt=lambda _: "0",
        emit=emit,
    )

    assert code == 0
    assert any("отменена" in line.lower() for line in lines)


def test_run_agents_interactive_install_reports_failure_exit_code():
    lines, emit = make_emit()

    code = agents.run_agents(
        "install",
        which=lambda command: "/path",
        prompt=lambda _: "1",
        run=lambda command, args: 1,
        emit=emit,
    )

    assert code == 1
    assert any("Ошибки" in line for line in lines)


def test_default_run_returns_process_exit_code():
    result = agents._default_run(sys.executable, ["-c", "raise SystemExit(0)"])

    assert result.returncode == 0


def test_default_run_missing_command_returns_127():
    result = agents._default_run("sfu-converter-no-such-binary-xyz", [])

    assert result.returncode == 127
    assert "Command not found" in result.stderr

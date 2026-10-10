<#
    Установщик sfu-toolkit (Windows).

    Проверяет зависимости и НЕ трогает то, что уже установлено; для отсутствующих
    спрашивает разрешение и ставит через winget. Затем создаёт venv, ставит
    конвертер, кладёт команду obsidian2sfu в PATH и создаёт конфиг.

    Запуск (из корня репозитория):
        powershell -ExecutionPolicy Bypass -File .\install.ps1

    Флаги:
        -Yes          отвечать «да» на все вопросы (неинтерактивно)
        -RepoUrl      git-URL (для автономной установки)
        -ProjectDir   куда клонировать (по умолчанию — папка скрипта, если в ней проект)
        -Vault        путь к хранилищу Obsidian
#>
param(
    [switch]$Yes,
    [string]$RepoUrl = "https://github.com/bounchich1/sfu_converter.git",
    [string]$ProjectDir = "",
    [string]$Vault = "$env:USERPROFILE\obsidian_backup"
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$BinDir = "$env:USERPROFILE\bin"
$ConfigDir = "$env:APPDATA\sfu"

function Say($m)  { Write-Host "==> $m" -ForegroundColor Cyan }
function Ok($m)   { Write-Host "  ✓ $m" -ForegroundColor Green }
function Warn($m) { Write-Host "  ! $m" -ForegroundColor Yellow }

function Confirm($q) {
    if ($Yes) { return $true }
    $a = Read-Host "  $q [y/N]"
    return ($a -match '^[yY]')
}

function Install-Winget($id, $name) {
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        & winget install --id $id -e --accept-source-agreements --accept-package-agreements
        return ($LASTEXITCODE -eq 0)
    }
    Warn "winget не найден — установите «$name» вручную"
    return $false
}

function Test-Python10([string]$cmd) {
    try { & $cmd -c "import sys; raise SystemExit(0 if sys.version_info[:2] >= (3,10) else 1)" 2>$null } catch { return $false }
    return ($LASTEXITCODE -eq 0)
}

function Ensure-Required($found, $id, $name, $q) {
    if ($found) { Ok "$name — уже установлен"; return $true }
    Warn "$name не найден"
    if (Confirm $q) { return (Install-Winget $id $name) }
    Warn "пропускаю установку «$name»"
    return $false
}

function Ensure-Optional($found, $id, $name) {
    if ($found) { Ok "$name — уже установлен"; return }
    Warn "$name не найден (необязательно)"
    if (Confirm "Установить «$name» (необязательно)?") {
        Install-Winget $id $name | Out-Null
    } else {
        Warn "без «$name»: PDF-превью и номера страниц в содержании будут недоступны"
    }
}

Say "1/5 Проверка зависимостей"

$py = $null
foreach ($c in @("py", "python", "python3")) {
    if (Get-Command $c -ErrorAction SilentlyContinue) {
        if (Test-Python10 $c) { $py = $c; break }
    }
}
if ($py) { Ok "Python ($py)"; }
else {
    if (Ensure-Required $false "Python.Python.3.12" "Python 3.10+" "Установить Python 3.10+?") {
        foreach ($c in @("py", "python")) { if (Get-Command $c -ErrorAction SilentlyContinue) { $py = $c; break } }
    }
}
if (-not $py) { throw "Без Python 3.10+ продолжить нельзя." }

Say "2/5 Проект"
if (Test-Path (Join-Path $ScriptDir "pyproject.toml")) {
    $ProjectDir = $ScriptDir
    Ok "использую текущий репозиторий: $ProjectDir"
} else {
    if (-not $ProjectDir) { $ProjectDir = "$env:USERPROFILE\Programs\tupoi_word" }
    if (-not (Ensure-Required ([bool](Get-Command git -ErrorAction SilentlyContinue)) "Git.Git" "Git" "Установить Git?")) {
        throw "Без Git продолжить нельзя."
    }
    if (Test-Path "$ProjectDir\.git") {
        git -C $ProjectDir pull --ff-only
        Ok "репозиторий обновлён: $ProjectDir"
    } else {
        New-Item -ItemType Directory -Force (Split-Path $ProjectDir) | Out-Null
        git clone $RepoUrl $ProjectDir
        Ok "склонировано в $ProjectDir"
    }
}

Say "3/5 Виртуальное окружение"
$venvPy = "$ProjectDir\.venv\Scripts\python.exe"
if (-not (Test-Path $venvPy)) {
    & $py -m venv "$ProjectDir\.venv"
}
& $venvPy -m pip install --quiet --upgrade pip wheel setuptools
& $venvPy -m pip install --quiet -e $ProjectDir
Ok "пакет sfu-converter установлен"

Say "4/5 Команда obsidian2sfu"
New-Item -ItemType Directory -Force $BinDir | Out-Null
$shim = "@echo off`r`n`"$venvPy`" `"$ProjectDir\obsidian2sfu\obsidian2sfu.py`" %*"
Set-Content -Path "$BinDir\obsidian2sfu.cmd" -Value $shim -Encoding ASCII
Ok "команда: $BinDir\obsidian2sfu.cmd"

$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($userPath -notlike "*$BinDir*") {
    [Environment]::SetEnvironmentVariable("Path", "$userPath;$BinDir", "User")
    Warn "добавлено в PATH: $BinDir (перезапустите терминал)"
} else {
    Ok "$BinDir уже в PATH"
}

Say "5/5 Конфиг"
New-Item -ItemType Directory -Force $ConfigDir | Out-Null
if (Test-Path "$ConfigDir\obsidian2sfu.json") {
    Ok "конфиг уже есть: $ConfigDir\obsidian2sfu.json"
} else {
    $example = "$ScriptDir\toolkit\config.example.json"
    if (-not (Test-Path $example)) { $example = "$ScriptDir\config.example.json" }
    if (Test-Path $example) {
        Copy-Item $example "$ConfigDir\obsidian2sfu.json"
        Ok "создан конфиг: $ConfigDir\obsidian2sfu.json (отредактируйте под себя)"
    }
}

Write-Host ""
Say "Готово"
Write-Host "  Репозиторий : $ProjectDir"
Write-Host "  Хранилище   : $Vault"
Write-Host "  Конфиг      : $ConfigDir\obsidian2sfu.json"
Write-Host ""
Write-Host "  Запуск:  obsidian2sfu `"Универ\Сети\Отчёт.md`""

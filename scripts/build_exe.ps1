param(
    [string]$Name = "accelscope",
    [string]$PythonExe = "python",
    [switch]$IncludeOpenVINO,
    [switch]$IncludeOMZ,
    [switch]$Clean
)

$ErrorActionPreference = "Stop"

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $RepoRoot

if ($Clean) {
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue ".\build", ".\dist", ".\$Name.spec"
}

$InstallTarget = ".[dev]"
if ($IncludeOpenVINO) {
    $InstallTarget = ".[dev,openvino]"
}

& $PythonExe -m pip install -e $InstallTarget

if ($IncludeOMZ) {
    & $PythonExe -m pip install "openvino-dev==2024.6.0"
}

$PyInstallerArgs = @(
    "-m", "PyInstaller",
    "--name", $Name,
    "--onefile",
    "--clean",
    "--paths", ".\src"
)

if ($IncludeOpenVINO) {
    $PyInstallerArgs += @("--collect-all", "openvino")
}

if ($IncludeOMZ) {
    $PyInstallerArgs += @("--collect-all", "omz_tools")
}

$PyInstallerArgs += ".\src\ai_pc_kit\cli.py"

& $PythonExe $PyInstallerArgs

$ExePath = Join-Path $RepoRoot "dist\$Name.exe"
if (-not (Test-Path $ExePath)) {
    throw "Expected exe was not created: $ExePath"
}

Write-Host "Built $ExePath"
& $ExePath --help

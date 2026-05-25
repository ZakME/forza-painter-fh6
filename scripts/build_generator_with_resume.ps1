$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path | Split-Path -Parent
$GeneratorRoot = Join-Path $Root "external\geometrize-gpu"
$OutputExe = Join-Path $Root "bin\forza-painter-geometrize-go.exe"

function Resolve-GoExecutable {
    param([string]$ProjectRoot)
    $candidates = @(
        "C:\Program Files\Go\bin\go.exe",
        (Join-Path $ProjectRoot ".tools\go\bin\go.exe")
    )
    foreach ($candidate in $candidates) {
        if (Test-Path $candidate) {
            return (Resolve-Path $candidate).Path
        }
    }
    $onPath = Get-Command go -ErrorAction SilentlyContinue
    if ($onPath) {
        return $onPath.Source
    }
    throw "Go not found. Install from https://go.dev/dl/ or add Go\bin to PATH."
}

$GoExe = Resolve-GoExecutable -ProjectRoot $Root
$GoBin = Split-Path -Parent $GoExe
$env:Path = "$GoBin;$env:Path"
Write-Host "Using Go: $GoExe"
& $GoExe version

if (-not (Test-Path $GeneratorRoot)) {
    throw "Missing external\geometrize-gpu. Run: git clone --depth 1 https://github.com/zjl88858/forza-painter-geometrize-gpu.git external/geometrize-gpu"
}

Push-Location $GeneratorRoot
try {
    & (Join-Path $GeneratorRoot "build.ps1") -OutputName $OutputExe
} finally {
    Pop-Location
}
Write-Host "Installed generator with resume support to $OutputExe"

# Builds dist\PDF Toolkit.exe: a single self-contained file with Python and
# every dependency bundled. Run from this folder:  .\build.ps1
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Test-Path .venv)) {
    py -3.12 -m venv .venv
}
$py = ".\.venv\Scripts\python.exe"
& $py -m pip install --quiet --upgrade pip
& $py -m pip install --quiet -r requirements.txt -r requirements-dev.txt

& $py -m unittest discover -s tests
if ($LASTEXITCODE -ne 0) { throw "Tests failed; not building." }

& $py -m PyInstaller --noconfirm --clean `
    --onefile --windowed `
    --name "PDF Toolkit" `
    --icon assets\icon.ico `
    --version-file packaging\version_info.txt `
    --paths app `
    --add-data "app\ui;ui" `
    --exclude-module tkinter `
    --exclude-module numpy `
    app\main.py
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed." }

$exe = Get-Item "dist\PDF Toolkit.exe"
"Built {0} ({1:N1} MB)" -f $exe.FullName, ($exe.Length / 1MB)

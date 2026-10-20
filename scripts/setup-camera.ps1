param([string]$PythonPath, [string[]]$PhoneHosts)
$ErrorActionPreference = 'Stop'
$projectPath = Split-Path -Parent $PSScriptRoot
if (!$PythonPath) { $PythonPath = Join-Path $projectPath '.venv/Scripts/python.exe' }
if (!(Test-Path -LiteralPath $PythonPath)) { throw 'Python environment not found. Create .venv and install backend/requirements.txt, or pass -PythonPath.' }
if (!$PhoneHosts) {
    $PhoneHosts = @(Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -ne '127.0.0.1' -and $_.IPAddress -notlike '169.254.*' } | Select-Object -ExpandProperty IPAddress)
}
& $PythonPath (Join-Path $PSScriptRoot 'camera_cert.py') @PhoneHosts
if ($LASTEXITCODE -ne 0) { throw 'Certificate generation failed.' }
Write-Host 'Use the address matching your Wi-Fi network, on the same Wi-Fi as your phone:'
foreach ($ip in $PhoneHosts) { Write-Host "https://${ip}:5443" }

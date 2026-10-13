$ErrorActionPreference = 'Stop'
$projectPath = Split-Path -Parent $PSScriptRoot
$envPath = Join-Path $projectPath '.env'
if (Test-Path -LiteralPath $envPath) { Write-Host '.env already exists; keeping your settings.'; exit 0 }
function New-Secret {
    $bytes = New-Object byte[] 24
    [Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
    return ([BitConverter]::ToString($bytes)).Replace('-', '').ToLower()
}
$lines = @(('DB_PASSWORD=' + (New-Secret)), ('DB_ROOT_PASSWORD=' + (New-Secret)), 'ADMIN_EMAIL=admin@help.local', ('ADMIN_PASSWORD=' + (New-Secret)))
[IO.File]::WriteAllLines($envPath, $lines)
Write-Host 'Created .env with random local passwords. Open it privately to find your admin sign-in details.'

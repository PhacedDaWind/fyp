param([string]$Email)
$ErrorActionPreference = 'Stop'
$projectPath = Split-Path -Parent $PSScriptRoot
$envPath = Join-Path $projectPath '.env'

# Do not run setup.ps1 here: new database secrets won't unlock an existing volume.
$ids = @(docker ps -aq --filter 'label=com.docker.compose.service=api')
if ($LASTEXITCODE -ne 0) { throw 'Docker is unavailable. Start Docker Desktop and resolve any WSL error first.' }
$candidates = @()
foreach ($id in $ids) {
    $item = (docker inspect $id | ConvertFrom-Json)[0]
    $workingDir = $item.Config.Labels.'com.docker.compose.project.working_dir'
    if ($workingDir -and [IO.Path]::GetFullPath($workingDir).TrimEnd('\','/') -eq $projectPath.TrimEnd('\','/')) { $candidates += $item }
}
if ($candidates.Count -ne 1) { throw 'Could not identify exactly one existing API container for this project. No credentials changed.' }
$api = $candidates[0]
$project = $api.Config.Labels.'com.docker.compose.project'
$dbIds = @(docker ps -aq --filter "label=com.docker.compose.project=$project" --filter 'label=com.docker.compose.service=db')
if ($dbIds.Count -ne 1) { throw 'Could not identify the existing database container. No credentials changed.' }
$dbContainer = (docker inspect $dbIds[0] | ConvertFrom-Json)[0]
function Read-ContainerEnv($container) {
    $values = @{}
    foreach ($line in $container.Config.Env) { $pair = $line -split '=',2; $values[$pair[0]] = $pair[1] }
    return $values
}
$apiEnv = Read-ContainerEnv $api
$dbEnv = Read-ContainerEnv $dbContainer
if (!$apiEnv['DB_PASSWORD'] -or !$dbEnv['MYSQL_ROOT_PASSWORD']) { throw 'Existing container credentials are incomplete. No credentials changed.' }

# Reconstruct only missing configuration from the existing containers, keeping
# any unrelated settings. Secrets stay out of terminal output and command args.
$settings = @{}
if (Test-Path -LiteralPath $envPath) {
    foreach ($line in [IO.File]::ReadAllLines($envPath)) {
        if ($line -match '^([A-Z_]+)=(.*)$') { $settings[$Matches[1]] = $Matches[2] }
    }
}
$settings['DB_PASSWORD'] = $apiEnv['DB_PASSWORD']
$settings['DB_ROOT_PASSWORD'] = $dbEnv['MYSQL_ROOT_PASSWORD']
if (!$settings['ADMIN_EMAIL']) { $settings['ADMIN_EMAIL'] = $apiEnv['ADMIN_EMAIL'] }
if (!$settings['ADMIN_PASSWORD']) { $settings['ADMIN_PASSWORD'] = $apiEnv['ADMIN_PASSWORD'] }
function Save-Settings {
    $lines = @($settings.Keys | Sort-Object | ForEach-Object { $_ + '=' + $settings[$_] })
    [IO.File]::WriteAllLines($envPath, $lines, [Text.UTF8Encoding]::new($false))
}
Save-Settings
if (!$dbContainer.State.Running) { docker start $dbContainer.Id | Out-Null; if ($LASTEXITCODE -ne 0) { throw 'Database failed to start.' } }
$ready = $false
for ($i=0; $i -lt 30; $i++) {
    try {
        # Authenticate with the container's own secret, keeping it out of the
        # host command line. PowerShell 5 treats native stderr as an exception.
        docker exec $dbContainer.Id sh -c 'MYSQL_PWD=$MYSQL_ROOT_PASSWORD mysqladmin --user=root --host=127.0.0.1 --silent ping' 2>$null | Out-Null
        $pingExit = $LASTEXITCODE
    } catch { $pingExit = 1 }
    if ($pingExit -eq 0) { $ready = $true; break }
    Start-Sleep -Seconds 2
}
if (!$ready) { throw 'Recovered .env, but MySQL is not ready. Run recovery again after Docker finishes starting.' }
$api = (docker inspect $api.Id | ConvertFrom-Json)[0]
if (!$api.State.Running) { docker start $api.Id | Out-Null; if ($LASTEXITCODE -ne 0) { throw 'API failed to start.' } }
$resetScript = [IO.File]::ReadAllText((Join-Path $projectPath 'backend/reset_admin.py'))
if ($Email) { $result = $resetScript | docker exec -i $api.Id python - --email $Email }
else { $result = $resetScript | docker exec -i $api.Id python - }
if ($LASTEXITCODE -ne 0) { throw 'Recovery failed; review the error above. If multiple administrators exist, rerun with -Email.' }
$credentials = $result | ConvertFrom-Json
$settings['ADMIN_EMAIL'] = $credentials.email
$settings['ADMIN_PASSWORD'] = $credentials.password
Save-Settings
Write-Host "Reset administrator $($credentials.email). Read ADMIN_PASSWORD in the ignored .env file to sign in."
Write-Host "Vehicle and parking records were preserved; this administrator's existing sessions were revoked."

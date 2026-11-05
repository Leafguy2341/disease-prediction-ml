# Source-only staging/publication. Never mirror/delete dataset or model artifacts.
[CmdletBinding()]
param(
    [switch]$Publish,
    [string]$DriveProjectPath,
    [switch]$CheckOnly,
    [switch]$Refresh,
    [string]$PythonExe = 'python'
)
$ErrorActionPreference = 'Stop'
$project = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
if ($Publish -and $CheckOnly) { throw 'Choose Publish or CheckOnly.' }
if ($Refresh) { Write-Output 'Refresh now creates/reuses an immutable source revision; no old staging is removed.' }
$action = if ($Publish) { 'publish' } else { 'stage' }
$packArgs = @('-B', (Join-Path $PSScriptRoot 'package_handover.py'), $action, '--project-root', $project)
if ($Publish) {
    if ([string]::IsNullOrWhiteSpace($DriveProjectPath)) { throw 'Specify the actual existing Google Drive for desktop project path with -DriveProjectPath.' }
    $packArgs += @('--drive-project-path', $DriveProjectPath)
}
if ($CheckOnly) { $packArgs += '--check-only' }
& $PythonExe @packArgs
if ($LASTEXITCODE -ne 0) { throw "Source operation failed (exit $LASTEXITCODE). Nothing in data/models was synchronized." }

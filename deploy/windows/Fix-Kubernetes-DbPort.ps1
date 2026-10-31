# Preserve local YAML edits while fixing the DB Service environment-variable collision.
# Windows PowerShell 5.1 and PowerShell 7; no additional modules required.
[CmdletBinding()]
param(
    [string]$ProjectRoot = (Join-Path $PSScriptRoot '../..'),
    [string]$BackupRoot = ''
)
$ErrorActionPreference = 'Stop'
$ProjectRoot = (Resolve-Path -LiteralPath $ProjectRoot).Path
$files = @(
    @{ Path = 'k8s/20-provision.yml'; PodIndent = 6 },
    @{ Path = 'k8s/40-tools.yml'; PodIndent = 2 }
)
$changes = @()
foreach ($file in $files) {
    $path = Join-Path $ProjectRoot $file.Path
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw ('Missing manifest: ' + $file.Path) }
    $original = [IO.File]::ReadAllText($path)
    $text = $original
    $newline = "`n"
    if ($text.Contains("`r`n")) { $newline = "`r`n" }
    $hostPattern = '(?m)^(?<indent>[ ]*)- name: DB_HOST[ \t]*\r?\n\k<indent>  value: db[ \t]*\r?$'
    $hostMatches = [regex]::Matches($text, $hostPattern)
    if ($hostMatches.Count -ne 1) {
        throw ('Expected one DB_HOST with value db in ' + $file.Path + '. No files were changed; review this custom manifest.')
    }
    $portNames = [regex]::Matches($text, '(?m)^[ ]*- name: DB_PORT[ \t]*\r?$')
    if ($portNames.Count -eq 0) {
        $match = $hostMatches[0]
        $indent = $match.Groups['indent'].Value
        $replacement = $match.Value.TrimEnd([char[]]"`r") + $newline + $indent + '- name: DB_PORT' + $newline + $indent + "  value: '3306'"
        if ($match.Value.EndsWith("`r")) { $replacement += "`r" }
        $text = $text.Remove($match.Index, $match.Length).Insert($match.Index, $replacement)
    } elseif ($portNames.Count -ne 1 -or -not [regex]::IsMatch($text, '(?m)^[ ]*- name: DB_PORT[ \t]*\r?\n[ ]*value:[ \t]*[''"]?3306[''"]?[ \t]*\r?$')) {
        throw ('Review DB_PORT in ' + $file.Path + ': this cluster database uses numeric port 3306. No files were changed.')
    }
    # DNS names such as db remain available when automatic service links are disabled.
    $prefix = ' ' * $file.PodIndent
    $linksPattern = '(?m)^' + $prefix + 'enableServiceLinks:[^\r\n]*'
    $links = [regex]::Matches($text, $linksPattern)
    if ($links.Count -gt 1) { throw ('Duplicate enableServiceLinks in ' + $file.Path + '. No files were changed.') }
    if ($links.Count -eq 1) {
        $text = [regex]::Replace($text, $linksPattern, ($prefix + 'enableServiceLinks: false'))
    } else {
        $restart = [regex]::Matches($text, ('(?m)^' + $prefix + 'restartPolicy:[^\r\n]*'))
        if ($restart.Count -ne 1) { throw ('Expected one pod restartPolicy in ' + $file.Path + '. No files were changed.') }
        $text = $text.Insert($restart[0].Index, ($prefix + 'enableServiceLinks: false' + $newline))
    }
    if ($text -ne $original) { $changes += @{ Path = $path; Relative = $file.Path; Text = $text } }
}
if ($changes.Count -eq 0) {
    Write-Host 'DB_PORT fix already present: both manifests use 3306 and disable automatic service links.'
    return
}
if (-not $BackupRoot) {
    $documents = [Environment]::GetFolderPath([Environment+SpecialFolder]::MyDocuments)
    if (-not $documents) { $documents = [IO.Path]::GetTempPath() }
    $BackupRoot = Join-Path $documents 'EasyCampusStay_Backups'
}
$backup = Join-Path $BackupRoot ('DbPort_' + (Get-Date -Format 'yyyyMMdd_HHmmss') + '_' + [Guid]::NewGuid().ToString('N').Substring(0,8))
foreach ($change in $changes) {
    $backupPath = Join-Path $backup $change.Relative
    New-Item -ItemType Directory -Force (Split-Path -Parent $backupPath) | Out-Null
    Copy-Item -LiteralPath $change.Path -Destination $backupPath
}
$encoding = New-Object System.Text.UTF8Encoding($false)
foreach ($change in $changes) {
    [IO.File]::WriteAllText($change.Path, $change.Text, $encoding)
    Write-Host ('Fixed ' + $change.Relative + ': DB_PORT=3306; enableServiceLinks=false')
}
Write-Host ('Original manifest backups: ' + $backup)

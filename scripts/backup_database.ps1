# =============================================================================
# PropVal AI — Automated Database Backup Script (PowerShell / Windows)
# Usage:
#   .\scripts\backup_database.ps1 [-BackupDir ".\backups"]
# =============================================================================
param (
    [string]$BackupDir = ".\backups"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -Path $BackupDir)) {
    New-Item -ItemType Directory -Path $BackupDir | Out-Null
}

$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$BackupFile = Join-Path $BackupDir "propval_db_$Timestamp.db"
$MetaFile = Join-Path $BackupDir "propval_db_$Timestamp.meta.json"

Write-Host "[INFO] Starting PropVal AI database backup at $(Get-Date)..." -ForegroundColor Cyan

if (Test-Path ".\propval.db") {
    Copy-Item -Path ".\propval.db" -Destination $BackupFile -Force
    $Hash = (Get-FileHash -Path $BackupFile -Algorithm SHA256).Hash
    $Size = (Get-Item -Path $BackupFile).Length

    $Metadata = @{
        timestamp = $Timestamp
        file = $BackupFile
        sha256 = $Hash
        size_bytes = $Size
        backup_status = "SUCCESS"
    } | ConvertTo-Json

    Set-Content -Path $MetaFile -Value $Metadata -Encoding UTF8
    Write-Host "[INFO] Database backup completed: $BackupFile (Size: $Size bytes, SHA256: $Hash)" -ForegroundColor Green
} else {
    Write-Error "[ERROR] No database found at .\propval.db"
}


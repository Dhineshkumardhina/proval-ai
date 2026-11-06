# =============================================================================
# PropVal AI — Database Restoration Script (PowerShell / Windows)
# Usage:
#   .\scripts\restore_database.ps1 -BackupFile ".\backups\propval_db_YYYYMMDD_HHMMSS.db" [-TargetFile ".\propval_restored.db"]
# =============================================================================
param (
    [Parameter(Mandatory=$true)]
    [string]$BackupFile,
    [string]$TargetFile = ".\propval_restored.db"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -Path $BackupFile)) {
    Write-Error "[ERROR] Backup file not found: $BackupFile"
}

Write-Host "[INFO] Restoring database from $BackupFile to $TargetFile..." -ForegroundColor Cyan
Copy-Item -Path $BackupFile -Destination $TargetFile -Force

$SourceHash = (Get-FileHash -Path $BackupFile -Algorithm SHA256).Hash
$TargetHash = (Get-FileHash -Path $TargetFile -Algorithm SHA256).Hash

if ($SourceHash -eq $TargetHash) {
    Write-Host "[INFO] Database restored successfully and verified (SHA256 Match: $TargetHash)" -ForegroundColor Green
} else {
    Write-Error "[CRITICAL] Checksum mismatch during restoration! Backup: $SourceHash, Target: $TargetHash"
}


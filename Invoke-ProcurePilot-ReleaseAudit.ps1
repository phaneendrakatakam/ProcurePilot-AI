param([string]$ProjectRoot = (Get-Location).Path)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $ProjectRoot
$reports = Join-Path $env:TEMP 'ProcurePilot-ReleaseAudit'
New-Item -ItemType Directory -Path $reports -Force | Out-Null
$report = Join-Path $reports ("audit-" + (Get-Date -Format 'yyyyMMdd-HHmmss') + '.txt')
$results = New-Object System.Collections.Generic.List[string]
function Add-Result([string]$status,[string]$description) {
  $line = "[$status] $description"
  Write-Host $line
  $script:results.Add($line)
}
function Run-Check([string]$title,[string[]]$arguments) {
  Write-Host "`n--- $title ---"
  & python @arguments
  if ($LASTEXITCODE -eq 0) { Add-Result 'PASS' $title } else { Add-Result 'FAIL' "$title (exit $LASTEXITCODE)" }
}
Write-Host 'ProcurePilot local release audit (no database writes, no file deletion)'
if (!(Test-Path 'app/main.py') -or !(Test-Path 'alembic.ini')) { throw 'Run in the actual project root (where app/main.py and alembic.ini exist).' }
if (!(Test-Path '.venv/Scripts/python.exe')) { throw 'Missing .venv/Scripts/python.exe; check project directory.' }
$pythonPath = (Resolve-Path '.venv/Scripts/python.exe').Path
function Run-Python([string]$title,[string[]]$arguments) {
  Write-Host "`n--- $title ---"
  & $pythonPath @arguments
  if ($LASTEXITCODE -eq 0) { Add-Result 'PASS' $title } else { Add-Result 'FAIL' "$title (exit $LASTEXITCODE)" }
}
$ignoredFolders = @('.venv','venv','.git','.pytest_cache','__pycache__','node_modules')
$files = Get-ChildItem -File -Recurse -Force | Where-Object {
  $relative = $_.FullName.Substring((Get-Location).Path.Length).TrimStart('\','/')
  -not ($ignoredFolders | Where-Object { ($relative -split '[\\/]') -contains $_ })
}
$badFiles = @($files | Where-Object {
  $_.Name -match '(?i)^\.env($|\.)' -and $_.Name -ne '.env.example' -or
  $_.Extension -match '(?i)^\.(pem|p12|pfx|key)$' -or
  $_.Name -match '(?i)(recovery.?codes|service.?account.*\.json|access.?key.*\.csv|credentials.*\.json)'
})
if ($badFiles.Count) { Add-Result 'WARN' "Private/local filenames present: $($badFiles.Count). These must NOT be published." }
else { Add-Result 'PASS' 'No private filenames detected outside excluded virtual environment' }
if (Test-Path '.git') {
  $tracked = @(& git ls-files)
  $riskyTracked = @($tracked | Where-Object { $_ -match '(^|/)(\.env($|\.)|.*\.(pem|p12|pfx|key)$|.*recovery.*code.*|.*credential.*\.json)' -and $_ -notmatch '(^|/)\.env\.example$' })
  if ($riskyTracked.Count) { Add-Result 'FAIL' "Potential secret files tracked by Git: $($riskyTracked.Count). Review locally; do not publish." }
  else { Add-Result 'PASS' 'No suspicious credential filenames tracked by Git' }
} else { Add-Result 'INFO' 'No .git directory in this working copy; remote/repository history not audited' }
$env:PYTHONUTF8='1'
Run-Python 'Full pytest suite' @('-m','pytest','-q')
Run-Python 'Alembic current revision' @('-m','alembic','current')
Run-Python 'Alembic migration heads' @('-m','alembic','heads')
Run-Python 'Historical E2E read-only verification' @('-m','scripts.verify_e2e_repairs')
Run-Python 'Python installed dependency consistency' @('-m','pip','check')
$results | Set-Content -LiteralPath $report -Encoding UTF8
Write-Host "`nAudit summary saved to: $report"
Write-Host 'Do not share .env, database connection strings, tokens, or passwords.'
if (@($results | Where-Object { $_ -match '^\[FAIL\]' }).Count) { exit 1 }

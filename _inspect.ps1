$ErrorActionPreference = 'Continue'
$r = Join-Path $PSScriptRoot '..'
Set-Location -LiteralPath $r
$out = New-Object System.Collections.Generic.List[string]

$out.Add('===ROOT_FILES===')
Get-ChildItem -LiteralPath $r -Force -File -Name | ForEach-Object { $out.Add($_) }
$out.Add('')
$out.Add('===ROOT_DIRS===')
Get-ChildItem -LiteralPath $r -Force -Directory -Name | ForEach-Object { $out.Add($_) }
$out.Add('')
$out.Add('===GIT_LS===')
git ls-files | ForEach-Object { $out.Add($_) }
$out.Add('')
$out.Add('===GIT_STATUS===')
git status 2>&1 | ForEach-Object { $out.Add($_) }
$out.Add('')
$out.Add('===GIT_LOG===')
git log --oneline -15 2>&1 | ForEach-Object { $out.Add($_) }

$out | Set-Content -LiteralPath (Join-Path $r '_inspect_out.txt') -Encoding utf8
Write-Output ('WROTE ' + $out.Count + ' lines')

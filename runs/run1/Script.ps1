# Diagnostics for AiEC-Bot
$ErrorActionPreference = 'Continue'
$script:root = Split-Path -Parent $PSScriptRoot   # parent of runs\run1 => AiEC-Bot
$out = New-Object System.Collections.Generic.List[string]
function L($s){ [void]$out.Add($s) }

L '===ROOT===' + $script:root
L ''
L '===ROOT_ITEM_NAMES==='
Get-ChildItem -LiteralPath $script:root -Force | Select-Object @{n='Name';e={$_.Name}}, @{n='Type';e={ if ($_.PSIsContainer){'DIR'}else{'FILE'} }} | ForEach-Object { L ("{0}`t{1}" -f $_.Name, $_.Type) }
L ''
L '===ENV:KNOWN_FILES==='
# Look for common bot files
foreach($f in @('app.py','requirements.txt','admin.html','index.html','Procfile','render.yaml','run_app.sh','config.example.py','.gitignore','LICENSE')){
  $p = Join-Path $script:root $f
  if(Test-Path -LiteralPath $p){ L ("{0}  ->  {1} bytes" -f $f, (Get-Item -LiteralPath $p).Length) } else { L ($f + '  ->  MISSING') }
}
L ''
$out | Set-Content -LiteralPath (Join-Path $script:root '_diag_out.txt') -Encoding utf8
Write-Output ("WROTE " + $out.Count + " lines to " + (Join-Path $script:root '_diag_out.txt'))
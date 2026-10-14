cd D:\Apps\DevOps\Github\monkeymatters
foreach ($f in @('2026-10-01','2026-09-30','2026-09-29','2026-09-28')) {
  Write-Output "--- $f ---"
  $j = Get-Content "data\daily\$f.json" -Raw | ConvertFrom-Json
  $j.schwab_futures | ConvertTo-Json -Depth 3
}

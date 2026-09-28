try {
  $r1 = Invoke-WebRequest -Uri "https://joselitosering.github.io/monkeymatters/mmm-daily/2026-09-02.html" -UseBasicParsing
  Write-Output ("DIRECT URL: HTTP " + $r1.StatusCode + " bytes " + $r1.Content.Length)
} catch { Write-Output ("DIRECT URL FAILED: " + $_.Exception.Message) }

try {
  $r2 = Invoke-WebRequest -Uri "https://joselitosering.github.io/monkeymatters/" -UseBasicParsing
  Write-Output ("HOMEPAGE: HTTP " + $r2.StatusCode + " bytes " + $r2.Content.Length)
  Write-Output ("Homepage links to 2026-09-02: " + ($r2.Content -match "2026-09-02"))
  Write-Output ("Homepage links to 2026-09-01: " + ($r2.Content -match "2026-09-01"))
  $latest = [regex]::Matches($r2.Content, 'mmm-daily/(\d{4}-\d{2}-\d{2})\.html') | ForEach-Object { $_.Groups[1].Value } | Sort-Object -Descending | Select-Object -First 3
  Write-Output ("Latest dated links found on homepage: " + ($latest -join ", "))
} catch { Write-Output ("HOMEPAGE FAILED: " + $_.Exception.Message) }

Write-Output "--- remote repo state (GitHub, not local working tree) ---"
gh api repos/joselitosering/monkeymatters/contents/shadowmonkey/index.html --jq ".sha" 2>&1

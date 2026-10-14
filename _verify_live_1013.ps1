Set-Location "D:\Apps\DevOps\Github\monkeymatters"
gh api repos/joselitosering/monkeymatters/contents/shadowmonkey/mmm-daily/2026-10-13.html -H "Accept: application/vnd.github.raw" | Out-File -FilePath "_live_page_1013.html" -Encoding utf8

$content = Get-Content "_live_page_1013.html" -Raw
$strayTokens = [regex]::Matches($content, '\{\{[A-Z0-9_]+\}\}') | ForEach-Object { $_.Value } | Sort-Object -Unique
$pending = $content -match "PENDING"

"=== STRAY TOKENS (raw, includes comment-only legend matches) ===" | Out-File -FilePath "_verify_1013_out.txt" -Encoding utf8
$strayTokens | Out-File -FilePath "_verify_1013_out.txt" -Append -Encoding utf8
"=== CONTAINS PENDING ===" | Out-File -FilePath "_verify_1013_out.txt" -Append -Encoding utf8
$pending | Out-File -FilePath "_verify_1013_out.txt" -Append -Encoding utf8

"=== SPOT CHECKS ===" | Out-File -FilePath "_verify_1013_out.txt" -Append -Encoding utf8
"chip-sector: " + ($content -match "chip-sector") | Out-File -FilePath "_verify_1013_out.txt" -Append -Encoding utf8
"Kospi: " + ($content -match "Kospi") | Out-File -FilePath "_verify_1013_out.txt" -Append -Encoding utf8
"JPM: " + ($content -match "JPM") | Out-File -FilePath "_verify_1013_out.txt" -Append -Encoding utf8
"BTC trade idea ticker present: " + ($content -match "BTC") | Out-File -FilePath "_verify_1013_out.txt" -Append -Encoding utf8
"ETH trade idea ticker present: " + ($content -match "ETH") | Out-File -FilePath "_verify_1013_out.txt" -Append -Encoding utf8

Get-Content "_verify_1013_out.txt"

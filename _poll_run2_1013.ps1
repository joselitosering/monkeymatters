Set-Location "D:\Apps\DevOps\Github\monkeymatters"
$deadline = (Get-Date).AddSeconds(100)
do {
    Start-Sleep -Seconds 8
    $j = gh run view 38409563362 --repo joselitosering/monkeymatters --json status,conclusion | ConvertFrom-Json
} while ($j.status -ne 'completed' -and (Get-Date) -lt $deadline)
$j | ConvertTo-Json | Out-File -FilePath "_run2_status_1013.txt" -Encoding utf8
Get-Content "_run2_status_1013.txt"

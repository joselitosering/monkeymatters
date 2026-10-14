Set-Location "D:\Apps\DevOps\Github\monkeymatters"
gh workflow run mmm-daily.yml -f force=true --repo joselitosering/monkeymatters
Start-Sleep -Seconds 8
gh run list --workflow=mmm-daily.yml --repo joselitosering/monkeymatters --limit 3 --json databaseId,status,conclusion,createdAt,event | Out-File -FilePath "_trigger_1013_out.txt" -Encoding utf8
Get-Content "_trigger_1013_out.txt"

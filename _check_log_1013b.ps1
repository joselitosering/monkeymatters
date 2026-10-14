Set-Location "D:\Apps\DevOps\Github\monkeymatters"
gh run view 38409563362 --repo joselitosering/monkeymatters --log | Out-File -FilePath "_run_log_1013b.txt" -Encoding utf8
Select-String -Path "_run_log_1013b.txt" -Pattern "WARN|ERROR|Traceback" | Out-File -FilePath "_run_log_1013b_grep.txt" -Encoding utf8
Get-Content "_run_log_1013b_grep.txt"

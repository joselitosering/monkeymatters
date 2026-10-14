cd D:\Apps\DevOps\Github\monkeymatters
gh run view 37689461623 --repo joselitosering/monkeymatters --log 2>&1 | Select-String -Pattern 'Fetch data' | Out-File -Encoding utf8 _log2_full.txt
Get-Content _log2_full.txt

cd D:\Apps\DevOps\Github\monkeymatters
gh run view 37689461623 --repo joselitosering/monkeymatters --log 2>&1 | Select-String -Pattern 'schwab|ES|NQ|error|Traceback|WARN|400|401|403' | Select-Object -First 100 | Out-File -Encoding utf8 _log1_grep.txt
Get-Content _log1_grep.txt

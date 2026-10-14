cd D:\Apps\DevOps\Github\monkeymatters
gh run view 37691848020 --repo joselitosering/monkeymatters --log 2>&1 | Select-String -Pattern 'WARN|Traceback|ERROR|SANITIZE FAILED|Commit and push' | Out-File -Encoding utf8 _log3_grep.txt
Get-Content _log3_grep.txt

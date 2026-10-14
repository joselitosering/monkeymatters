$matches = Select-String -Path 'D:\Apps\DevOps\Github\monkeymatters\template\mmm_template.html' -Pattern '\{\{[A-Z0-9_]+\}\}' -AllMatches
$all = foreach ($m in $matches) { $m.Matches.Value }
$all | Sort-Object -Unique | Out-File -FilePath 'D:\Apps\DevOps\Github\monkeymatters\_tokens_out.txt' -Encoding utf8

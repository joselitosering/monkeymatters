gh api repos/joselitosering/monkeymatters/contents/.github/workflows/mmm-daily.yml -H "Accept: application/vnd.github.raw"
Write-Output "=== last 8 scheduled runs: created_at vs actual run start ==="
gh run list --repo joselitosering/monkeymatters --workflow mmm-daily.yml --limit 8 --json createdAt,event,status,conclusion --jq ".[] | [.createdAt,.event,.status,.conclusion] | @tsv"

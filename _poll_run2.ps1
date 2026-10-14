$runId = 37691848020
for ($i=0; $i -lt 15; $i++) {
  Start-Sleep -Seconds 10
  $status = gh run view $runId --repo joselitosering/monkeymatters --json status,conclusion | ConvertFrom-Json
  Write-Output "$($status.status) / $($status.conclusion)"
  if ($status.status -eq 'completed') { break }
}

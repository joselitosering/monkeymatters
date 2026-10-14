param([string]$RunId)
cd D:\Apps\DevOps\Github\monkeymatters
$status = "queued"
while ($status -ne "completed") {
    Start-Sleep -Seconds 15
    $json = gh run view $RunId --repo joselitosering/monkeymatters --json status,conclusion
    $obj = $json | ConvertFrom-Json
    $status = $obj.status
    Write-Output "$($obj.status) $($obj.conclusion)"
}

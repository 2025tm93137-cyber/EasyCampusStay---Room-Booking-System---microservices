$ErrorActionPreference = 'Stop'
Set-Location (Join-Path $PSScriptRoot '../..')
$folder='evidence/assignment2/minikube'
New-Item -ItemType Directory -Force $folder | Out-Null
kubectl --context=minikube -n easy-campus-stay scale deployment/inventory --replicas=3
if ($LASTEXITCODE -ne 0) { throw 'Scaling failed.' }
kubectl --context=minikube -n easy-campus-stay rollout status deployment/inventory --timeout=180s
if ($LASTEXITCODE -ne 0) { throw 'Three replicas did not become ready.' }
$raw=kubectl --context=minikube -n easy-campus-stay get pods -l app=inventory -o json
if ($LASTEXITCODE -ne 0) { throw 'Could not inspect pods.' }
$before=$raw | ConvertFrom-Json
$raw | Set-Content "$folder/inventory-before.json"
$pod=$before.items[0].metadata.name
$uid=$before.items[0].metadata.uid
Write-Host "Deleting one Inventory pod: $pod"
kubectl --context=minikube -n easy-campus-stay delete pod $pod
if ($LASTEXITCODE -ne 0) { throw 'Pod deletion failed.' }
kubectl --context=minikube -n easy-campus-stay rollout status deployment/inventory --timeout=180s
if ($LASTEXITCODE -ne 0) { throw 'Recovery did not complete.' }
$raw=kubectl --context=minikube -n easy-campus-stay get pods -l app=inventory -o json
if ($LASTEXITCODE -ne 0) { throw 'Could not inspect recovered pods.' }
$after=$raw | ConvertFrom-Json
$raw | Set-Content "$folder/inventory-after.json"
$ready=@($after.items | Where-Object { $_.status.phase -eq 'Running' -and @($_.status.conditions | Where-Object { $_.type -eq 'Ready' -and $_.status -eq 'True' }).Count -gt 0 })
if ($ready.Count -ne 3 -or @($after.items | Where-Object { $_.metadata.uid -eq $uid }).Count -gt 0) { throw 'Expected three ready replacement replicas; inspect saved evidence.' }
[ordered]@{timestamp=(Get-Date -Format o);deletedPod=$pod;deletedUid=$uid;readyReplicas=$ready.Count;result='PASS'} | ConvertTo-Json | Set-Content "$folder/self-healing.json"
Write-Host 'Three ready replicas restored. Now verify a booking through the Kubernetes UI and run Check-Minikube.ps1.'

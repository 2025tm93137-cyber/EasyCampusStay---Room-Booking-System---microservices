$ErrorActionPreference = 'Stop'
Set-Location (Join-Path $PSScriptRoot '../..')
New-Item -ItemType Directory -Force evidence/assignment2/minikube | Out-Null
Get-Date -Format o | Set-Content evidence/assignment2/minikube/timestamp.txt
kubectl version --client | Out-File evidence/assignment2/minikube/kubectl-version.txt
minikube version | Out-File evidence/assignment2/minikube/minikube-version.txt
kubectl --context=minikube -n easy-campus-stay get pods,jobs,services,pvc -o wide | Out-File evidence/assignment2/minikube/resources.txt
kubectl --context=minikube -n easy-campus-stay logs deployment/reservation --tail=150 | Out-File evidence/assignment2/minikube/reservation-logs.txt
kubectl --context=minikube -n easy-campus-stay exec deployment-tools -- python deploy/run_checks.py 2>&1 | Tee-Object evidence/assignment2/minikube/workflow-console.txt
$result=$LASTEXITCODE
kubectl --context=minikube -n easy-campus-stay cp deployment-tools:/app/evidence/. evidence/assignment2/minikube/
if ($LASTEXITCODE -ne 0) { throw 'Evidence copy failed.' }
if ($result -ne 0) { throw 'Workflow checks failed; inspect saved output.' }

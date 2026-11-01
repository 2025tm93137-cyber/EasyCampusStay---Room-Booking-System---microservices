$ErrorActionPreference = 'Stop'
Set-Location (Join-Path $PSScriptRoot '../..')
function Run-Native { param([string]$Exe,[string[]]$Arguments)
    & $Exe @Arguments
    if ($LASTEXITCODE -ne 0) { throw "$Exe failed; stop and inspect output." }
}
if (!(Test-Path '.env')) { throw 'Create private .env first: py -3.12 deploy/configure.py' }
Run-Native -Exe docker -Arguments @('compose','--profile','test','build')
Run-Native -Exe docker -Arguments @('pull','mariadb:10.11')
Run-Native -Exe minikube -Arguments @('start','--driver=docker','--cpus=2','--memory=3072')
foreach ($name in @('inventory','reservation','payment','notification','ui','provision','tools')) {
    Run-Native -Exe minikube -Arguments @('image','load',"easystay/${name}:assignment2")
}
Run-Native -Exe minikube -Arguments @('image','load','mariadb:10.11')
Run-Native -Exe kubectl -Arguments @('--context=minikube','apply','-f','k8s/00-namespace.yml')
# Generate Secret JSON in memory only; never save credentials as a manifest.
$secret = & kubectl --context=minikube -n easy-campus-stay create secret generic easystay-secrets --from-env-file=.env --dry-run=client -o json
if ($LASTEXITCODE -ne 0) { throw 'Could not generate Secret.' }
$secret | & kubectl --context=minikube apply -f - | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'Could not apply Secret.' }
Run-Native -Exe kubectl -Arguments @('--context=minikube','apply','-f','k8s/10-database.yml')
Run-Native -Exe kubectl -Arguments @('--context=minikube','-n','easy-campus-stay','rollout','status','deployment/db','--timeout=300s')
& kubectl --context=minikube -n easy-campus-stay delete job db-init --ignore-not-found | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'Could not reset completed provisioning job.' }
Run-Native -Exe kubectl -Arguments @('--context=minikube','apply','-f','k8s/20-provision.yml')
Run-Native -Exe kubectl -Arguments @('--context=minikube','-n','easy-campus-stay','wait','--for=condition=complete','job/db-init','--timeout=300s')
Run-Native -Exe kubectl -Arguments @('--context=minikube','apply','-f','k8s/30-application.yml')
foreach ($name in @('inventory','payment','notification','reservation','ui')) {
    Run-Native -Exe kubectl -Arguments @('--context=minikube','-n','easy-campus-stay','rollout','status',"deployment/$name",'--timeout=240s')
}
Run-Native -Exe kubectl -Arguments @('--context=minikube','apply','-f','k8s/40-tools.yml')
Run-Native -Exe kubectl -Arguments @('--context=minikube','-n','easy-campus-stay','wait','--for=condition=Ready','pod/deployment-tools','--timeout=180s')
Write-Host 'Ready. In another terminal run the port-forward command from the guide.'

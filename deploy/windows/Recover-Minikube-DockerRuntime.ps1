# Windows PowerShell 5.1 / PowerShell 7. Run from the existing Assignment 2 project.
[CmdletBinding()]
param(
    [ValidatePattern('^[a-z][a-z0-9-]*$')]
    [string]$ProfileName = 'easystay-docker',
    [ValidateRange(2048,32768)]
    [int]$MemoryMB = 3072
)

$ErrorActionPreference = 'Stop'
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$Namespace = 'easy-campus-stay'
$ImageTag = 'a2-recovery-' + (Get-Date -Format 'yyyyMMddHHmmss')
$EvidenceDirectory = Join-Path $ProjectRoot 'evidence/assignment2/docker-runtime-recovery'
$Phase = 'preflight'

function Invoke-Checked {
    param([string]$Program, [string[]]$Arguments)
    & $Program @Arguments | Out-Host
    $nativeExitCode = $LASTEXITCODE
    if ($nativeExitCode -ne 0) {
        throw ('{0} exited with code {1}. Recovery stopped during {2}.' -f $Program,$nativeExitCode,$script:Phase)
    }
}

function Read-Checked {
    param([string]$Program, [string[]]$Arguments)
    $nativeOutput = & $Program @Arguments
    $nativeExitCode = $LASTEXITCODE
    if ($nativeExitCode -ne 0) {
        throw ('{0} exited with code {1}. Recovery stopped during {2}.' -f $Program,$nativeExitCode,$script:Phase)
    }
    return (($nativeOutput | Out-String).Trim())
}

function Invoke-Kube {
    param([string[]]$Arguments)
    Invoke-Checked -Program 'kubectl' -Arguments (@("--context=$ProfileName",'-n',$Namespace) + $Arguments)
}

function Read-KubeJson {
    param([string[]]$Arguments)
    $text = Read-Checked -Program 'kubectl' -Arguments (@("--context=$ProfileName",'-n',$Namespace) + $Arguments + @('-o','json'))
    return ($text | ConvertFrom-Json)
}

function Apply-Document {
    param([string]$Document)
    $applyArguments = @("--context=$ProfileName",'-n',$Namespace,'apply','-f','-')
    $Document | & kubectl @applyArguments | Out-Host
    if ($LASTEXITCODE -ne 0) { throw 'Applying a Kubernetes document failed. Recovery stopped.' }
}

function Read-Manifest {
    param([string]$RelativePath)
    $text = Get-Content (Join-Path $ProjectRoot $RelativePath) -Raw
    $text = $text -replace ':assignment2\b',(':' + $ImageTag)
    # These images are loaded locally. Missing images must fail locally rather than pull from Docker Hub.
    return $text.Replace('imagePullPolicy: IfNotPresent','imagePullPolicy: Never')
}

function Show-Diagnostics {
    param([string]$JobName = '')
    # Best effort only; the original exception is rethrown by the caller.
    $savedPreference = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    $diagnosticArguments = @("--context=$ProfileName",'-n',$Namespace,'get','pods,jobs','-o','wide')
    & kubectl @diagnosticArguments
    $diagnosticArguments = @("--context=$ProfileName",'-n',$Namespace,'get','events','--sort-by=.metadata.creationTimestamp')
    & kubectl @diagnosticArguments
    if ($JobName) {
        $diagnosticArguments = @("--context=$ProfileName",'-n',$Namespace,'logs',"job/$JobName",'--all-containers=true','--tail=100','--pod-running-timeout=10s')
        & kubectl @diagnosticArguments
    }
    $ErrorActionPreference = $savedPreference
}

function Wait-SetupJob {
    $deadline = (Get-Date).AddSeconds(600)
    while ((Get-Date) -lt $deadline) {
        $job = Read-KubeJson -Arguments @('get','job','db-init')
        $complete = @($job.status.conditions | Where-Object { $_.type -eq 'Complete' -and $_.status -eq 'True' })
        if ($complete.Count -gt 0) { return }
        $failed = @($job.status.conditions | Where-Object { $_.type -eq 'Failed' -and $_.status -eq 'True' })
        if ($failed.Count -gt 0) { throw ('db-init failed: ' + $failed[0].reason + '. ' + $failed[0].message) }
        $pods = Read-KubeJson -Arguments @('get','pods','-l','job-name=db-init')
        foreach ($pod in $pods.items) {
            foreach ($container in @($pod.status.containerStatuses)) {
                $reason = $container.state.waiting.reason
                if ($reason -in @('ErrImageNeverPull','ErrImagePull','ImagePullBackOff','CreateContainerConfigError','InvalidImageName')) {
                    throw ('db-init cannot start: ' + $reason + '. ' + $container.state.waiting.message)
                }
            }
        }
        Start-Sleep -Seconds 2
    }
    throw 'db-init did not complete within 600 seconds.'
}

Push-Location $ProjectRoot
try {
    if ($ProfileName -eq 'minikube') { throw 'Use a separate profile name. The existing minikube profile must be retained.' }
    foreach ($command in @('docker','minikube','kubectl')) {
        if (-not (Get-Command $command -ErrorAction SilentlyContinue)) { throw "$command is not installed or is missing from PATH." }
    }
    $dockerfiles = [ordered]@{
        provision = 'deploy/provision/Dockerfile'
        inventory = 'services/inventory/Dockerfile'
        reservation = 'services/reservation/Dockerfile'
        payment = 'services/payment/Dockerfile'
        notification = 'services/notification/Dockerfile'
        ui = 'ui/Dockerfile'
        tools = 'deploy/tools/Dockerfile'
    }
    $required = @('.env','k8s/00-namespace.yml','k8s/10-database.yml','k8s/20-provision.yml','k8s/30-application.yml','k8s/40-tools.yml','deploy/windows/Fix-Kubernetes-DbPort.ps1') + @($dockerfiles.Values)
    foreach ($relativePath in $required) {
        if (-not (Test-Path (Join-Path $ProjectRoot $relativePath))) { throw "Missing project file: $relativePath. Extract this kit into your existing Assignment 2 project." }
    }
    $Phase = 'repair explicit database ports in the setup and tools manifests'
    & (Join-Path $ProjectRoot 'deploy/windows/Fix-Kubernetes-DbPort.ps1') -ProjectRoot $ProjectRoot
    $privateEnvText = Get-Content '.env' -Raw
    foreach ($key in @('MARIADB_ROOT_PASSWORD','INVENTORY_DB_PASSWORD','RESERVATION_DB_PASSWORD','PAYMENT_DB_PASSWORD','NOTIFICATION_DB_PASSWORD')) {
        if ($privateEnvText -notmatch ('(?m)^' + $key + '=.+$')) { throw "The existing .env is missing $key. Review it locally; do not print or share its contents." }
    }
    $privateEnvText = $null
    if ((Read-Checked -Program 'docker' -Arguments @('info','--format','{{.OSType}}')) -ne 'linux') {
        throw 'Docker Desktop must be running with Linux containers.'
    }
    Invoke-Checked -Program 'docker' -Arguments @('buildx','version')
    New-Item -ItemType Directory -Force $EvidenceDirectory | Out-Null

    $Phase = 'stop the old profile while retaining its storage'
    Write-Host "[1/7] Retaining the old minikube profile and its volume. New profile: $ProfileName"
    $profiles = (Read-Checked -Program 'minikube' -Arguments @('profile','list','-o','json')) | ConvertFrom-Json
    if (@($profiles.valid | Where-Object { $_.Name -eq 'minikube' }).Count -gt 0) {
        Invoke-Checked -Program 'minikube' -Arguments @('-p','minikube','stop')
    }

    $Phase = 'start and verify the separate Docker runtime profile'
    Write-Host '[2/7] Starting a separate cluster with the Docker container runtime.'
    Invoke-Checked -Program 'minikube' -Arguments @('-p',$ProfileName,'start','--driver=docker','--container-runtime=docker','--cpus=2',"--memory=$MemoryMB")
    $nodes = Read-KubeJson -Arguments @('get','nodes')
    $node = $nodes.items[0]
    $runtime = $node.status.nodeInfo.containerRuntimeVersion
    $architecture = $node.status.nodeInfo.architecture
    if ($runtime -notlike 'docker://*') { throw "Unexpected runtime $runtime. This recovery requires a separate Docker runtime profile." }
    if ($architecture -notin @('amd64','arm64')) { throw "Unsupported architecture: $architecture" }
    $targetPlatform = 'linux/' + $architecture
    Invoke-Kube -Arguments @('apply','-f','k8s/00-namespace.yml')

    $Phase = 'verify official Python before creating or updating databases'
    Write-Host '[3/7] Checking official Python inside the new cluster.'
    Invoke-Kube -Arguments @('delete','pod','easystay-runtime-check','--ignore-not-found','--wait=true')
    Invoke-Kube -Arguments @('run','easystay-runtime-check','--image=docker.io/library/python:3.12-slim-bookworm','--restart=Never','--image-pull-policy=Always','--command','--','/usr/local/bin/python','--version')
    try {
        Invoke-Kube -Arguments @('wait','--for=jsonpath={.status.phase}=Succeeded','pod/easystay-runtime-check','--timeout=180s')
    } catch {
        Show-Diagnostics
        $logArguments = @("--context=$ProfileName",'-n',$Namespace,'logs','pod/easystay-runtime-check','--pod-running-timeout=10s')
        & kubectl @logArguments
        throw
    }
    Invoke-Kube -Arguments @('logs','pod/easystay-runtime-check')

    $Phase = 'build and load the seven project images'
    Write-Host "[4/7] Building seven project images for $targetPlatform. Every failed build stops recovery."
    foreach ($entry in $dockerfiles.GetEnumerator()) {
        $image = 'easystay/' + $entry.Key + ':' + $ImageTag
        Write-Host ('Building ' + $entry.Key)
        Invoke-Checked -Program 'docker' -Arguments @('buildx','build','--platform',$targetPlatform,'--pull','--provenance=false','--sbom=false','--load','-f',$entry.Value,'-t',$image,'.')
        if ($entry.Key -eq 'provision') {
            Invoke-Checked -Program 'docker' -Arguments @('run','--rm','--pull=never','--platform',$targetPlatform,'--entrypoint','/usr/local/bin/python',$image,'--version')
        }
        Invoke-Checked -Program 'minikube' -Arguments @('-p',$ProfileName,'image','load','--daemon','--overwrite=true',$image)
    }

    $Phase = 'provision databases using the retained local .env'
    Write-Host '[5/7] Using the existing private .env; the first deployment in this separate profile has fresh databases.'
    $secretJson = Read-Checked -Program 'kubectl' -Arguments @("--context=$ProfileName",'-n',$Namespace,'create','secret','generic','easystay-secrets','--from-env-file=.env','--dry-run=client','-o','json')
    Apply-Document -Document $secretJson
    $secretJson = $null
    Invoke-Kube -Arguments @('apply','-f','k8s/10-database.yml')
    Invoke-Kube -Arguments @('rollout','status','deployment/db','--timeout=300s')
    Invoke-Kube -Arguments @('delete','job','db-init','--ignore-not-found','--wait=true')
    $jobYaml = Read-Manifest -RelativePath 'k8s/20-provision.yml'
    $jobYaml = $jobYaml.Replace('restartPolicy: OnFailure','restartPolicy: Never').Replace('backoffLimit: 4','backoffLimit: 0').Replace('activeDeadlineSeconds: 300','activeDeadlineSeconds: 600')
    Apply-Document -Document $jobYaml
    try { Wait-SetupJob } catch { Show-Diagnostics -JobName 'db-init'; throw }
    Invoke-Kube -Arguments @('logs','job/db-init')

    $Phase = 'start the five application deployments'
    Write-Host '[6/7] Starting Inventory, Payment, Notification, Reservation and the browser UI.'
    Apply-Document -Document (Read-Manifest -RelativePath 'k8s/30-application.yml')
    foreach ($serviceName in @('inventory','payment','notification','reservation','ui')) {
        try { Invoke-Kube -Arguments @('rollout','status',('deployment/' + $serviceName),'--timeout=300s') }
        catch { Show-Diagnostics; throw }
    }

    $Phase = 'start tools and record readiness'
    Write-Host '[7/7] Starting the tools pod and recording actual cluster readiness.'
    Invoke-Kube -Arguments @('delete','pod','deployment-tools','--ignore-not-found','--wait=true')
    Apply-Document -Document (Read-Manifest -RelativePath 'k8s/40-tools.yml')
    Invoke-Kube -Arguments @('wait','--for=condition=Ready','pod/deployment-tools','--timeout=180s')
    Invoke-Kube -Arguments @('get','pods,jobs,services,pvc','-o','wide')
    $summary = [ordered]@{
        timestamp_utc = (Get-Date).ToUniversalTime().ToString('o')
        result = 'DEPLOYMENT_READY'
        business_workflow_checks = 'NOT_RUN; use Check-Minikube-DockerRuntime.ps1'
        profile = $ProfileName
        host_os = [Environment]::OSVersion.VersionString
        powershell_version = $PSVersionTable.PSVersion.ToString()
        node_runtime = $runtime
        node_architecture = $architecture
        project_image_tag = $ImageTag
        database_port_fix = 'Explicit DB_PORT=3306; service links disabled for setup and tools'
        old_profile = 'minikube; retained, not deleted'
    }
    $summary | ConvertTo-Json -Depth 10 | Set-Content (Join-Path $EvidenceDirectory 'deployment_summary.json') -Encoding UTF8
    Write-Host 'DEPLOYMENT READY. Business workflow checks have not run yet.'
    Write-Host ('Next: powershell -NoProfile -ExecutionPolicy Bypass -File deploy\windows\Check-Minikube-DockerRuntime.ps1 -ProfileName ' + $ProfileName)
    Write-Host ('Browser terminal: kubectl --context=' + $ProfileName + ' -n easy-campus-stay port-forward svc/ui 8181:8080 --address=127.0.0.1')
    Write-Host 'Then open http://127.0.0.1:8181/ and keep the port-forward terminal open.'
} catch {
    Write-Host ('RECOVERY STOPPED during: ' + $Phase) -ForegroundColor Red
    throw
} finally {
    Pop-Location
}

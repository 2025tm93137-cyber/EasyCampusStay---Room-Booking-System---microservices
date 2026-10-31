# Run only after Recover-Minikube-DockerRuntime.ps1 reports DEPLOYMENT READY.
[CmdletBinding()]
param(
    [ValidatePattern('^[a-z][a-z0-9-]*$')]
    [string]$ProfileName = 'easystay-docker'
)
$ErrorActionPreference = 'Stop'
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$Namespace = 'easy-campus-stay'
$RunName = Get-Date -Format 'yyyyMMdd_HHmmss'
$RelativeEvidence = 'evidence/assignment2/kubernetes-docker-runtime/' + $RunName

function Invoke-Checked {
    param([string]$Program,[string[]]$Arguments)
    & $Program @Arguments | Out-Host
    if ($LASTEXITCODE -ne 0) { throw "$Program failed. Inspect the output above." }
}

Push-Location $ProjectRoot
try {
    if ($ProfileName -eq 'minikube') { throw 'Use the recovered profile, normally easystay-docker.' }
    New-Item -ItemType Directory -Force $RelativeEvidence | Out-Null
    $nodeArguments = @("--context=$ProfileName",'get','nodes','-o','json')
    $nodeOutput = & kubectl @nodeArguments
    if ($LASTEXITCODE -ne 0) { throw 'Cannot read the recovered cluster.' }
    $nodes = ($nodeOutput | Out-String) | ConvertFrom-Json
    $runtime = $nodes.items[0].status.nodeInfo.containerRuntimeVersion
    if ($runtime -notlike 'docker://*') { throw "Expected the recovery Docker runtime; found $runtime." }
    $toolsArguments = @("--context=$ProfileName",'-n',$Namespace,'get','pod','deployment-tools','--ignore-not-found','-o','name')
    $toolsPod = & kubectl @toolsArguments
    if ($LASTEXITCODE -ne 0) { throw 'Cannot inspect deployment-tools. Check access to the recovered cluster.' }
    if (-not (($toolsPod | Out-String).Trim())) {
        throw 'Recovery is incomplete: deployment-tools has not been created. Run the updated Recover-Minikube-DockerRuntime.ps1 and wait for DEPLOYMENT READY before running these checks.'
    }
    Invoke-Checked -Program 'kubectl' -Arguments @("--context=$ProfileName",'-n',$Namespace,'wait','--for=condition=Ready','pod/deployment-tools','--timeout=60s')
    foreach ($serviceName in @('db','inventory','reservation','payment','notification','ui')) {
        Invoke-Checked -Program 'kubectl' -Arguments @("--context=$ProfileName",'-n',$Namespace,'rollout','status',('deployment/' + $serviceName),'--timeout=120s')
    }
    $nodeOutput | Set-Content (Join-Path $RelativeEvidence 'nodes.json') -Encoding UTF8
    Get-Date -Format o | Set-Content (Join-Path $RelativeEvidence 'timestamp.txt') -Encoding UTF8
    $snapshotArguments = @("--context=$ProfileName",'-n',$Namespace,'get','pods,jobs,services,pvc','-o','wide')
    & kubectl @snapshotArguments | Out-File (Join-Path $RelativeEvidence 'resources.txt') -Encoding UTF8
    if ($LASTEXITCODE -ne 0) { throw 'Resource snapshot failed.' }
    $logArguments = @("--context=$ProfileName",'-n',$Namespace,'logs','deployment/reservation','--tail=150')
    & kubectl @logArguments | Out-File (Join-Path $RelativeEvidence 'reservation-logs.txt') -Encoding UTF8
    if ($LASTEXITCODE -ne 0) { throw 'Reservation log capture failed.' }

    Write-Host 'Running the supplied main flow, concurrency, idempotency, saga and database-isolation checks.'
    # On Windows PowerShell 5.1, redirected native stderr can otherwise stop before artifacts are copied.
    $savedPreference = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        $workflowArguments = @("--context=$ProfileName",'-n',$Namespace,'exec','deployment-tools','--','python','deploy/run_checks.py')
        & kubectl @workflowArguments 2>&1 | Tee-Object -FilePath (Join-Path $RelativeEvidence 'workflow-console.txt')
        $workflowExitCode = $LASTEXITCODE
    } finally { $ErrorActionPreference = $savedPreference }

    $artifactFolder = $RelativeEvidence + '/artifacts'
    New-Item -ItemType Directory -Force $artifactFolder | Out-Null
    # A relative destination avoids interpreting a Windows drive colon as a remote pod separator.
    Invoke-Checked -Program 'kubectl' -Arguments @("--context=$ProfileName",'-n',$Namespace,'cp','deployment-tools:/app/evidence/.',$artifactFolder)
    if ($workflowExitCode -ne 0) { throw "Workflow checks failed. Actual artifacts are in $RelativeEvidence" }

    $summaryPath = Join-Path $artifactFolder 'assignment2/workflow_summary.json'
    if (-not (Test-Path $summaryPath)) { throw 'The expected workflow_summary.json was not copied. Do not claim PASS.' }
    $workflow = Get-Content $summaryPath -Raw | ConvertFrom-Json
    if ($workflow.result -ne 'PASS' -or $workflow.peer_database_attempts_denied -ne 12) {
        throw 'The copied workflow summary does not record PASS and 12 denied peer-database checks.'
    }
    $hostRecord = [ordered]@{
        timestamp_utc = (Get-Date).ToUniversalTime().ToString('o')
        profile = $ProfileName
        node_runtime = $runtime
        host_os = [Environment]::OSVersion.VersionString
        native_windows_host = ([Environment]::OSVersion.Platform -eq [PlatformID]::Win32NT)
        container_checks_platform = $workflow.platform
        note = 'The host can be Windows while the application and test containers report Linux.'
        workflow_exit_code = $workflowExitCode
        result = $workflow.result
    }
    $hostRecord | ConvertTo-Json -Depth 10 | Set-Content (Join-Path $RelativeEvidence 'host_and_container.json') -Encoding UTF8
    Write-Host ('WORKFLOW CHECKS PASSED. Inspect actual evidence at ' + $RelativeEvidence)
} finally { Pop-Location }

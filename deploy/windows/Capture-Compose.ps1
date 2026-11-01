$ErrorActionPreference = 'Stop'
Set-Location (Join-Path $PSScriptRoot '../..')
New-Item -ItemType Directory -Force evidence/assignment2/compose | Out-Null
Get-Date -Format o | Set-Content evidence/assignment2/compose/timestamp.txt
docker version | Out-File evidence/assignment2/compose/docker-version.txt
docker compose version | Out-File evidence/assignment2/compose/compose-version.txt
docker compose ps -a | Out-File evidence/assignment2/compose/containers.txt
docker compose images | Out-File evidence/assignment2/compose/images.txt
docker compose logs --no-color --tail=250 | Out-File evidence/assignment2/compose/logs.txt
# Avoid docker inspect environment output and resolved docker compose config: both expose passwords.
docker image inspect easystay/inventory:assignment2 easystay/reservation:assignment2 easystay/payment:assignment2 easystay/notification:assignment2 easystay/ui:assignment2 easystay/provision:assignment2 easystay/tools:assignment2 mariadb:10.11 --format '{{.RepoTags}} {{.Id}} {{.RepoDigests}}' | Out-File evidence/assignment2/compose/image-identities.txt
Write-Host 'Saved deployment evidence. Review before committing; no environment dump was requested.'

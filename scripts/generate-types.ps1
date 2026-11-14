#!/usr/bin/env pwsh
# generate-types.ps1 — Re-generate OpenAPI spec and TypeScript types.
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$root = Split-Path -Parent (Split-Path -Parent $PSCommandPath)

# 1. Export OpenAPI JSON
Write-Host "Exporting OpenAPI spec..."
Push-Location "$root\backend"
python scripts\export_openapi.py
Pop-Location

# 2. Generate TypeScript types
Write-Host "Generating TypeScript types..."
Push-Location "$root\frontend"
npx openapi-typescript ..\openapi.json -o src\types\api.ts
Pop-Location

Write-Host "Done."

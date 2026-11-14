#!/usr/bin/env bash
# generate-types.sh — Re-generate OpenAPI spec and TypeScript types.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# 1. Export OpenAPI JSON
echo "Exporting OpenAPI spec..."
cd "$ROOT/backend"
python scripts/export_openapi.py

# 2. Generate TypeScript types
echo "Generating TypeScript types..."
cd "$ROOT/frontend"
npx openapi-typescript ../openapi.json -o src/types/api.ts

echo "Done."

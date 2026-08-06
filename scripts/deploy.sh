#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/cdk"

echo "Installing CDK dependencies…"
npm install

echo "Bootstrapping CDK (if needed)…"
npx cdk bootstrap

echo "Deploying Splice stack…"
npx cdk deploy --require-approval never

echo ""
echo "Deployment complete. Check stack outputs for ApiUrl and WebUrl."

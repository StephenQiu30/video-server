#!/usr/bin/env bash
set -euo pipefail

required_files=(
  "README.md"
  "AGENTS.md"
  "AGENTS.local.md"
  ".github/pull_request_template.md"
  ".github/workflows/ci.yml"
  "Dockerfile"
  "docker-compose.yml"
  "docker-compose.prod.yml"
  "docs/README.md"
  "docs/TEMPLATE.md"
  "docs/00-文档总览/00-文档索引.md"
  "docs/02-产品需求/03-MVP需求清单.md"
  "docs/03-架构设计/01-总体架构方案.md"
  "docs/04-执行计划/01-阶段执行计划.md"
  "docs/05-测试验收/01-验收标准.md"
  "docs/06-运维合规/01-部署与运行规划.md"
  "openspec/config.yaml"
  "package.json"
)

for file in "${required_files[@]}"; do
  test -f "$file"
done

grep -q "Test-First PR 提交规范" AGENTS.md
grep -q "test:" AGENTS.md
grep -q "impl:" AGENTS.md
grep -q "Test-first Evidence" .github/pull_request_template.md

for script in scripts/*.sh; do
  bash -n "$script"
done

PYTHON_BIN="${PYTHON_BIN:-python3}"

if "$PYTHON_BIN" scripts/validate_prod_env.py .env.production.example >/tmp/video-prod-env-validation.out 2>&1; then
  echo ".env.production.example must keep unsafe placeholders and fail production validation" >&2
  exit 1
fi
grep -q "replace placeholder values" /tmp/video-prod-env-validation.out

git diff --check

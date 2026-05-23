#!/usr/bin/env bash
set -euo pipefail

required_files=(
  "README.md"
  "AGENTS.md"
  "AGENTS.local.md"
  ".github/pull_request_template.md"
  ".github/workflows/ci.yml"
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

git diff --check

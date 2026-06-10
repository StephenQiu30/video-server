#!/usr/bin/env bash
set -euo pipefail

required_files=(
  "README.md"
  "CLAUDE.md"
  "CLAUDE.local.md"
  "WORKFLOW.md"
  "openspec/config.yaml"
  "openspec/specs/agent-governance/spec.md"
  ".env.example"
  ".env.production.example"
  ".claude/agents/pm.md"
  ".claude/agents/explorer.md"
  ".claude/agents/builder.md"
  ".claude/agents/tester.md"
  ".claude/agents/reporter.md"
  ".claude/skills/agent-browser/SKILL.md"
  ".claude/skills/openspec-new-change/SKILL.md"
  ".claude/skills/openspec-apply-change/SKILL.md"
  ".claude/skills/openspec-verify-change/SKILL.md"
  ".claude/skills/harness-local-server/SKILL.md"
  ".claude/skills/harness-playwright-evidence/SKILL.md"
  ".claude/skills/harness-linear-loop/SKILL.md"
  ".claude/skills/harness-quality-gate/SKILL.md"
  ".claude/skills/using-superpowers/SKILL.md"
  ".claude/skills/test-driven-development/SKILL.md"
  ".claude/skills/executing-plans/SKILL.md"
  ".claude/skills/verification-before-completion/SKILL.md"
  "scripts/vendor-superpowers-skills.sh"
  ".claude/skills/debug/SKILL.md"
  ".claude/skills/commit/SKILL.md"
  ".claude/skills/pull/SKILL.md"
  ".claude/skills/push/SKILL.md"
  ".claude/skills/land/SKILL.md"
  ".claude/skills/land/land_watch.py"
  ".claude/skills/linear/SKILL.md"
  ".github/pull_request_template.md"
  ".github/workflows/ci.yml"
  "Dockerfile"
  "docker-compose.yml"
  "docker-compose.prod.yml"
  "docs/README.md"
  "docs/TEMPLATE.md"
  "docs/prd/README.md"
  "docs/plans/README.md"
  "docs/design/README.md"
  "docs/acceptance/README.md"
  "docs/operations/README.md"
  "docs/prd/001-链接解析与平台识别.md"
  "docs/prd/002-分辨率选择与无水印优先.md"
  "docs/prd/003-下载任务与产物归档.md"
  "docs/prd/004-AI摘要与PDF报告.md"
  "docs/prd/005-自部署Cookie与合规治理.md"
  "docs/plans/001-万能视频下载器MVP执行计划.md"
  "docs/plans/001-01-平台画像扩展计划.md"
  "docs/plans/001-02-解析安全与错误语义计划.md"
  "docs/plans/002-01-清晰度预设计划.md"
  "docs/plans/002-02-高级格式与水印提示计划.md"
  "docs/plans/003-01-下载主链路计划.md"
  "docs/plans/003-02-字幕封面元数据归档计划.md"
  "docs/plans/004-01-AI摘要与思维导图计划.md"
  "docs/plans/004-02-PDF报告导出计划.md"
  "docs/plans/005-01-自部署浏览器Cookie配置计划.md"
  "docs/plans/005-02-限流配额与合规负向计划.md"
  "docs/acceptance/001-万能视频下载器MVP测试计划.md"
  "docs/operations/001-OpenAPI契约与前端生成协作.md"
  "package.json"
)

for file in "${required_files[@]}"; do
  test -f "$file"
done

test ! -f AGENTS.md
test ! -f CURSOR.md
test ! -d .codex
test ! -d .cursor

grep -q "Commit 规范" CLAUDE.md
grep -q "Agent Review" CLAUDE.md
grep -q "test:" CLAUDE.md
grep -q "impl:" CLAUDE.md
grep -q "openspec/specs/" CLAUDE.md
grep -q ".claude/agents" CLAUDE.local.md

grep -q "tracker:" WORKFLOW.md
grep -q "kind: linear" WORKFLOW.md
grep -q "project_slug" WORKFLOW.md
grep -q "## Claude Workpad" WORKFLOW.md
grep -q "command: claude" WORKFLOW.md
grep -q "Agent Review" WORKFLOW.md
grep -q "Human Review" WORKFLOW.md
grep -q "harness-quality-gate" WORKFLOW.md
grep -q "superpowers" WORKFLOW.md
grep -q ".claude/skills/land/SKILL.md" WORKFLOW.md
grep -q "Test-first Evidence" .github/pull_request_template.md

test ! -d .agents
test ! -f skills-lock.json

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

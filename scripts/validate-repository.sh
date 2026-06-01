#!/usr/bin/env bash
set -euo pipefail

required_files=(
  "README.md"
  "AGENTS.md"
  "AGENTS.local.md"
  "CLAUDE.md"
  "CLAUDE.local.md"
  "CURSOR.md"
  "CURSOR.local.md"
  "WORKFLOW.md"
  ".codex/agents/pm.toml"
  ".codex/agents/explorer.toml"
  ".codex/agents/builder.toml"
  ".codex/agents/tester.toml"
  ".codex/agents/reporter.toml"
  ".codex/skills/project-planning/SKILL.md"
  ".codex/skills/mvp-implementation/SKILL.md"
  ".codex/skills/release-acceptance/SKILL.md"
  ".claude/agents/pm.md"
  ".claude/agents/explorer.md"
  ".claude/agents/builder.md"
  ".claude/agents/tester.md"
  ".claude/agents/reporter.md"
  ".claude/skills/commit/SKILL.md"
  ".claude/skills/pull/SKILL.md"
  ".claude/skills/push/SKILL.md"
  ".claude/skills/land/SKILL.md"
  ".claude/skills/land/land_watch.py"
  ".claude/skills/linear/SKILL.md"
  ".claude/skills/harness-local-server/SKILL.md"
  ".claude/skills/harness-playwright-evidence/SKILL.md"
  ".claude/skills/harness-linear-loop/SKILL.md"
  ".cursor/agents/pm.md"
  ".cursor/agents/explorer.md"
  ".cursor/agents/builder.md"
  ".cursor/agents/tester.md"
  ".cursor/agents/reporter.md"
  ".cursor/skills/commit/SKILL.md"
  ".cursor/skills/pull/SKILL.md"
  ".cursor/skills/push/SKILL.md"
  ".cursor/skills/land/SKILL.md"
  ".cursor/skills/land/land_watch.py"
  ".cursor/skills/linear/SKILL.md"
  ".cursor/skills/harness-local-server/SKILL.md"
  ".cursor/skills/harness-playwright-evidence/SKILL.md"
  ".cursor/skills/harness-linear-loop/SKILL.md"
  ".cursor/rules/multi-agent.mdc"
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

grep -q "Test-First PR 提交规范" CLAUDE.md
grep -q "test:" CLAUDE.md
grep -q "impl:" CLAUDE.md
grep -q "Test-First PR 提交规范" CURSOR.md
grep -q "test:" CURSOR.md
grep -q "impl:" CURSOR.md
grep -q "Test-First PR 提交规范" AGENTS.md
grep -q ".codex/agents" AGENTS.md
grep -q ".claude/agents" CLAUDE.md
grep -q ".cursor/agents" CURSOR.md
grep -q ".cursor/skills" CURSOR.md
grep -q "Cursor" .cursor/rules/multi-agent.mdc
grep -q "Codex" .cursor/rules/multi-agent.mdc
grep -q "Claude" .cursor/rules/multi-agent.mdc
grep -q "TDD Rules" .cursor/rules/multi-agent.mdc
grep -q "Cursor Execution Flow" .cursor/rules/multi-agent.mdc
grep -q "Docs Rules" .cursor/rules/multi-agent.mdc
grep -q "Git and PR Rules" .cursor/rules/multi-agent.mdc
grep -q "Do not remove Codex, Claude, or Cursor entrypoints" .cursor/rules/multi-agent.mdc
grep -q ".cursor/agents/" .cursor/rules/multi-agent.mdc
grep -q ".cursor/skills/" .cursor/rules/multi-agent.mdc
grep -q "## Claude Workpad" WORKFLOW.md
grep -q ".claude/skills/land/SKILL.md" WORKFLOW.md
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

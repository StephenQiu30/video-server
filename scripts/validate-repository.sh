#!/usr/bin/env bash
set -euo pipefail

required_files=(
  "README.md"
  "CLAUDE.md"
  "CLAUDE.local.md"
  "WORKFLOW.md"
  "openspec/config.yaml"
  "openspec/specs/agent-governance/spec.md"
  "openspec/specs/backend-layer-boundaries/spec.md"
  "openspec/specs/minio-artifact-archive/spec.md"
  "openspec/specs/presigned-download-delivery/spec.md"
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
  ".claude/skills/linear-create-task/SKILL.md"
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
  "docs/prd/01-解析入口与URL安全.md"
  "docs/prd/02-平台识别与平台画像.md"
  "docs/prd/03-异步下载任务主链路.md"
  "docs/prd/04-MinIO产物归档与下载交付.md"
  "docs/prd/05-自部署运行与环境复用.md"
  "docs/prd/08-后端工程规范与架构治理.md"
  "docs/design/01-个人自部署万能视频下载器技术设计.md"
  "docs/plans/01-URL协议与地址安全计划.md"
  "docs/plans/02-错误语义与日志脱敏计划.md"
  "docs/plans/03-平台画像注册与识别计划.md"
  "docs/plans/04-创建任务与状态查询计划.md"
  "docs/plans/05-Worker下载执行与失败分类计划.md"
  "docs/plans/06-取消重试与事件流计划.md"
  "docs/plans/07-MinIO对象归档计划.md"
  "docs/plans/08-预签名下载与过期清理计划.md"
  "docs/plans/09-本机开发与依赖复用计划.md"
  "docs/plans/10-DockerCompose部署与健康检查计划.md"
  "docs/plans/13-后端工程规范与架构治理计划.md"
  "docs/acceptance/01-个人自部署万能视频下载器验收方案.md"
  "docs/operations/01-个人自部署万能视频下载器运行与部署.md"
  "docs/operations/02-OpenAPI契约与前端生成协作.md"
  "package.json"
)

for file in "${required_files[@]}"; do
  test -f "$file"
done

test ! -f AGENTS.md
test ! -f CURSOR.md
test ! -d .codex
test ! -d .cursor

grep -q "video-server" README.md
grep -q "docs/" README.md
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

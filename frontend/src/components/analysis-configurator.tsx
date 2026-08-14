'use client';

import { ArrowCounterClockwise, ShieldCheck } from '@phosphor-icons/react';
import { useEffect, useMemo, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Field, FieldDescription, FieldLabel } from '@/components/ui/field';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Spinner } from '@/components/ui/spinner';
import { Textarea } from '@/components/ui/textarea';
import { useAnalysisSkills } from '@/hooks/useAnalysisSkills';
import type { CreateAnalysisInput, OutputLanguage } from '@/types/video';

const MAX_PROMPT_LENGTH = 4_000;

export default function AnalysisConfigurator({
  busy,
  onStart,
}: {
  busy: boolean;
  onStart: (input: CreateAnalysisInput) => void;
}) {
  const catalog = useAnalysisSkills('video');
  const [skillId, setSkillId] = useState('');
  const [language, setLanguage] = useState<OutputLanguage>('zh-CN');
  const [prompt, setPrompt] = useState('');
  const selected = useMemo(
    () => catalog.skills.find((skill) => skill.id === skillId),
    [catalog.skills, skillId],
  );

  useEffect(() => {
    const first = catalog.skills[0];
    if (!skillId && first) {
      setSkillId(first.id);
      setPrompt(first.default_prompt);
    }
  }, [catalog.skills, skillId]);

  function changeSkill(value: string) {
    const next = catalog.skills.find((skill) => skill.id === value);
    if (!next) return;
    setPrompt((current) =>
      !selected || current === selected.default_prompt
        ? next.default_prompt
        : current,
    );
    setSkillId(next.id);
  }

  return (
    <div className="mt-10 w-full">
      <div className="grid gap-5 sm:grid-cols-2">
        <Field>
          <FieldLabel htmlFor="analysis-skill">分析 Skill</FieldLabel>
          <Select
            disabled={catalog.loading || catalog.skills.length === 0}
            onValueChange={changeSkill}
            value={skillId}
          >
            <SelectTrigger className="w-full" id="analysis-skill">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {catalog.skills.map((skill) => (
                <SelectItem key={skill.id} value={skill.id}>
                  {skill.display_name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <FieldDescription>
            {catalog.error ? (
              <>
                Skill 清单加载失败。{' '}
                <Button
                  className="h-auto p-0 align-baseline text-inherit"
                  onClick={() => void catalog.retry()}
                  variant="link"
                  type="button"
                >
                  重试
                </Button>
              </>
            ) : (
              (selected?.description ?? '正在加载可用的分析 Skill…')
            )}
          </FieldDescription>
        </Field>
        <Field>
          <FieldLabel htmlFor="analysis-language">输出语言</FieldLabel>
          <Select
            onValueChange={(value) => setLanguage(value as OutputLanguage)}
            value={language}
          >
            <SelectTrigger className="w-full" id="analysis-language">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="zh-CN">简体中文</SelectItem>
              <SelectItem value="en-US">English</SelectItem>
            </SelectContent>
          </Select>
          <FieldDescription>
            分析结构保持一致，仅改变模型输出文字。
          </FieldDescription>
        </Field>
      </div>

      <Field className="mt-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <FieldLabel htmlFor="analysis-prompt">分析提示词</FieldLabel>
          <Button
            disabled={!selected || prompt === selected.default_prompt}
            onClick={() => selected && setPrompt(selected.default_prompt)}
            size="sm"
            type="button"
            variant="ghost"
          >
            <ArrowCounterClockwise />
            恢复模式默认值
          </Button>
        </div>
        <Textarea
          id="analysis-prompt"
          maxLength={MAX_PROMPT_LENGTH}
          onChange={(event) => setPrompt(event.target.value)}
          rows={5}
          value={prompt}
        />
        <div className="flex items-start justify-between gap-4 text-sm text-muted-foreground">
          <span>
            可修改或清空分析重点；工具权限、安全边界与结果结构不可修改。
          </span>
          <span aria-live="polite" className="shrink-0 tabular-nums">
            {prompt.length}/{MAX_PROMPT_LENGTH}
          </span>
        </div>
      </Field>

      <div className="mt-7 flex flex-col-reverse items-start justify-between gap-5 sm:flex-row sm:items-center">
        <p className="flex max-w-2xl items-start gap-2 text-sm leading-6 text-muted-foreground">
          <ShieldCheck className="mt-1 shrink-0 text-success" />
          完整视频文件会交给本机 Agent；Agent
          必须覆盖全片时间轴并自主复核分镜边界与高光，不以预先抽取的固定帧集替代分析。Agent
          实际查看的画面帧、任务指令和必要上下文会发送到所选云端模型处理；应用不会把原始视频容器直接上传给模型服务。
        </p>
        <Button
          className="w-full shrink-0 sm:w-auto"
          disabled={busy || !selected}
          onClick={() => {
            if (!selected) return;
            onStart({
              skill_id: selected.id,
              output_language: language,
              custom_prompt: prompt.trim() || null,
            });
          }}
          size="lg"
        >
          {busy ? <Spinner aria-hidden /> : null}
          开始 AI 分析
        </Button>
      </div>
    </div>
  );
}

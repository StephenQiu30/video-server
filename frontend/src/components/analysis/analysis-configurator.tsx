'use client';

import { ArrowCounterClockwise } from '@phosphor-icons/react';
import { useEffect, useMemo, useState } from 'react';
import { Button } from '@/components/ui/button';
import {
  Field,
  FieldDescription,
  FieldGroup,
  FieldLabel,
} from '@/components/ui/field';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import { useAnalysisSkills } from '@/hooks/useAnalysisSkills';
import type { CreateAnalysisInput, OutputLanguage } from '@/types/video';
import { AnalysisExecutionNotice } from './analysis-execution-notice';

const MAX_PROMPT_LENGTH = 4_000;

export default function AnalysisConfigurator({
  busy,
  inputKind = 'video',
  onStart,
}: {
  busy: boolean;
  inputKind?: API.AnalysisInputKind;
  onStart: (input: CreateAnalysisInput) => void;
}) {
  const catalog = useAnalysisSkills(inputKind);
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

  function startAnalysis() {
    if (!selected) return;
    onStart({
      skill_id: selected.id,
      output_language: language,
      custom_prompt: prompt.trim() || null,
    });
  }

  return (
    <FieldGroup className="mt-10 gap-6">
      <FieldGroup className="grid gap-5 sm:grid-cols-2">
        <Field>
          <FieldLabel htmlFor={controlId(inputKind, 'skill')}>
            {inputKind === 'screenplay' ? '剧本 Skill' : '分析 Skill'}
          </FieldLabel>
          <Select
            disabled={catalog.loading || catalog.skills.length === 0}
            onValueChange={changeSkill}
            value={skillId}
          >
            <SelectTrigger
              className="w-full"
              id={controlId(inputKind, 'skill')}
            >
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
          <FieldLabel htmlFor={controlId(inputKind, 'language')}>
            输出语言
          </FieldLabel>
          <Select
            onValueChange={(value) => setLanguage(value as OutputLanguage)}
            value={language}
          >
            <SelectTrigger
              className="w-full"
              id={controlId(inputKind, 'language')}
            >
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="zh-CN">简体中文</SelectItem>
              <SelectItem value="en-US">English</SelectItem>
            </SelectContent>
          </Select>
          <FieldDescription>
            {inputKind === 'screenplay'
              ? '与原文语言相同表示润色，不同表示跨语言改写。'
              : '分析结构保持一致，仅改变模型输出文字。'}
          </FieldDescription>
        </Field>
      </FieldGroup>

      <Field>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <FieldLabel htmlFor={controlId(inputKind, 'prompt')}>
            {inputKind === 'screenplay' ? '分析或改写要求' : '分析提示词'}
          </FieldLabel>
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
          id={controlId(inputKind, 'prompt')}
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

      <AnalysisExecutionNotice
        busy={busy}
        inputKind={inputKind}
        onStart={startAnalysis}
        resultContract={selected?.result_contract}
      />
    </FieldGroup>
  );
}

function controlId(inputKind: API.AnalysisInputKind, field: string) {
  return `${inputKind === 'video' ? 'analysis' : 'screenplay-analysis'}-${field}`;
}

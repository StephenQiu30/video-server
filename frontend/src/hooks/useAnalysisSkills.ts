import { useCallback, useEffect, useState } from 'react';

import { displayError } from '@/lib/request-error';
import { listAnalysisSkills } from '@/services/analysis';
import type { AnalysisSkill } from '@/types/video';

export function useAnalysisSkills(inputKind: API.AnalysisInputKind = 'video') {
  const [skills, setSkills] = useState<AnalysisSkill[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await listAnalysisSkills(inputKind);
      if (!Array.isArray(result)) {
        throw new Error('分析 Skill 清单格式无效');
      }
      setSkills(result);
    } catch (reason) {
      setError(displayError(reason));
    } finally {
      setLoading(false);
    }
  }, [inputKind]);

  useEffect(() => {
    void load();
  }, [load]);

  return { error, loading, retry: load, skills };
}

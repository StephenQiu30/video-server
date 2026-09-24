import { useQueryClient } from '@tanstack/react-query';
import { useRef, useState } from 'react';
import { createDownload } from '@/api/downloads';
import { getInspection } from '@/api/inspections';
import { useRequestScope } from '@/hooks/use-request-scope';
import { privateQueryKey } from '@/lib/query-keys';
import { displayError } from '@/lib/request-error';
import { createUuid } from '@/lib/uuid';

/** Every selected result is checked by the same API as its detail page. */
export function useBulkParseDownload() {
  const queries = useQueryClient();
  const scope = useRequestScope('bulk-parse-download');
  const keys = useRef(new Map<string, string>());
  const running = useRef(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const [progress, setProgress] = useState({ completed: 0, total: 0 });
  async function execute(items: API.ParseHistoryRecordResponse[]) {
    if (running.current) return [];
    running.current = true;
    setBusy(true);
    setMessage('');
    setProgress({ completed: 0, total: items.length });
    const request = scope.capture();
    const done: string[] = [];
    const failures: string[] = [];
    try {
      for (const item of items) {
        if (!request.current()) break;
        try {
          if (!item.inspection_id) {
            failures.push(`${item.title || '媒体解析'}：没有可用的解析结果`);
            continue;
          }
          const inspection = await getInspection({
            inspection_id: item.inspection_id,
          });
          if (!request.current()) break;
          if (
            inspection.access_decision !== 'downloadable' ||
            !inspection.formats.length
          ) {
            failures.push(
              `${item.title || '媒体解析'}：当前结果不可下载，请查看详情`,
            );
            continue;
          }
          if (Date.parse(inspection.expires_at) <= Date.now()) {
            failures.push(
              `${item.title || '媒体解析'}：解析结果已过期，请重新解析`,
            );
            continue;
          }
          const formatId = inspection.formats[0].id;
          const payload = `${inspection.id}:${formatId}`;
          const key = keys.current.get(payload) ?? createUuid();
          keys.current.set(payload, key);
          const job = await createDownload(
            { inspection_id: inspection.id, format_id: formatId },
            { headers: { 'Idempotency-Key': key } },
          );
          if (!request.current()) break;
          queries.setQueryData(privateQueryKey('download', job.id), job);
          done.push(item.id);
        } catch (error) {
          failures.push(`${item.title || '媒体解析'}：${displayError(error)}`);
        } finally {
          if (request.current())
            setProgress((value) => ({
              ...value,
              completed: value.completed + 1,
            }));
        }
      }
      if (request.current()) {
        void queries.invalidateQueries({
          queryKey: privateQueryKey('download-history'),
        });
        void queries.invalidateQueries({
          queryKey: privateQueryKey('intent-history'),
        });
        setMessage(
          `已创建 ${done.length} 项下载任务，失败 ${failures.length} 项。${done.length ? '可在下载记录查看进度。' : ''}${failures.join('；')}`,
        );
      }
      return done;
    } finally {
      running.current = false;
      if (request.current()) setBusy(false);
    }
  }
  return { busy, message, progress, execute };
}

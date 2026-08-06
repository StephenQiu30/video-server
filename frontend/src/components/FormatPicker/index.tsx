import { DownOutlined, UpOutlined } from '@ant-design/icons';
import { Button, Radio } from 'antd';
import { useState } from 'react';

import type { MediaFormat } from '@/types/video';

import styles from './index.module.css';

type FormatPickerProps = {
  formats: MediaFormat[];
  selectedId: string;
  onChange: (id: string) => void;
};

const fpsLabels = {
  fps_30: '≤ 30 FPS',
  fps_60: '≤ 60 FPS',
  above_60: '> 60 FPS',
};

export default function FormatPicker({
  formats,
  selectedId,
  onChange,
}: FormatPickerProps) {
  const [expanded, setExpanded] = useState(false);

  if (formats.length === 0) {
    return <p className={styles.empty}>没有可用的下载格式。</p>;
  }

  return (
    <fieldset className={styles.group}>
      <legend>选择下载格式</legend>
      <Radio.Group
        className={styles.options}
        onChange={(event) => onChange(event.target.value)}
        value={selectedId}
      >
        {(expanded ? formats : formats.slice(0, 4)).map((format, index) => {
          const { plan } = format;
          return (
            <Radio className={styles.option} key={format.id} value={format.id}>
              <span className={styles.copy}>
                <span className={styles.primary}>
                  {index === 0 ? (
                    <span className={styles.recommended}>推荐</span>
                  ) : null}
                  <strong>{format.display_name}</strong>
                </span>
                <span>
                  {plan.width} × {plan.height} · {fpsLabels[plan.fps_bucket]} ·{' '}
                  {plan.dynamic_range.toUpperCase()}
                </span>
                <span>
                  {plan.video_codec_family.toUpperCase()} +{' '}
                  {plan.audio_codec_family.toUpperCase()} ·{' '}
                  {plan.container_preference.toUpperCase()}
                </span>
              </span>
            </Radio>
          );
        })}
      </Radio.Group>
      {formats.length > 4 ? (
        <Button
          block
          className={styles.expand}
          icon={expanded ? <UpOutlined /> : <DownOutlined />}
          onClick={() => setExpanded((value) => !value)}
          type="text"
        >
          {expanded ? '收起格式' : `查看全部 ${formats.length} 个格式`}
        </Button>
      ) : null}
    </fieldset>
  );
}

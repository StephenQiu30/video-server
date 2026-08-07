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
      <legend>可用下载格式</legend>
      <div aria-hidden className={styles.tableHeader}>
        <span>清晰度</span>
        <span>格式</span>
        <span>视频编码</span>
        <span>音频</span>
      </div>
      <Radio.Group
        className={styles.options}
        onChange={(event) => onChange(event.target.value)}
        value={selectedId}
      >
        {(expanded ? formats : formats.slice(0, 4)).map((format) => {
          const { plan } = format;
          return (
            <Radio className={styles.option} key={format.id} value={format.id}>
              <span className={styles.copy}>
                <span className={styles.primary} data-label="格式">
                  <strong>{plan.height}P</strong>
                  <small>
                    {plan.width} × {plan.height} ·{' '}
                    {plan.dynamic_range.toUpperCase()}
                  </small>
                </span>
                <span data-label="格式">
                  <strong>{plan.container_preference.toUpperCase()}</strong>
                  <small>{format.display_name}</small>
                </span>
                <span data-label="视频编码">
                  <strong>{plan.video_codec_family.toUpperCase()}</strong>
                  <small>{fpsLabels[plan.fps_bucket]}</small>
                </span>
                <span data-label="音频">
                  <strong>{plan.audio_codec_family.toUpperCase()}</strong>
                  <small>{plan.audio_language ?? '默认音轨'}</small>
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

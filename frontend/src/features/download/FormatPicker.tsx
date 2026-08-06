import styles from './format-picker.module.css';
import type { MediaFormat } from './types';

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
  if (formats.length === 0) {
    return <p className={styles.empty}>没有可用的下载格式。</p>;
  }
  return (
    <fieldset className={styles.group}>
      <legend>选择下载格式</legend>
      <div className={styles.options}>
        {formats.map((format) => {
          const { plan } = format;
          return (
            <label className={styles.option} key={format.id}>
              <input
                checked={selectedId === format.id}
                name="download-format"
                onChange={() => onChange(format.id)}
                type="radio"
                value={format.id}
              />
              <span className={styles.copy}>
                <strong>{format.display_name}</strong>
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
            </label>
          );
        })}
      </div>
    </fieldset>
  );
}

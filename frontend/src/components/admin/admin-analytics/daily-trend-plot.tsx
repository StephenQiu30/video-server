import type { AdminDownloadAnalytics } from '@/services/analytics';

import { formatInteger, formatShortDate } from './analytics-format';

export type SeriesKey = 'total' | 'succeeded' | 'failed' | 'cancelled';
type DailyPoint = AdminDownloadAnalytics['daily'][number];

export const trendSeries: Array<{
  key: SeriesKey;
  label: string;
  stroke: string;
  dashArray?: string;
  width: number;
}> = [
  { key: 'total', label: '全部', stroke: 'stroke-foreground', width: 3 },
  {
    key: 'succeeded',
    label: '成功',
    stroke: 'stroke-success',
    dashArray: '9 4',
    width: 2.25,
  },
  {
    key: 'failed',
    label: '失败',
    stroke: 'stroke-destructive',
    dashArray: '2 5',
    width: 2.25,
  },
  {
    key: 'cancelled',
    label: '取消',
    stroke: 'stroke-muted-foreground',
    dashArray: '9 3 2 3',
    width: 2,
  },
];

type ChartFrame = {
  width: number;
  height: number;
  padding: { top: number; right: number; bottom: number; left: number };
};

export const mobileFrame: ChartFrame = {
  width: 360,
  height: 280,
  padding: { top: 18, right: 12, bottom: 36, left: 42 },
};

export const desktopFrame: ChartFrame = {
  width: 960,
  height: 360,
  padding: { top: 22, right: 20, bottom: 42, left: 50 },
};

export const tabletFrame: ChartFrame = {
  width: 720,
  height: 320,
  padding: { top: 20, right: 18, bottom: 40, left: 48 },
};

export function DailyTrendPlot({
  className,
  frame,
  maximum,
  points,
  visibleSeries,
}: {
  className: string;
  frame: ChartFrame;
  maximum: number;
  points: DailyPoint[];
  visibleSeries: SeriesKey[];
}) {
  const { width, height, padding } = frame;
  const plotWidth = width - padding.left - padding.right;
  const plotHeight = height - padding.top - padding.bottom;
  const x = (index: number) =>
    roundCoordinate(
      points.length === 1
        ? padding.left + plotWidth / 2
        : padding.left + (index / (points.length - 1)) * plotWidth,
    );
  const y = (value: number) =>
    roundCoordinate(padding.top + (1 - value / maximum) * plotHeight);
  const labelIndexes = Array.from(
    new Set([0, Math.floor((points.length - 1) / 2), points.length - 1]),
  );

  return (
    <svg
      aria-describedby="daily-trend-description"
      aria-label="每日下载任务折线趋势"
      className={className}
      role="img"
      viewBox={`0 0 ${width} ${height}`}
    >
      {gridLines(maximum).map((value) => {
        const lineY = y(value);
        return (
          <g key={value}>
            <line
              className="stroke-border"
              vectorEffect="non-scaling-stroke"
              x1={padding.left}
              x2={width - padding.right}
              y1={lineY}
              y2={lineY}
            />
            <text
              className="fill-muted-foreground text-[11px] tabular-nums"
              textAnchor="end"
              x={padding.left - 8}
              y={lineY + 4}
            >
              {formatInteger(value)}
            </text>
          </g>
        );
      })}
      {visibleSeries.includes('total') ? (
        <path
          className="fill-foreground/5"
          d={areaPath(points, 'total', x, y, padding.top + plotHeight)}
        />
      ) : null}
      {trendSeries
        .filter((item) => visibleSeries.includes(item.key))
        .map((item) => (
          <path
            className={item.stroke}
            d={linePath(points, item.key, x, y)}
            fill="none"
            key={item.key}
            strokeDasharray={item.dashArray}
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={item.width}
            vectorEffect="non-scaling-stroke"
          />
        ))}
      {points.length === 1
        ? trendSeries
            .filter((item) => visibleSeries.includes(item.key))
            .map((item) => (
              <circle
                className={`${item.stroke} fill-background`}
                cx={x(0)}
                cy={y(points[0][item.key])}
                key={item.key}
                r={3}
                strokeWidth={2}
                vectorEffect="non-scaling-stroke"
              />
            ))
        : trendSeries
            .filter((item) => visibleSeries.includes(item.key))
            .map((item) => {
              const index = points.length - 1;
              return (
                <circle
                  className={`${item.stroke} fill-surface`}
                  cx={x(index)}
                  cy={y(points[index][item.key])}
                  key={item.key}
                  r={2.75}
                  strokeWidth={2}
                  vectorEffect="non-scaling-stroke"
                />
              );
            })}
      {labelIndexes.map((index) => (
        <text
          className="fill-muted-foreground text-[11px]"
          key={points[index].date}
          textAnchor={labelAnchor(index, points.length)}
          x={x(index)}
          y={height - 9}
        >
          {formatShortDate(points[index].date)}
        </text>
      ))}
    </svg>
  );
}

function areaPath(
  points: DailyPoint[],
  key: SeriesKey,
  x: (index: number) => number,
  y: (value: number) => number,
  baseline: number,
): string {
  if (points.length === 0) return '';
  const line = linePath(points, key, x, y);
  const last = points.length - 1;
  return `${line} L ${x(last)} ${baseline} L ${x(0)} ${baseline} Z`;
}

function gridLines(maximum: number): number[] {
  return Array.from(
    new Set(
      [0, 0.25, 0.5, 0.75, 1].map((ratio) => Math.round(maximum * ratio)),
    ),
  );
}

function linePath(
  points: DailyPoint[],
  key: SeriesKey,
  x: (index: number) => number,
  y: (value: number) => number,
): string {
  return points
    .map(
      (point, index) =>
        `${index === 0 ? 'M' : 'L'} ${x(index)} ${y(point[key])}`,
    )
    .join(' ');
}

function labelAnchor(index: number, length: number) {
  if (index === 0) return 'start';
  if (index === length - 1) return 'end';
  return 'middle';
}

function roundCoordinate(value: number): number {
  return Number(value.toFixed(1));
}

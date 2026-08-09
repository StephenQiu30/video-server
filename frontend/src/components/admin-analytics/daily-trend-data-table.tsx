import type { AdminDownloadAnalytics } from '@/services/analytics';

type DailyPoint = AdminDownloadAnalytics['daily'][number];

export function DailyTrendDataTable({ points }: { points: DailyPoint[] }) {
  return (
    <table className="sr-only">
      <caption>每日下载趋势精确数据</caption>
      <thead>
        <tr>
          <th scope="col">日期</th>
          <th scope="col">全部</th>
          <th scope="col">成功</th>
          <th scope="col">失败</th>
          <th scope="col">取消</th>
        </tr>
      </thead>
      <tbody>
        {points.map((point) => (
          <tr key={point.date}>
            <th scope="row">{point.date}</th>
            <td>{point.total}</td>
            <td>{point.succeeded}</td>
            <td>{point.failed}</td>
            <td>{point.cancelled}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

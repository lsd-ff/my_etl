import { Progress } from 'antd';

export default function ProgressBar({ total, done }: { total?: number; done?: number }) {
  const totalValue = total || 0;
  const percent = totalValue ? Math.round(((done || 0) / totalValue) * 100) : 0;
  return <Progress percent={percent} size="small" />;
}


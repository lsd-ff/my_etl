import { Card, Empty } from 'antd';

export default function LogViewer({ log }: { log?: string }) {
  return (
    <Card title="处理日志">
      {log ? <pre className="pre-wrap mono">{log}</pre> : <Empty description="暂无日志" />}
    </Card>
  );
}


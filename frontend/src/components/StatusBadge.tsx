import { Tag } from 'antd';

const colorMap: Record<string, string> = {
  uploaded: 'default',
  chunking: 'processing',
  chunked: 'blue',
  qa_processing: 'processing',
  qa_done: 'green',
  qa_failed: 'orange',
  embedding_processing: 'processing',
  imported: 'green',
  failed: 'red'
};

export default function StatusBadge({ status }: { status?: string }) {
  const value = status || 'unknown';
  return <Tag color={colorMap[value] || 'default'}>{value}</Tag>;
}


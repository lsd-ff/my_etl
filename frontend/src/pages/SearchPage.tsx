import { Button, Input, InputNumber, Table, Typography, message } from 'antd';
import { useState } from 'react';
import { api } from '../api';

export default function SearchPage() {
  const [query, setQuery] = useState('');
  const [topK, setTopK] = useState(5);
  const [items, setItems] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  const search = async () => {
    setLoading(true);
    try {
      setItems(await api.search(query, topK));
    } catch (error) {
      message.error((error as Error).message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page">
      <Typography.Title level={3}>搜索测试</Typography.Title>
      <div className="toolbar">
        <Input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="输入问题" style={{ maxWidth: 520 }} />
        <InputNumber min={1} max={50} value={topK} onChange={(value) => setTopK(value || 5)} />
        <Button type="primary" loading={loading} onClick={search}>搜索</Button>
      </div>
      <Table
        rowKey={(row) => `${row.doc_id}-${row.chunk_id}-${row.question}`}
        dataSource={items}
        loading={loading}
        expandable={{ expandedRowRender: (record) => <div className="pre-wrap">{record.context}</div> }}
        columns={[
          { title: 'question', dataIndex: 'question', ellipsis: true },
          { title: 'answer', dataIndex: 'answer', ellipsis: true },
          { title: 'keywords', dataIndex: 'keywords', width: 220, ellipsis: true },
          { title: 'source', dataIndex: 'source', width: 180 },
          { title: 'page', dataIndex: 'page', width: 80 },
          { title: 'score', dataIndex: 'score', width: 100, render: (value) => Number(value).toFixed(3) }
        ]}
      />
    </div>
  );
}


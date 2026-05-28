import { Button, Input, Typography } from 'antd';
import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { api } from '../api';
import QATable from '../components/QATable';

export default function QAViewerPage() {
  const { docId = '' } = useParams();
  const [items, setItems] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [q, setQ] = useState('');
  const [loading, setLoading] = useState(false);

  const load = async (nextPage = page, nextSize = pageSize) => {
    setLoading(true);
    try {
      const result = await api.qaRecords(docId, nextPage, nextSize, q);
      setItems(result.items);
      setTotal(result.total);
      setPage(nextPage);
      setPageSize(nextSize);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(1, pageSize); }, [docId]);

  return (
    <div className="page">
      <div className="toolbar">
        <Typography.Title level={3} style={{ marginRight: 'auto' }}>QA Records</Typography.Title>
        <Input.Search placeholder="搜索 QA JSONL" value={q} onChange={(event) => setQ(event.target.value)} onSearch={() => load(1, pageSize)} style={{ width: 320 }} />
        <Button onClick={() => load()}>刷新</Button>
      </div>
      <QATable data={items} total={total} loading={loading} page={page} pageSize={pageSize} onChange={load} />
    </div>
  );
}


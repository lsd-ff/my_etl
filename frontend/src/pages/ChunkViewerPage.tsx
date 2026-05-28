import { Button, Typography } from 'antd';
import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { api } from '../api';
import ChunkTable from '../components/ChunkTable';

export default function ChunkViewerPage() {
  const { docId = '' } = useParams();
  const [items, setItems] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [loading, setLoading] = useState(false);

  const load = async (nextPage = page, nextSize = pageSize) => {
    setLoading(true);
    try {
      const result = await api.chunks(docId, nextPage, nextSize);
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
        <Typography.Title level={3} style={{ marginRight: 'auto' }}>Chunks</Typography.Title>
        <Button onClick={() => load()}>刷新</Button>
      </div>
      <ChunkTable data={items} total={total} loading={loading} page={page} pageSize={pageSize} onChange={load} />
    </div>
  );
}


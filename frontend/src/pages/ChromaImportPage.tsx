import { Button, Space, Table, Typography, message } from 'antd';
import { useEffect, useState } from 'react';
import { api, DocumentItem } from '../api';
import StatusBadge from '../components/StatusBadge';

export default function ChromaImportPage() {
  const [data, setData] = useState<DocumentItem[]>([]);
  const [loading, setLoading] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      setData(await api.listDocuments());
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const importOne = async (docId: string) => {
    try {
      await api.importChroma(docId);
      message.success('导入完成');
      load();
    } catch (error) {
      message.error((error as Error).message);
    }
  };

  return (
    <div className="page">
      <div className="toolbar">
        <Typography.Title level={3} style={{ marginRight: 'auto' }}>Chroma 导入</Typography.Title>
        <Button onClick={load}>刷新</Button>
      </div>
      <Table
        rowKey="doc_id"
        dataSource={data}
        loading={loading}
        columns={[
          { title: '文件名', dataIndex: 'filename' },
          { title: '状态', dataIndex: 'status', render: (status) => <StatusBadge status={status} /> },
          { title: 'QA 数', dataIndex: 'qa_count' },
          { title: '已导入', dataIndex: 'imported_to_chroma', render: (value) => (value ? '是' : '否') },
          { title: '操作', render: (_, row) => <Space><Button onClick={() => importOne(row.doc_id)}>导入 Chroma</Button></Space> }
        ]}
      />
    </div>
  );
}


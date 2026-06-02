import { Button, Popconfirm, Space, Table, Typography, message } from 'antd';
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api, DocumentItem } from '../api';
import ProgressBar from '../components/ProgressBar';
import StatusBadge from '../components/StatusBadge';

export default function DocumentListPage() {
  const [data, setData] = useState<DocumentItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [selected, setSelected] = useState<React.Key[]>([]);

  const load = async (silent = false) => {
    if (!silent) setLoading(true);
    try {
      setData(await api.listDocuments());
    } finally {
      if (!silent) setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);
  useEffect(() => {
    const hasRunningTask = data.some((item) => ['chunking', 'qa_processing', 'embedding_processing'].includes(item.status));
    if (!hasRunningTask) return;
    const timer = window.setInterval(() => load(true), 1500);
    return () => window.clearInterval(timer);
  }, [data]);

  const run = async (label: string, action: () => Promise<any>) => {
    const timer = window.setInterval(() => load(true), 1500);
    try {
      const promise = action();
      await load(true);
      await promise;
      message.success(`${label}完成`);
      load();
    } catch (error) {
      message.error((error as Error).message);
    } finally {
      window.clearInterval(timer);
    }
  };

  return (
    <div className="page">
      <div className="toolbar">
        <Typography.Title level={3} style={{ marginRight: 'auto' }}>文件列表</Typography.Title>
        <Button onClick={() => load()}>刷新</Button>
        <Button
          disabled={!selected.length}
          onClick={() => run('批量处理', () => api.batch(selected as string[], ['chunk', 'generate_qa', 'import_chroma']))}
        >
          批量全流程
        </Button>
      </div>
      <Table
        rowKey="doc_id"
        dataSource={data}
        loading={loading}
        scroll={{ x: 'max-content' }}
        rowSelection={{ selectedRowKeys: selected, onChange: setSelected }}
        columns={[
          { title: '文件名', dataIndex: 'filename', render: (text, row) => <Link to={`/documents/${row.doc_id}`}>{text}</Link> },
          { title: '类型', dataIndex: 'file_type', width: 90 },
          { title: '状态', dataIndex: 'status', width: 150, render: (status) => <StatusBadge status={status} /> },
          { title: 'chunk 数', dataIndex: 'total_chunks', width: 100 },
          { title: 'QA 数', dataIndex: 'qa_count', width: 90 },
          { title: '导入 Chroma', dataIndex: 'imported_to_chroma', width: 120, render: (value) => (value ? '是' : '否') },
          { title: '进度', width: 160, render: (_, row) => <ProgressBar total={row.total_chunks} done={row.imported_to_chroma ? row.total_chunks : row.processed_chunks} /> },
          {
            title: '操作',
            width: 500,
            render: (_, row) => {
              const running = ['chunking', 'qa_processing', 'embedding_processing'].includes(row.status);
              return (
                <Space wrap>
                  <Button disabled={running} size="small" onClick={() => run('分块', () => api.chunk(row.doc_id))}>分块</Button>
                  <Button disabled={running} size="small" onClick={() => run('生成 QA', () => api.generateQA(row.doc_id))}>生成 QA</Button>
                  <Button disabled={running} size="small" onClick={() => run('导入 Chroma', () => api.importChroma(row.doc_id))}>导入 Chroma</Button>
                  <Button disabled={running} size="small" onClick={() => run('重试失败', () => api.retryFailed(row.doc_id))}>重试失败</Button>
                  <Link to={`/documents/${row.doc_id}`}>详情</Link>
                  <Popconfirm
                    title="确认删除该文件？"
                    description="会删除原文件、中间结果、状态日志，并尝试删除 Chroma 中的记录。"
                    okText="删除"
                    cancelText="取消"
                    onConfirm={() => run('删除文件', () => api.deleteDocument(row.doc_id))}
                  >
                    <Button danger disabled={running} size="small">删除</Button>
                  </Popconfirm>
                </Space>
              );
            }
          }
        ]}
      />
    </div>
  );
}

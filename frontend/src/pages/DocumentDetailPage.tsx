import { Button, Descriptions, Popconfirm, Space, Statistic, Typography, message } from 'antd';
import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { api } from '../api';
import LogViewer from '../components/LogViewer';
import ProgressBar from '../components/ProgressBar';
import StatusBadge from '../components/StatusBadge';

export default function DocumentDetailPage() {
  const { docId = '' } = useParams();
  const navigate = useNavigate();
  const [state, setState] = useState<Record<string, any>>({});
  const [log, setLog] = useState('');

  const load = async () => {
    setState(await api.getState(docId));
    setLog((await api.getLogs(docId)).log);
  };

  useEffect(() => { load(); }, [docId]);
  useEffect(() => {
    if (!['chunking', 'qa_processing', 'embedding_processing'].includes(state.status)) return;
    const timer = window.setInterval(load, 1500);
    return () => window.clearInterval(timer);
  }, [state.status, docId]);

  const run = async (label: string, action: () => Promise<any>) => {
    const timer = window.setInterval(load, 1500);
    try {
      const promise = action();
      await load();
      await promise;
      message.success(`${label}完成`);
      load();
    } catch (error) {
      message.error((error as Error).message);
    } finally {
      window.clearInterval(timer);
    }
  };

  const remove = async () => {
    try {
      await api.deleteDocument(docId);
      message.success('删除完成');
      navigate('/documents');
    } catch (error) {
      message.error((error as Error).message);
    }
  };

  return (
    <div className="page">
      <div className="toolbar">
        <Typography.Title level={3} style={{ marginRight: 'auto' }}>{state.filename || docId}</Typography.Title>
        <Button onClick={load}>刷新</Button>
        <Button onClick={() => run('分块', () => api.chunk(docId))}>分块</Button>
        <Button onClick={() => run('生成 QA', () => api.generateQA(docId))}>生成 QA</Button>
        <Button onClick={() => run('导入 Chroma', () => api.importChroma(docId))}>导入 Chroma</Button>
        <Popconfirm
          title="确认删除该文件？"
          description="会删除原文件、中间结果、状态日志，并尝试删除 Chroma 中的记录。"
          okText="删除"
          cancelText="取消"
          onConfirm={remove}
        >
          <Button danger>删除</Button>
        </Popconfirm>
      </div>
      <Descriptions bordered column={2}>
        <Descriptions.Item label="doc_id"><span className="mono">{docId}</span></Descriptions.Item>
        <Descriptions.Item label="状态"><StatusBadge status={state.status} /></Descriptions.Item>
        <Descriptions.Item label="文件类型">{state.file_type}</Descriptions.Item>
        <Descriptions.Item label="当前步骤">{state.current_step}</Descriptions.Item>
        <Descriptions.Item label="创建时间">{state.created_at}</Descriptions.Item>
        <Descriptions.Item label="更新时间">{state.updated_at}</Descriptions.Item>
        <Descriptions.Item label="错误" span={2}>{state.error || '-'}</Descriptions.Item>
      </Descriptions>
      <Space size="large" wrap>
        <Statistic title="chunks" value={state.total_chunks || 0} />
        <Statistic title="processed" value={state.processed_chunks || 0} />
        <Statistic title="QA" value={state.qa_records || 0} />
        <Statistic title="failed" value={state.failed_chunks || 0} />
      </Space>
      <ProgressBar total={state.total_chunks} done={state.processed_chunks} />
      <Space>
        <Link to={`/documents/${docId}/chunks`}>查看 chunks</Link>
        <Link to={`/documents/${docId}/qa`}>查看 QA</Link>
      </Space>
      <LogViewer log={log} />
    </div>
  );
}

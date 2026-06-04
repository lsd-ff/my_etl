import { Button, Space, Statistic, Table, Tag, Typography } from 'antd';
import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { api } from '../api';

const severityColor: Record<string, string> = {
  high: 'red',
  warning: 'gold'
};

const typeLabel: Record<string, string> = {
  chunk: 'Chunk',
  qa: 'QA',
  failed_chunk: 'Failed'
};

export default function ReviewQueuePage() {
  const { docId = '' } = useParams();
  const [items, setItems] = useState<any[]>([]);
  const [summary, setSummary] = useState<Record<string, number>>({});
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [loading, setLoading] = useState(false);

  const load = async (nextPage = page, nextSize = pageSize) => {
    setLoading(true);
    try {
      const result = await api.reviewQueue(docId, nextPage, nextSize);
      setItems(result.items);
      setSummary(result.summary || {});
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
        <Typography.Title level={3} style={{ marginRight: 'auto' }}>审核队列</Typography.Title>
        <Button onClick={() => load()}>刷新</Button>
      </div>
      <Space size="large" wrap>
        <Statistic title="待审核" value={total} />
        <Statistic title="高风险" value={summary.high || 0} />
        <Statistic title="Chunk" value={summary.chunks || 0} />
        <Statistic title="QA" value={summary.qa || 0} />
        <Statistic title="Failed" value={summary.failed_chunks || 0} />
      </Space>
      <Table
        rowKey={(row) => `${row.type}-${row.id}`}
        dataSource={items}
        loading={loading}
        scroll={{ x: 'max-content' }}
        pagination={{ current: page, pageSize, total, showSizeChanger: true }}
        onChange={(pagination) => load(pagination.current || 1, pagination.pageSize || pageSize)}
        expandable={{
          expandedRowRender: (record) => (
            <div className="review-detail">
              {record.question ? <Typography.Paragraph><Typography.Text strong>Question</Typography.Text><br />{record.question}</Typography.Paragraph> : null}
              {record.answer ? <Typography.Paragraph><Typography.Text strong>Answer</Typography.Text><br />{record.answer}</Typography.Paragraph> : null}
              {record.evidence ? <Typography.Paragraph><Typography.Text strong>Evidence</Typography.Text><br />{record.evidence}</Typography.Paragraph> : null}
              {record.content ? <Typography.Paragraph className="pre-wrap">{record.content}</Typography.Paragraph> : null}
              {record.error ? <Typography.Paragraph type="danger">{record.error}</Typography.Paragraph> : null}
            </div>
          )
        }}
        columns={[
          {
            title: 'type',
            dataIndex: 'type',
            width: 110,
            render: (value) => <Tag>{typeLabel[value] || value}</Tag>
          },
          {
            title: 'severity',
            dataIndex: 'severity',
            width: 110,
            render: (value) => <Tag color={severityColor[value] || 'default'}>{value}</Tag>
          },
          { title: 'id', dataIndex: 'id', width: 230, ellipsis: true },
          { title: 'score', dataIndex: 'score', width: 90 },
          {
            title: 'reasons',
            dataIndex: 'reasons',
            width: 320,
            render: (value: string[] = []) => (
              <Space size={[4, 4]} wrap>{value.map((item) => <Tag key={item}>{item}</Tag>)}</Space>
            )
          },
          { title: 'page', dataIndex: 'page', width: 80 },
          { title: 'section', dataIndex: 'section', width: 180, ellipsis: true },
          {
            title: 'preview',
            ellipsis: true,
            render: (_: any, row: any) => row.question || row.content || row.error || ''
          }
        ]}
      />
    </div>
  );
}

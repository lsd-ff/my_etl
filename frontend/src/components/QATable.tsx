import { Table, Tag, Typography } from 'antd';

export default function QATable({ data, total, loading, page, pageSize, onChange }: any) {
  return (
    <Table
      rowKey="id"
      dataSource={data}
      loading={loading}
      scroll={{ x: 'max-content' }}
      pagination={{ current: page, pageSize, total, showSizeChanger: true }}
      onChange={(pagination) => onChange(pagination.current || 1, pagination.pageSize || pageSize)}
      expandable={{
        expandedRowRender: (record) => (
          <div className="pre-wrap">
            <Typography.Text strong>Context</Typography.Text>
            <Typography.Paragraph>{record.metadata?.context || record.context}</Typography.Paragraph>
            <Typography.Text strong>Evidence</Typography.Text>
            <Typography.Paragraph>{record.metadata?.evidence || record.evidence || '-'}</Typography.Paragraph>
          </div>
        )
      }}
      columns={[
        { title: 'QA ID', dataIndex: 'id', width: 230 },
        { title: 'question', dataIndex: 'document', ellipsis: true },
        { title: 'answer', render: (_: any, row: any) => row.metadata?.answer || row.answer, ellipsis: true },
        { title: 'type', render: (_: any, row: any) => row.metadata?.answer_type || row.answer_type || '-', width: 90 },
        { title: 'quality', render: (_: any, row: any) => row.metadata?.quality_score ?? row.quality_score ?? '-', width: 90 },
        {
          title: 'warnings',
          render: (_: any, row: any) => {
            const warnings = String(row.metadata?.validation_warnings || row.validation_warnings || '')
              .split(',')
              .map((item) => item.trim())
              .filter(Boolean);
            return warnings.length ? warnings.map((item) => <Tag key={item}>{item}</Tag>) : '-';
          },
          width: 240
        },
        { title: 'keywords', render: (_: any, row: any) => row.metadata?.keywords || row.keywords, width: 220, ellipsis: true },
        { title: 'source', render: (_: any, row: any) => row.metadata?.source || row.source, width: 180 },
        { title: 'page', render: (_: any, row: any) => row.metadata?.page ?? row.page, width: 80 }
      ]}
    />
  );
}

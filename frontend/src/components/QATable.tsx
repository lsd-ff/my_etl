import { Table, Typography } from 'antd';

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
          </div>
        )
      }}
      columns={[
        { title: 'QA ID', dataIndex: 'id', width: 230 },
        { title: 'question', dataIndex: 'document', ellipsis: true },
        { title: 'answer', render: (_: any, row: any) => row.metadata?.answer || row.answer, ellipsis: true },
        { title: 'keywords', render: (_: any, row: any) => row.metadata?.keywords || row.keywords, width: 220, ellipsis: true },
        { title: 'source', render: (_: any, row: any) => row.metadata?.source || row.source, width: 180 },
        { title: 'page', render: (_: any, row: any) => row.metadata?.page ?? row.page, width: 80 }
      ]}
    />
  );
}

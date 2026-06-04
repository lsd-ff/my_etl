import { Space, Table, Tag, Typography } from 'antd';

export default function ChunkTable({ data, total, loading, page, pageSize, onChange }: any) {
  return (
    <Table
      rowKey="chunk_id"
      dataSource={data}
      loading={loading}
      scroll={{ x: 'max-content' }}
      pagination={{ current: page, pageSize, total, showSizeChanger: true }}
      onChange={(pagination) => onChange(pagination.current || 1, pagination.pageSize || pageSize)}
      expandable={{ expandedRowRender: (record: any) => <Typography.Paragraph className="pre-wrap">{record.content}</Typography.Paragraph> }}
      columns={[
        { title: 'chunk_id', dataIndex: 'chunk_id', width: 220 },
        { title: 'index', dataIndex: 'chunk_index', width: 90 },
        { title: 'page', dataIndex: 'page', width: 80 },
        { title: 'section', dataIndex: 'section', width: 160 },
        { title: 'tokens', dataIndex: 'token_count', width: 90 },
        { title: 'quality', dataIndex: 'quality_score', width: 90 },
        {
          title: 'warnings',
          dataIndex: 'warnings',
          width: 260,
          render: (value: string[] = []) => (
            <Space size={[4, 4]} wrap>{value.map((item) => <Tag key={item}>{item}</Tag>)}</Space>
          )
        },
        { title: 'content', dataIndex: 'content', ellipsis: true },
        { title: 'chunk_hash', dataIndex: 'chunk_hash', width: 220, ellipsis: true }
      ]}
    />
  );
}

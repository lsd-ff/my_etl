import { Alert, Card, Typography } from 'antd';
import { useState } from 'react';
import { Link } from 'react-router-dom';
import FileUploader from '../components/FileUploader';

export default function UploadPage() {
  const [docId, setDocId] = useState('');

  return (
    <div className="page">
      <Typography.Title level={3}>上传文件</Typography.Title>
      <FileUploader onUploaded={setDocId} />
      {docId && (
        <Alert
          type="success"
          showIcon
          message="上传成功"
          description={<span>doc_id: <Link to={`/documents/${docId}`}>{docId}</Link></span>}
        />
      )}
      <Card title="处理入口">
        <Typography.Paragraph>
          上传完成后可进入文件列表执行分块、QA 生成和 Chroma 导入。
        </Typography.Paragraph>
      </Card>
    </div>
  );
}


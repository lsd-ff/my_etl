import { InboxOutlined } from '@ant-design/icons';
import { Upload, message } from 'antd';
import type { UploadProps } from 'antd';
import { api } from '../api';

export default function FileUploader({ onUploaded }: { onUploaded?: (docId: string) => void }) {
  const props: UploadProps = {
    name: 'file',
    multiple: false,
    accept: '.pdf,.docx,.txt,.md,.markdown',
    customRequest: async ({ file, onSuccess, onError }) => {
      try {
        const result = await api.upload(file as File);
        message.success(`上传成功：${result.doc_id}`);
        onUploaded?.(result.doc_id);
        onSuccess?.(result);
      } catch (error) {
        message.error((error as Error).message);
        onError?.(error as Error);
      }
    }
  };

  return (
    <Upload.Dragger {...props}>
      <p className="ant-upload-drag-icon"><InboxOutlined /></p>
      <p className="ant-upload-text">拖拽或点击上传文档</p>
      <p className="ant-upload-hint">支持 PDF、DOCX、TXT、Markdown</p>
    </Upload.Dragger>
  );
}


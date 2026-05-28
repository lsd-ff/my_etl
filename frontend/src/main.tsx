import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter, Link, Navigate, Route, Routes } from 'react-router-dom';
import { Layout, Menu, Typography } from 'antd';
import {
  CloudUploadOutlined,
  DatabaseOutlined,
  FileTextOutlined,
  SearchOutlined,
  UnorderedListOutlined
} from '@ant-design/icons';
import 'antd/dist/reset.css';
import './styles.css';
import UploadPage from './pages/UploadPage';
import DocumentListPage from './pages/DocumentListPage';
import DocumentDetailPage from './pages/DocumentDetailPage';
import ChunkViewerPage from './pages/ChunkViewerPage';
import QAViewerPage from './pages/QAViewerPage';
import ChromaImportPage from './pages/ChromaImportPage';
import SearchPage from './pages/SearchPage';

const { Header, Content, Sider } = Layout;

function App() {
  return (
    <BrowserRouter>
      <Layout className="app-shell">
        <Sider width={236} theme="light" className="app-sider">
          <Typography.Title level={4} className="brand">QA Vector Admin</Typography.Title>
          <Menu
            mode="inline"
            defaultSelectedKeys={['documents']}
            items={[
              { key: 'upload', icon: <CloudUploadOutlined />, label: <Link to="/upload">上传文件</Link> },
              { key: 'documents', icon: <UnorderedListOutlined />, label: <Link to="/documents">文件列表</Link> },
              { key: 'chroma', icon: <DatabaseOutlined />, label: <Link to="/chroma">Chroma 导入</Link> },
              { key: 'search', icon: <SearchOutlined />, label: <Link to="/search">搜索测试</Link> }
            ]}
          />
        </Sider>
        <Layout>
          <Header className="app-header">
            <FileTextOutlined />
            <span>大文档 QA 向量化处理平台</span>
          </Header>
          <Content className="app-content">
            <Routes>
              <Route path="/" element={<Navigate to="/documents" replace />} />
              <Route path="/upload" element={<UploadPage />} />
              <Route path="/documents" element={<DocumentListPage />} />
              <Route path="/documents/:docId" element={<DocumentDetailPage />} />
              <Route path="/documents/:docId/chunks" element={<ChunkViewerPage />} />
              <Route path="/documents/:docId/qa" element={<QAViewerPage />} />
              <Route path="/chroma" element={<ChromaImportPage />} />
              <Route path="/search" element={<SearchPage />} />
            </Routes>
          </Content>
        </Layout>
      </Layout>
    </BrowserRouter>
  );
}

ReactDOM.createRoot(document.getElementById('root')!).render(<App />);


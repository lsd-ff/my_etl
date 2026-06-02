import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter, Link, Navigate, Route, Routes, useLocation } from 'react-router-dom';
import { ConfigProvider, Layout, Menu, Typography } from 'antd';
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
  const location = useLocation();
  const selectedKey = location.pathname.startsWith('/upload')
    ? 'upload'
    : location.pathname.startsWith('/chroma')
      ? 'chroma'
      : location.pathname.startsWith('/search')
        ? 'search'
        : 'documents';

  return (
    <ConfigProvider
      theme={{
        token: {
          colorPrimary: '#2563eb',
          colorSuccess: '#0f9f6e',
          colorWarning: '#b7791f',
          colorError: '#dc2626',
          colorText: '#172033',
          colorTextSecondary: '#667085',
          colorBgLayout: '#f6f7f9',
          colorBorder: '#d9dee8',
          borderRadius: 6,
          controlHeight: 34,
          fontFamily: 'Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'
        },
        components: {
          Table: {
            headerBg: '#f8fafc',
            headerColor: '#475467',
            rowHoverBg: '#f7faff'
          },
          Menu: {
            itemBorderRadius: 6,
            itemSelectedBg: '#eef4ff',
            itemSelectedColor: '#1d4ed8'
          }
        }
      }}
    >
      <Layout className="app-shell">
        <Sider width={248} theme="light" className="app-sider">
          <div className="brand">
            <div className="brand-mark">etl</div>
            <div>
              <Typography.Title level={4} className="brand-title">文档处理助手</Typography.Title>
            </div>
          </div>
          <Menu
            mode="inline"
            selectedKeys={[selectedKey]}
            items={[
              { key: 'upload', icon: <CloudUploadOutlined />, label: <Link to="/upload">上传文件</Link> },
              { key: 'documents', icon: <UnorderedListOutlined />, label: <Link to="/documents">文件列表</Link> },
              { key: 'chroma', icon: <DatabaseOutlined />, label: <Link to="/chroma">Chroma 导入</Link> },
              { key: 'search', icon: <SearchOutlined />, label: <Link to="/search">搜索测试</Link> }
            ]}
          />
        </Sider>
        <Layout className="app-main">
          <Header className="app-header">
            <div className="header-title">
              <FileTextOutlined />
              <span>文档处理平台</span>
            </div>
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
    </ConfigProvider>
  );
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <BrowserRouter>
    <App />
  </BrowserRouter>
);

# 智能合约安全审计工具

## 项目编号: 6600002

## 项目类型
全栈

## 技术栈
- **前端**: Vue 3 + TypeScript + Ant Design Vue + Monaco Editor
- **后端**: Python FastAPI + 正则引擎 + AST分析
- **数据库**: SQLite

## 项目描述
面向区块链开发者，Solidity合约代码上传、漏洞模式扫描、Gas优化建议、安全评分报告

## 核心功能
- Monaco Editor语法高亮（Solidity）
- 重入攻击漏洞检测
- 整数溢出/下溢检测
- 未授权访问检测
- 自杀指令检测
- Gas消耗分析优化建议
- 综合安全评分与PDF报告导出

## 技术亮点
正则模式库匹配漏洞，AST简单解析，ReportLab生成PDF

## 快速启动

### 前端
```bash
cd frontend
npm install
npm run dev
```

### 后端
```bash
cd backend
# Python
pip install -r requirements.txt
uvicorn app.main:app --reload

# Java
cd backend
mvn spring-boot:run
```

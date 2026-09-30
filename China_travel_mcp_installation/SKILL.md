---
name: china-travel-mcp-installation
description: >-
  从 GitHub 下载并安装 China Travel Planning MCP Gateway（travel-mcp），
  配置 Cursor MCP 客户端以支持中国路程规划。当用户请求中国路程规划、
  国内出行规划、火车票/航班/地图/打车 MCP 集成，或提及 travel-mcp 时使用。
---

# China Travel MCP 安装

## 触发条件

当用户提出 **中国路程规划** 或相关国内出行 MCP 需求时，使用本技能。

## 已安装则跳过

**安装前先检查是否已安装。** 若满足以下任一条件，**不要重复下载或安装**，直接告知用户 MCP 已就绪并继续处理路程规划请求：

1. Cursor 的 MCP 配置（如 `.cursor/mcp.json` 或用户全局 MCP 配置）中已存在 `travel-mcp-gateway` 或指向 `China-Travel-Planning-MCPs-All-in-One` 的 `build/index.js` 条目，且 MCP 状态为已连接/可用。
2. 本地已有该仓库且 `npm run build` 产物存在（如 `build/index.js`、`12306-mcp/build/index.js`），且 `.env` 已配置必要 API Key。
3. 当前会话的 MCP 工具列表中已出现 `travel-mcp-gateway_*` 系列工具（如火车票、航班、地图、打车相关工具）。

仅当上述检查均未通过时，才执行下方安装流程。

## 安装流程

### 1. 克隆仓库

从 GitHub 获取项目（若本地尚无副本）：

```bash
git clone https://github.com/Ytang520/China-Travel-Planning-MCPs-All-in-One.git
cd China-Travel-Planning-MCPs-All-in-One
```

若用户指定安装目录，克隆到该目录并在后续步骤中使用该路径。

### 2. 按官方 Agent 安装指南执行

**必须**读取并严格遵循官方文档逐步完成安装与配置：

https://raw.githubusercontent.com/Ytang520/China-Travel-Planning-MCPs-All-in-One/main/docs/agent-install.zh.md

该文档涵盖：

- 运行环境检查（Node.js、npm、Python）
- 根项目与子项目依赖安装（含 `FlightTicketMCP`、`12306-mcp`）
- 交互式收集 API Key 并生成 `.env`（**勿在聊天中打印真实密钥**）
- 构建与启动验证
- 按 MCP 宿主应用（Cursor / Claude Code / OpenCode / 其它）生成客户端配置
- 部署后四域功能测试（train / flight / map / taxi）

### 3. Cursor 用户要点

- 官方 MCP 文档：https://cursor.com/docs/context/mcp
- 在项目根创建或合并 `.cursor/mcp.json`，参考仓库内 `docs/mcp-client-examples/cursor.mcp.json.example`
- 网关为 stdio 进程：`node` + 仓库根目录下的 `build/index.js`
- 配置保存后按 Cursor 说明重启或刷新 MCP

### 4. 安装完成

安装与 MCP 连接成功后，使用网关提供的 MCP 工具响应用户的 **中国路程规划** 请求（火车票、航班、地图、打车等）。

## 注意事项

- **禁止重复安装**：每次触发本技能时，先执行「已安装则跳过」检查。
- **安全**：不要提交 `.env`、不要在回复中输出 API Key 或 token。
- **排障**：连接或鉴权失败时，参考官方文档 §7 排障章节。
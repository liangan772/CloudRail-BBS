# CloudRail 论坛（工作区代号，可替换）

一个中文社区论坛项目：**自研前端（HTML/JS + 现代框架）+ Discourse 后端**。

- **前端**：Nuxt 3（Vue 3 + TypeScript + Vite），SSR 保证 SEO，技术栈完全自主可控
- **后端**：Discourse（Ruby on Rails 8 / Ruby 3.4），承担数据存储、权限、审核、邮件、搜索、限流等全部业务能力
- **对接方式**：Discourse REST API + MessageBus（实时消息）+ 同域反向代理（登录会话 / 上传 / WebSocket 走同一域名，避免跨域问题）

```
用户浏览器
   │
   ▼
nginx (forum.example.com:443)
   ├── / 及前端路由        → Nuxt SSR 应用（自研前端）
   ├── /session /message-bus /uploads /user-api-key /raw 及 *.json API
   │                        → Discourse（官方 Docker，内网端口）
   └── /admin 等系统路径    → 仅内网/管理员白名单
```

> Discourse 只作为后端服务，不对外提供其自带的 Ember 页面（管理员后台除外，见 `docs/02`）。
> 参考源码位于 `D:\discourse`（只读参考；插件开发阶段再按 `docs/06` 准备可写副本）。

## 文档索引

| 文档 | 内容 |
|------|------|
| [docs/01-项目概述与技术选型.md](docs/01-项目概述与技术选型.md) | 产品定位、功能范围、技术选型与取舍、风险 |
| [docs/02-系统架构与后端接入.md](docs/02-系统架构与后端接入.md) | 部署形态、认证/CSRF、API 端点清单、实时消息、上传、错误与限流、后端扩展 |
| [docs/03-前端工程规范.md](docs/03-前端工程规范.md) | 前端技术栈、目录结构、API 客户端、状态管理、组件与代码规范、性能 |
| [docs/04-数据模型与功能规划.md](docs/04-数据模型与功能规划.md) | 功能清单、Discourse 数据模型映射、站点设置、权限、内容治理、插件路线 |
| [docs/05-中文支持与本地化.md](docs/05-中文支持与本地化.md) | 中文 locale、中文用户名/搜索、前端 i18n、SEO、内容规范 |
| [docs/06-开发环境搭建.md](docs/06-开发环境搭建.md) | Discourse 与前端环境、联调代理、种子数据、常用命令、排障 |
| [docs/07-测试与质量保障.md](docs/07-测试与质量保障.md) | 测试分层、工具、CI 门禁、质量红线 |
| [docs/08-部署运维与安全.md](docs/08-部署运维与安全.md) | 生产拓扑、Docker 部署、备份升级、监控、安全清单、大陆合规（备案） |
| [docs/09-开发工作流程.md](docs/09-开发工作流程.md) | 分支模型、任务流转、PR/评审、发布流程、里程碑计划 |

## 快速开始（详见 docs/06）

```bash
# 1. 启动 Discourse（官方 Docker，约 10 分钟）
# 2. 启动前端
cd web && pnpm install && pnpm dev
# 3. 打开 http://localhost:5173，登录后即可发帖
```

## 仓库规划（建议）

```
E:\CloudRail\
├── README.md
├── docs/                    # 开发文档（本套文档）
├── web/                     # 自研前端（Nuxt 3）
├── discourse/               # （后续）Discourse 源码副本，仅插件开发时使用
└── deploy/                  # nginx 配置、部署脚本、监控配置
```

当前 `docs/` 已就绪；`web/`、`deploy/` 待里程碑 M0 创建（见 docs/09）。

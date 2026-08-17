# CloudRail 论坛

前后端分离的中文社区论坛系统，一套 API 同时支撑 **Web / H5 / App / 小程序** 多端。内置签到、积分、等级、任务、成就、排行榜等活跃度机制，以及轮播图、话题广场、投票帖、举报、拉黑、**AI 自动审核**等主流论坛功能。

## 功能特性

### 内容与互动
- 帖子：发帖（富文本 / Markdown）、编辑、软删除、多图上传、置顶 / 加精、**匿名发帖**
- 评论：两级结构（评论 + 楼中楼）、点赞、收藏
- 分类 / 标签 / **话题广场**（话题热度榜、关注话题）
- **投票帖**（单选 / 多选、截止时间、一人一票）、**草稿箱**（自动保存）
- **轮播图**运营位、**推荐流**、**公告中心**、浏览足迹、分享海报
- 搜索：全文检索 + 热词

### 用户与认证
- 注册 / 登录（图形验证码、登录限流）、JWT 双 Token（Access + Refresh，轮换与重用检测）
- 手机号验证码登录、第三方登录（微信 / QQ / GitHub）、扫码登录
- 多端会话管理（设备列表、远程踢下线）、找回密码
- **举报**（后台处理队列）、**拉黑 / 屏蔽**（双向不可见）

### AI 自动审核（v1.3）
- LLM 内容安全审核（OpenAI 兼容协议：DeepSeek / 通义千问 / 智谱，可切换供应商）
- 审核结论：`pass` 通过 / `review` 转人工 / `reject` 拦截，附违规分与命中类别
- 两种模式：`sync` 先审后发 / `async` 先发后审（违规自动下架）；异常熔断降级，不阻塞发帖
- 每次审核写入 `audit_records` 表，管理后台可查询复核

### 活跃度体系
- 每日签到（连续天数加成、签到日历）、积分账户（流水审计）
- 等级 / 头衔、每日任务 / 新手任务、成就勋章
- 排行榜（积分 / 签到 / 贡献）、邀请奖励、关注动态流

### 通知与推送
- 通知中心（回复 / 点赞 / 关注 / 公告 / 私信）、未读数
- App 消息推送（APNs / FCM / 厂商通道）、短信服务

### 管理后台
- 运营看板、用户 / 内容管理、敏感词库、激励配置
- 轮播图管理、举报处理、话题运营、AI 审核记录

## 技术栈

| 端 | 技术 |
| --- | --- |
| 前端 | Vue 3 + TypeScript + Vite + Pinia + Vue Router + Element Plus |
| 后端 | Python 3.11+ / FastAPI + SQLAlchemy 2.0（异步）+ Alembic + Celery |
| 数据库 | PostgreSQL 16 |
| 缓存 / 队列 | Redis 7 |
| AI 审核 | OpenAI 兼容协议（DeepSeek / 通义千问 / 智谱） |
| 部署 | Docker Compose + Nginx |

## 目录结构

```
├── docs/            # 开发文档（架构、数据库、API、缓存、部署等完整设计）
├── frontend/        # 前端（Vue 3 + Vite）
├── backend/         # 后端（FastAPI + Celery）
├── deploy/          # 部署（docker-compose.yml、nginx 配置、entrypoint）
├── Dockerfile       # 合并镜像（Nginx 前端 + FastAPI 后端，单镜像）
└── .dockerignore
```

## 快速开始

> 前置要求：Python 3.11+、Node.js 18+、Docker（可选，用于启动数据库与 Redis / 一键部署）

### 1. 启动依赖（PostgreSQL + Redis）

```bash
docker compose -f deploy/docker-compose.yml up -d postgres redis
```

不使用 Docker 时，请自行安装 PostgreSQL 16 与 Redis 7，并修改 `backend/.env` 中的连接串。

### 2. 后端

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate；macOS/Linux: source .venv/bin/activate
./.venv/Scripts/activate

pip install -e ".[dev]"
# 国内网络建议加镜像：-i https://mirrors.aliyun.com/pypi/simple/

cp .env.example .env        # 按需修改数据库/Redis/密钥/AI 审核配置
alembic upgrade head        # 应用数据库迁移

# 启动后端（推荐使用脚本，自动加载 .env 中的 Uvicorn 配置）
./run.sh                    # Git Bash / Linux / macOS；Windows PowerShell 用 .\run.ps1

# 或直接显式指定参数（不依赖 .env）
uvicorn app.main:app --reload --port 8000
```

> 说明：`backend/.env` 中的 `UVICORN_HOST` / `UVICORN_PORT` / `UVICORN_RELOAD` 等配置
> 由 `run.sh` / `run.ps1` 加载到进程环境后生效（uvicorn 的 `--env-file` 无法配置其自身参数，
> 仅能为应用注入环境变量）。

- API 文档（Swagger UI）：<http://localhost:8000/docs>
- 健康检查：<http://localhost:8000/health>

### 3. 前端

```bash
cd frontend
npm install
npm run dev     # http://localhost:5173（/api 自动代理到 8000）
```

### 4. Celery（异步任务，可选启动）

```bash
cd backend
celery -A app.tasks.celery_app:celery_app worker --loglevel=info   # 任务 Worker（含 AI 审核等）
celery -A app.tasks.celery_app:celery_app beat --loglevel=info     # 定时任务
```

## 测试

```bash
# 后端（需先激活 backend/.venv）
cd backend
pytest

# 前端（类型检查 + 构建）
cd frontend
npm run build
```

## 部署

```bash
# 方式一：从项目根目录
docker compose -f deploy/docker-compose.yml up -d --build

# 方式二：进入 deploy 目录
cd deploy && docker compose up -d --build
```

两种方式均会启动：PostgreSQL + Redis + 合并镜像（Nginx 前端 + 后端 API）+ Worker + Beat。

- 前端：<http://localhost>（合并镜像内 Nginx 托管）
- 后端 API：<http://localhost/api/>（Nginx 反代到容器内 FastAPI）

> 镜像策略：前后端打包为**单一镜像**（根目录 `Dockerfile`，多阶段构建：前端构建 → Python + Nginx 运行层）。
> 手动构建：`docker build -t forum:latest .`；worker / beat 复用同一镜像，仅覆盖启动命令。

> 首次部署请先 `cp deploy/.env.example deploy/.env` 并修改密码与密钥。

生产环境部署要点（详见开发文档第 10 章）：HTTPS 证书、`SECRET_KEY` 替换为随机 64 字节、数据库主从、监控告警。

## 配置说明

后端环境变量（`backend/.env`，完整清单见开发文档 10.3 节）：

| 变量 | 说明 |
| --- | --- |
| `DATABASE_URL` / `REDIS_URL` | PostgreSQL / Redis 连接串 |
| `SECRET_KEY` | JWT 签名密钥（生产必须更换） |
| `ACCESS_TOKEN_EXPIRE_MINUTES` / `REFRESH_TOKEN_EXPIRE_DAYS` | Token 有效期 |
| `CORS_ORIGINS` | 允许的前端来源（逗号分隔） |
| `SMS_*` / `PUSH_*` / `OAUTH_*` | 短信 / 推送 / 第三方登录凭证（可选） |
| `AI_ENABLED` | 是否启用 AI 审核（`true` / `false`） |
| `AI_BASE_URL` / `AI_API_KEY` / `AI_MODEL` | LLM 供应商接入（OpenAI 兼容协议） |
| `AI_AUDIT_MODE` | 审核模式：`sync` 先审后发 / `async` 先发后审 / `off` 关闭 |
| `AI_AUDIT_THRESHOLD` | 违规分阈值（默认 `0.6`，预留） |
| `UVICORN_HOST` / `UVICORN_PORT` / `UVICORN_RELOAD` / `UVICORN_WORKERS` | Uvicorn 运行配置（由 `run.sh` / `run.ps1` 加载生效） |

## 文档

- [开发文档](docs/开发文档.md)（v1.3）：总体架构、功能需求、数据库设计（ER 图 + 表结构）、API 接口清单、缓存与队列设计、核心实现要点、部署方案、里程碑计划
- API 调试：后端启动后访问 <http://localhost:8000/docs>

## 开发路线

| 阶段 | 内容 |
| --- | --- |
| M1 | 项目搭建（脚手架、CI、数据库迁移基线） |
| M2 | 用户体系与认证（JWT、短信、第三方登录、多设备） |
| M3 | 内容与互动（帖子、评论、投票、草稿、匿名、足迹、AI 审核接入） |
| M4–M5 | 检索缓存、通知推送 |
| M6–M7 | 管理后台（含 AI 审核记录）、活跃度体系 |
| M8–M10 | APP 端支撑（底部导航、扫码登录）、安全加固、上线打磨 |

完整里程碑见开发文档第 12 章（合计约 16 周，2 人并行）。

---

*当前状态：项目骨架 + AI 自动审核 API 已实现可用；其余业务模块（认证、帖子、评论等）为占位实现，按开发文档逐模块开发中。*

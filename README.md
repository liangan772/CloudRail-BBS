# CloudRail 论坛

> **版本：v0.1.0** ｜ 核心业务闭环（注册登录 → 发帖评论 → 管理后台）已实现可运行

前后端分离的中文社区论坛系统，一套 API 同时支撑 **Web / H5 / App / 小程序** 多端。核心业务闭环（注册登录 → 发帖评论 → 管理后台）已可运行，并规划了签到、积分、投票、话题广场、AI 自动审核等主流论坛能力。

## 功能特性

> ✅ 已实现可用 ｜ 🚧 规划中（见开发文档）

### 内容与互动
| 状态 | 功能 |
| --- | --- |
| ✅ | 发帖（分类、**匿名发帖**、标题/正文校验）、帖子列表（最新/热门/精华、游标分页）、详情（浏览计数） |
| ✅ | 评论列表 / 发表评论（需登录 + 验证码） |
| ✅ | 帖子卡片封面图展示（受后台「帖子图片展示」开关控制） |
| 🚧 | 富文本/Markdown 编辑器、编辑/软删除、多图上传、置顶/加精、点赞/收藏、投票帖、草稿箱 |
| 🚧 | 分类标签、话题广场、轮播图、推荐流、公告中心、浏览足迹、全文搜索、分享海报 |

### 用户与认证
| 状态 | 功能 |
| --- | --- |
| ✅ | 注册 / 登录（**图形验证码**必填校验，首用户自动成为管理员）、JWT 双 Token、注册即登录 |
| ✅ | 管理后台 / 发帖**强制登录**（未登录自动跳转登录页并回跳） |
| ✅ | 登录/注册失败自动刷新验证码 |
| 🚧 | 手机号验证码登录、第三方登录（微信/QQ/GitHub）、扫码登录、多端会话管理、找回密码、举报、拉黑 |

### AI 自动审核（v1.3）
- ✅ `POST /api/v1/audit/text` 同步审核接口（OpenAI 兼容协议：DeepSeek / 通义 / 智谱）
- ✅ 审核结论 pass / review / reject + 违规分 + 命中类别；`audit_records` 表落库
- 🚧 发帖/评论发布链路自动接入（sync 先审后发 / async 先发后审）

### 管理后台（/admin，需登录 + 管理员角色）
- ✅ 仪表盘（统计卡片 + 图表占位）、站点配置（帖子图片开关、站点名称，**真实读写** `site_configs` 表）
- ✅ 侧边菜单 9 项（用户/内容/举报/轮播图/话题/AI 审核/敏感词，占位待开发）
- 🚧 用户管理、内容审核、举报处理、轮播图管理、敏感词库、运营看板图表

### 规划中（活跃度 / 通知推送）
- 🚧 签到、积分、等级、任务、成就、排行榜、邀请、关注动态流
- 🚧 通知中心、App 推送（APNs/FCM/厂商通道）、短信服务

## 技术栈

| 端 | 技术 |
| --- | --- |
| 前端 | Vue 3 + TypeScript + Vite + Pinia + Vue Router + Element Plus |
| 后端 | Python 3.11+ / FastAPI + SQLAlchemy 2.0（异步）+ Alembic + Celery |
| 数据库 | PostgreSQL 16（生产）；**SQLite 开发降级**（零依赖开箱即用） |
| 缓存 / 队列 | Redis 7 |
| AI 审核 | OpenAI 兼容协议（DeepSeek / 通义千问 / 智谱） |
| 部署 | 单镜像 Docker（Nginx 前端 + FastAPI 后端）+ Docker Compose |

## 目录结构

```
├── docs/            # 开发文档（架构、数据库、API、缓存、部署等完整设计）
├── frontend/        # 前端（Vue 3 + Vite；含本地示例图 public/images）
├── backend/         # 后端（FastAPI + Celery；含 run.sh / run.ps1 启动脚本）
├── deploy/          # 部署（docker-compose.yml、nginx 配置、entrypoint）
├── scripts/         # 辅助脚本（check.sh 检查、e2e_check.py 端到端联调）
├── Dockerfile       # 合并镜像（Nginx 前端 + FastAPI 后端，单镜像）
├── .dockerignore
└── .github/workflows/  # CI：镜像构建检查 + GHCR 发布
```

## 快速开始

> 前置要求：Python 3.11+、Node.js 18+。数据库 **默认使用 SQLite**（`backend/forum.db`），无需安装 PostgreSQL；换用 PostgreSQL 只需改 `backend/.env` 的 `DATABASE_URL`。

### 1. 后端

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate；macOS/Linux: source .venv/bin/activate
./.venv/Scripts/activate

pip install -e ".[dev]"
# 国内网络建议加镜像：-i https://mirrors.aliyun.com/pypi/simple/

cp .env.example .env        # 按需修改密钥/数据库等配置
./run.sh                    # 一键启动（自动加载 .env 的 Uvicorn 配置）；PowerShell 用 .\run.ps1
```

- API 文档（Swagger UI）：<http://localhost:8000/docs>
- 健康检查：<http://localhost:8000/health>
- 首次启动自动建表 + 写入默认分类（技术交流/生活闲聊/站务公告）

### 2. 前端

```bash
cd frontend
npm install
npm run dev     # http://localhost:5173（/api 自动代理到 8000）
```

### 3. 体验完整流程

1. 打开 <http://localhost:5173/register> **注册**（首个用户自动成为管理员）
2. 首页 <http://localhost:5173/home> 查看帖子列表（真实数据）
3. 顶部「发帖」→ 选分类 + 填标题/正文 + 验证码 → 发布
4. 帖子详情页发表评论（需登录 + 验证码）
5. 右上角用户名 →「管理后台」→ 站点配置：关闭「帖子图片展示」开关 → 首页封面图立即隐藏

### 4. Celery（异步任务，可选）

```bash
cd backend
celery -A app.tasks.celery_app:celery_app worker --loglevel=info   # Worker（含 AI 审核等）
celery -A app.tasks.celery_app:celery_app beat --loglevel=info     # 定时任务
```

## 测试

```bash
# 后端单元测试（pytest，使用独立测试库）
cd backend && pytest

# 端到端联调（验证码 → 注册(管理员) → 登录 → 发帖 → 评论 → 后台配置 → 权限）
cd backend && python ../scripts/e2e_check.py

# 前端类型检查 + 构建
cd frontend && npm run build
```

## 部署教程

### 0. 环境要求

- Docker 20.10+（含 `docker compose` 插件）
- 服务器开放 80 端口（本地演示可省略）
- 建议 2 核 2G 以上（前端构建 + 后端 + 数据库）

### 1. 准备部署配置

```bash
cd deploy
cp .env.example .env
# 修改 deploy/.env：
#   PG_PASSWORD=强密码                # PostgreSQL 密码
#   SECRET_KEY=<随机 64 字节>          # JWT 签名密钥（python -c "import secrets;print(secrets.token_urlsafe(48))"）
#   CORS_ORIGINS=http://your-domain   # 允许的前端来源
```

### 2. 构建并启动全部服务

```bash
# 方式一：从项目根目录
cd .. && docker compose -f deploy/docker-compose.yml up -d --build
# 方式二：已在 deploy 目录
cd deploy && docker compose up -d --build
```

启动 6 个服务：PostgreSQL、Redis、后端（合并镜像：Nginx 前端 + FastAPI）、Celery Worker、Celery Beat。
首次构建约 5–10 分钟（前端 npm 安装 + 后端 pip 安装）。

### 3. 验证部署

```bash
docker compose -f deploy/docker-compose.yml ps          # 全部 running 即正常
curl http://localhost/api/v1/site-config                # 返回站点配置 JSON
curl http://localhost/api/v1/posts                      # 帖子列表（初始为空）
```

浏览器访问 <http://localhost>：

1. 打开 **注册** 页创建账号（**首个注册用户自动成为管理员**）
2. 首页发帖 → 详情评论 → 右上角用户名进入**管理后台** → 站点配置

### 4. 初始化与日常运维

| 操作 | 命令 |
| --- | --- |
| 查看状态 | `docker compose -f deploy/docker-compose.yml ps` |
| 后端日志 | `docker compose -f deploy/docker-compose.yml logs -f backend` |
| Worker 日志 | `docker compose -f deploy/docker-compose.yml logs -f worker` |
| 更新部署 | `docker compose -f deploy/docker-compose.yml up -d --build`（重新构建镜像） |
| 仅重启 | `docker compose -f deploy/docker-compose.yml restart backend` |
| 停止服务 | `docker compose -f deploy/docker-compose.yml down` |
| 停止并清数据 | `docker compose -f deploy/docker-compose.yml down -v`（**删除数据库卷，慎用**） |

> 首次启动说明：后端容器启动时自动建表并写入默认分类（技术交流 / 生活闲聊 / 站务公告）；
> 数据库持久化于 Docker 卷 `pgdata`，升级/重建容器不会丢失数据。

### 5. 生产环境加固（详见开发文档第 10 章）

- **HTTPS**：绑定域名，配置 Nginx TLS（443 端口）+ 证书（Let's Encrypt / 云厂商）
- **密钥**：`SECRET_KEY` 必须替换为随机值；`PG_PASSWORD` 使用强密码
- **数据安全**：PostgreSQL 定时备份（`pg_dump`），可选主从复制
- **持久化**：上传目录挂载卷（`/data/uploads`），避免容器重建丢图
- **监控**：Prometheus + Grafana（QPS / 延迟 / Redis 命中率 / 队列深度）

---

## 手动部署（无 Docker）

适用场景：目标机器没有 Docker，或需要以进程方式直接运行。

### 1. 环境要求

- Python 3.11+、Node.js 18+
- 数据库：PostgreSQL 16 + Redis 7（生产推荐）；**零依赖体验可直接使用 SQLite**（无需安装任何数据库）

### 2. 获取代码

```bash
# 方式一：克隆仓库
git clone https://github.com/liangan772/CloudRail-BBS.git && cd CloudRail-BBS

# 方式二：下载发行压缩包（GitHub Releases 页）
# 解压后目录即项目根：unzip CloudRail-BBS-v0.1.0.zip && cd CloudRail-BBS-v0.1.0
```

> **发行包签名验证**：GitHub Releases 中的压缩包带官方构建出处签名（attestation），
> 下载后可验证来源与完整性（需安装 [GitHub CLI](https://cli.github.com/)）：
>
> ```bash
> gh attestation verify CloudRail-BBS-v0.1.0.zip --repo liangan772/CloudRail-BBS
> # 输出 Signed artifact sha256:... 且 Verification succeeded 即通过
> ```

### 3. 后端安装与启动

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate；macOS/Linux: source .venv/bin/activate
./.venv/Scripts/activate

pip install -e ".[dev]"
# 国内网络建议加镜像：-i https://mirrors.aliyun.com/pypi/simple/

cp .env.example .env    # 修改 SECRET_KEY（必须）、DATABASE_URL 等
./run.sh                # 一键启动（自动建表 + 种子分类）；PowerShell 用 .\run.ps1
```

- API 文档：<http://localhost:8000/docs>
- 数据库选型：默认 SQLite（`backend/forum.db`）；使用 PostgreSQL 时修改 `DATABASE_URL` 并手动建库

```sql
-- PostgreSQL 手动建库（可选）
CREATE DATABASE forum;
CREATE USER forum WITH PASSWORD 'forum';
GRANT ALL PRIVILEGES ON DATABASE forum TO forum;
```

### 4. 前端安装与启动

```bash
cd frontend
npm install
npm run build           # 生产构建产物 dist/（发行包已自带，可跳过）
```

- **开发模式**：`npm run dev` → http://localhost:5173（/api 自动代理到 8000）
- **生产托管**：用 Nginx 托管 `frontend/dist` 并反代 `/api`（参考 `deploy/nginx/forum.conf`，将 `listen 8080` 改为 `listen 80`、`proxy_pass` 指向后端地址）

### 5. 验证与初始化

```bash
curl http://localhost:8000/health   # {"status":"ok",...}
curl http://localhost:8000/api/v1/site-config
```

浏览器打开前端地址 → **注册页创建账号（首个用户自动成为管理员）** → 首页发帖/评论 → 管理后台配置。

### 6. 生产运行注意事项

- **SECRET_KEY**：必须替换为随机 64 字节（`python -c "import secrets;print(secrets.token_urlsafe(48))"`），否则服务拒绝启动
- **Redis**：建议启用（验证码/限流/Refresh 吊销在 Redis 不可用时降级内存，多进程部署时需 Redis 共享状态）
- **HTTPS**：Nginx 配置 TLS 或使用反向代理网关
- **守护进程**：生产用 systemd / supervisor 托管 `uvicorn` 与 Celery Worker（`celery -A app.tasks.celery_app:celery_app worker`）

---

## 配置说明

后端环境变量（`backend/.env`，完整清单见开发文档 10.3 节）：

| 变量 | 说明 |
| --- | --- |
| `DATABASE_URL` | 数据库连接串：开发 `sqlite+aiosqlite:///./forum.db`；生产 `postgresql+asyncpg://...` |
| `REDIS_URL` | Redis 连接串（缓存 / Celery Broker） |
| `SECRET_KEY` | JWT 签名密钥（生产必须更换） |
| `ACCESS_TOKEN_EXPIRE_MINUTES` / `REFRESH_TOKEN_EXPIRE_DAYS` | Token 有效期 |
| `CORS_ORIGINS` | 允许的前端来源（逗号分隔） |
| `SMS_*` / `PUSH_*` / `OAUTH_*` | 短信 / 推送 / 第三方登录凭证（可选，规划中功能） |
| `AI_ENABLED` / `AI_BASE_URL` / `AI_API_KEY` / `AI_MODEL` | AI 审核开关与 LLM 供应商（OpenAI 兼容协议） |
| `AI_AUDIT_MODE` | 审核模式：`sync` 先审后发 / `async` 先发后审 / `off` 关闭 |
| `UVICORN_HOST` / `UVICORN_PORT` / `UVICORN_RELOAD` / `UVICORN_WORKERS` | Uvicorn 运行配置（由 `run.sh` / `run.ps1` 加载生效） |

## 文档

- [开发文档](docs/开发文档.md)（v1.3）：总体架构、功能需求、数据库设计（ER 图 + 表结构）、API 接口清单、缓存与队列设计、核心实现要点、部署方案、里程碑计划
- API 调试：后端启动后访问 <http://localhost:8000/docs>（自动生成 Swagger UI）

## 开发路线

| 阶段 | 内容 | 状态 |
| --- | --- | --- |
| M1 | 项目搭建（脚手架、CI、Docker 单镜像、数据库迁移基线） | ✅ |
| M2 | 用户体系（注册/登录/验证码/JWT/首用户管理员/强制登录） | ✅ |
| M3 | 内容与互动（帖子/评论/分类/匿名/详情，验证码保护） | ✅ |
| M6 | 管理后台（仪表盘/站点配置/角色权限） | 🚧 进行中 |
| M3+ | 点赞收藏、投票、草稿、搜索、富文本编辑器 | 🚧 规划中 |
| M4–M5 | 检索缓存、通知推送 | 🚧 规划中 |
| M7–M10 | 活跃度体系、APP 端（底部导航）、安全加固、上线 | 🚧 规划中 |

完整里程碑见开发文档第 12 章。

---

*当前状态：核心业务闭环（认证 / 内容 / 评论 / 后台配置）已实现并验证；其余功能按开发文档逐模块推进。*

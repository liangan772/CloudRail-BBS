"""管理后台（角色 >= 2 管理员）。

TODO（按文档 6.2）：
- GET    /admin/stats/overview            运营看板
- GET    /admin/users                      用户管理
- PUT    /admin/users/{id}/status          禁言/封禁/解封
- GET    /admin/posts                      审核列表
- PUT    /admin/posts/{id}/review          审核
- PUT    /admin/posts/{id}/pin|essence     置顶/加精
- POST   /admin/categories                 分类管理
- GET/POST/DELETE /admin/sensitive-words   敏感词管理
- GET/PUT /admin/config/gamification       激励配置
- GET/POST/PUT/DELETE /admin/banners       轮播图管理
- GET    /admin/reports                    举报队列
- PUT    /admin/reports/{id}               处理举报
- GET/PUT /admin/topics                    话题运营
"""

from fastapi import APIRouter

router = APIRouter(prefix="/admin", tags=["管理后台"])

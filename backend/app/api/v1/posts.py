"""帖子。

TODO（按文档 6.2；静态路径先于动态路径声明）：
- GET    /posts                 列表（分类/标签/排序/游标分页）
- POST   /posts                 发帖（支持 draft_id、投票、匿名）
- GET    /posts/hot             热门（Redis 缓存）
- GET    /posts/search?q=       搜索
- GET    /posts/recommend       推荐流
- GET    /posts/{id}            详情（含缓存）
- PUT    /posts/{id}            编辑
- DELETE /posts/{id}            删除（软删除）
- POST   /posts/{id}/like       点赞/取消
- POST   /posts/{id}/favorite   收藏/取消
- GET    /posts/{id}/comments   评论列表
- GET    /posts/{id}/poll       投票详情
- POST   /posts/{id}/vote       投票
"""

from fastapi import APIRouter

router = APIRouter(prefix="/posts", tags=["帖子"])

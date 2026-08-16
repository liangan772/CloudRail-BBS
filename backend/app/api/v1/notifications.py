"""通知。

TODO（按文档 6.2）：
- GET  /notifications            通知列表
- GET  /notifications/unread-count 未读数
- POST /notifications/read       标记已读
"""

from fastapi import APIRouter

router = APIRouter(prefix="/notifications", tags=["通知"])

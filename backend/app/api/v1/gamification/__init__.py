"""活跃度体系：签到 / 积分 / 任务 / 成就 / 排行榜 / 邀请 / Feed。

TODO（按文档 6.2）：
- POST /sign-in  每日签到
- GET  /sign-in/calendar?month=  签到日历
- GET  /points   积分余额与流水
- GET  /tasks    任务列表与进度
- POST /tasks/{id}/claim  领取奖励
- GET  /achievements  成就列表
- GET  /rank/points?period=  积分榜
- GET  /rank/sign   签到榜
- GET  /rank/contribution  贡献榜
- GET  /invites    邀请记录
- GET  /feed       关注动态流
"""

from fastapi import APIRouter

router = APIRouter(tags=["活跃度"])

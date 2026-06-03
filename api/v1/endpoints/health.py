# -*- coding: utf-8 -*-
"""
===================================
健康检查接口
===================================

职责：
1. 提供 /api/v1/health 健康检查接口
2. 用于负载均衡器和监控系统
"""

from datetime import datetime

from fastapi import APIRouter

from api.v1.schemas.common import HealthResponse, VersionResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    健康检查接口
    
    用于负载均衡器或监控系统检查服务状态
    
    Returns:
        HealthResponse: 包含服务状态和时间戳
    """
    return HealthResponse(
        status="ok",
        timestamp=datetime.now().isoformat()
    )


# 延迟导入避免循环依赖；_version_info 在 api.app 启动时注入
_version_info: dict = {"version": "1.0.0", "commit": None, "build_time": None}


def set_version_info(version: str, commit: str | None, build_time: str | None) -> None:
    """由 api.app 在启动时注入版本信息。"""
    _version_info["version"] = version
    _version_info["commit"] = commit
    _version_info["build_time"] = build_time


@router.get("/version", response_model=VersionResponse)
async def version_check() -> VersionResponse:
    """
    版本信息接口

    返回当前后端服务的版本号、Git commit hash 和构建时间，
    便于前端判断是否为最新版本。
    """
    return VersionResponse(
        version=_version_info["version"],
        commit=_version_info["commit"],
        build_time=_version_info["build_time"],
    )

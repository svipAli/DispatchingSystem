"""
统一 API 返回格式模块
-------------------
所有接口返回的 JSON 结构统一为 { code, message, data }。
- success()：成功响应，code=0
- paginate()：分页列表响应，data 中包含 items、total、page、page_size
- error()：错误响应，code 非 0
"""
from typing import Any, Generic, TypeVar
from pydantic import BaseModel

T = TypeVar("T")


class Response(BaseModel):
    """FastAPI 直接使用的返回模型（较少用，一般用下面的函数）"""
    code: int = 0
    message: str = "success"
    data: Any = None


class PageData(BaseModel, Generic[T]):
    """分页数据结构，items 是泛型列表"""
    items: list[T]
    total: int
    page: int
    page_size: int


def success(data: Any = None, message: str = "success") -> dict:
    """
    成功响应的快捷函数
    用法：return success(user_dict, message="创建成功")
    返回：{"code": 0, "message": "创建成功", "data": { ... }}
    """
    return {"code": 0, "message": message, "data": data}


def paginate(items: list, total: int, page: int, page_size: int) -> dict:
    """
    分页列表响应的快捷函数
    用法：return paginate(items, total=128, page=1, page_size=20)
    返回：{"code": 0, "message": "success", "data": {"items": [...], "total": 128, "page": 1, "page_size": 20}}
    """
    return {
        "code": 0,
        "message": "success",
        "data": {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        },
    }


def error(code: int = 1, message: str = "error", data: Any = None) -> dict:
    """
    错误响应的快捷函数
    用法：return error(code=1001, message="用户名已存在")
    返回：{"code": 1001, "message": "用户名已存在", "data": null}
    """
    return {"code": code, "message": message, "data": data}

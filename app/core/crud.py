"""
通用 CRUD 泛型基类
-----------------
所有模块的 CRUD 类都继承 BaseCRUD，只需传入模型类即可自动获得：
- get_by_id：按主键查一条
- get_list：分页列表（支持过滤条件）
- create：创建一条记录
- update：更新一条记录
- delete：软删除（status=False）或物理删除

子类只需写自己特有的查询方法（如 get_by_key、get_by_username）。
"""
from typing import Generic, TypeVar
from sqlalchemy import select, func, update as sa_update, delete as sa_delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import Base

# 泛型类型变量，绑定到 SQLAlchemy Base
ModelType = TypeVar("ModelType", bound=Base)


class BaseCRUD(Generic[ModelType]):
    """
    通用 CRUD 基类

    用法：
        class MyModelCRUD(BaseCRUD[MyModel]):
            def __init__(self):
                super().__init__(MyModel)
    """

    def __init__(self, model: type[ModelType]):
        """绑定要操作的 ORM 模型类"""
        self.model = model

    async def get_by_id(self, db: AsyncSession, id: int) -> ModelType | None:
        """按主键 ID 查询单条记录，不存在返回 None"""
        return await db.get(self.model, id)

    async def get_list(
        self,
        db: AsyncSession,
        *,
        page: int = 1,
        page_size: int = 20,
        status: bool | None = None,
        keyword: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        **filters,
    ) -> tuple[list[ModelType], int]:
        """
        分页查询列表

        :param db: 数据库会话
        :param page: 页码，从 1 开始
        :param page_size: 每页条数，默认 20
        :param status: 按状态过滤（None=不过滤）
        :param keyword: 关键字搜索（模糊匹配字符串字段）
        :param date_from: 创建时间起始 YYYY-MM-DD
        :param date_to: 创建时间截止 YYYY-MM-DD
        :param filters: 其他过滤条件，key=value 方式传入
        """
        from datetime import datetime
        conditions = []
        for key, value in filters.items():
            if value is not None and hasattr(self.model, key):
                conditions.append(getattr(self.model, key) == value)
        if status is not None and hasattr(self.model, 'status'):
            conditions.append(self.model.status == status)

        # 关键字搜索
        if keyword and keyword.strip():
            kw = f"%{keyword.strip()}%"
            from sqlalchemy import String, or_
            string_cols = [
                c for c in self.model.__table__.columns
                if isinstance(c.type, String)
            ]
            if string_cols:
                conditions.append(or_(*[c.ilike(kw) for c in string_cols]))

        # 日期范围过滤
        if date_from and hasattr(self.model, 'created_at'):
            conditions.append(self.model.created_at >= datetime.strptime(date_from, "%Y-%m-%d"))
        if date_to and hasattr(self.model, 'created_at'):
            conditions.append(self.model.created_at < datetime.strptime(date_to, "%Y-%m-%d").replace(hour=23, minute=59, second=59))

        # 基础查询（按 ID 降序，保证顺序稳定）
        base_stmt = select(self.model).where(*conditions).order_by(self.model.id.desc())

        # 查询总数
        count_stmt = select(func.count()).select_from(self.model).where(*conditions)
        total = (await db.execute(count_stmt)).scalar() or 0

        # 分页
        offset = (page - 1) * page_size
        stmt = base_stmt.offset(offset).limit(page_size)
        items = (await db.execute(stmt)).scalars().all()

        return list(items), total

    async def create(self, db: AsyncSession, **kwargs) -> ModelType:
        """
        创建一条新记录
        :param kwargs: 模型字段的 key=value
        :return: 创建后的模型对象（含自增 ID）
        """
        obj = self.model(**kwargs)
        db.add(obj)
        # flush 触发 INSERT 获得数据库生成的自增 ID，但不提交事务（由调用方控制）
        await db.flush()
        return obj

    async def update(self, db: AsyncSession, id: int, **kwargs) -> ModelType | None:
        """
        更新一条记录
        :param id: 主键
        :param kwargs: 要更新的字段 key=value
        :return: 更新后的模型对象，记录不存在返回 None
        """
        kwargs.pop("id", None)  # 防止意外修改主键
        await db.execute(
            sa_update(self.model).where(self.model.id == id).values(**kwargs)
        )
        return await self.get_by_id(db, id)

    async def delete(self, db: AsyncSession, id: int, soft: bool = True):
        """
        删除记录
        :param id: 主键
        :param soft: True=软删除（status=False），False=物理删除（DELETE）
        """
        if soft:
            await db.execute(
                sa_update(self.model)
                .where(self.model.id == id)
                .values(status=False)
            )
        else:
            await db.execute(sa_delete(self.model).where(self.model.id == id))

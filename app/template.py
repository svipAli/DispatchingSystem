"""
模板引擎单例
独立模块，避免 main.py 和 pages 之间的循环引用。
"""
from fastapi.templating import Jinja2Templates
from datetime import timedelta
from app.config import settings

templates = Jinja2Templates(directory="app/templates")
templates.env.globals["settings"] = settings
templates.env.globals["timedelta"] = timedelta

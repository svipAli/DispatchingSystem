FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# 启动脚本：自动迁移 + 启动服务
RUN echo '#!/bin/sh\n\
echo ">>> Running database migrations..."\n\
alembic upgrade head\n\
echo ">>> Checking admin account..."\n\
python init_admin.py\n\
echo ">>> Starting server..."\n\
exec uvicorn app.main:app --host 0.0.0.0 --port 8000\n\
' > /entrypoint.sh && chmod +x /entrypoint.sh

CMD ["/entrypoint.sh"]

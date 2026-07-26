FROM python:3.14-slim

WORKDIR /app

# 先安装依赖（利用 Docker 缓存层）
COPY apps/api/pyproject.toml ./pyproject.toml
RUN pip install --no-cache-dir alembic>=1.14,\<2 fastapi>=0.115,\<1 httpx>=0.27,\<1 openai>=1,\<2 \
    'psycopg[binary]>=3.2,<4' pydantic-settings>=2.6,\<3 python-multipart>=0.0.18,\<1 \
    openpyxl>=3.1,\<4 pandas>=2.2,\<3 python-docx>=1.1,\<2 pymupdf>=1.24,\<2 \
    pgvector>=0.3,\<1 sqlalchemy>=2.0,\<3 'uvicorn[standard]>=0.32,<1' \
    'python-pptx>=1.0,<2'

# 复制代码
COPY apps/api/app ./app
COPY apps/api/alembic ./alembic
COPY apps/api/alembic.ini ./alembic.ini

# 将当前目录加入 PYTHONPATH，让 alembic 能找到 app 模块
ENV PYTHONPATH=/app

EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"]

FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY pyproject.toml .

RUN pip install --no-cache-dir -e .

# 로컬 파일 캐시(코드코드 목록 등) 저장용 디렉터리
RUN mkdir -p /app/.cache
ENV MCP_CACHE_DIR=/app/.cache

# MCP는 stdio(표준입출력)로 통신하므로 별도 포트 노출 없음.
# 실행: docker run -i --rm --env-file .env korea-public-data-mcp
ENTRYPOINT ["python", "-m", "korea_public_data_mcp.server"]

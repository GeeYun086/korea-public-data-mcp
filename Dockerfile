FROM python:3.11-slim

WORKDIR /app

# 의존성만 먼저 설치해서 소스가 바뀌어도 이 레이어는 캐시를 타게 한다.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# pyproject.toml 의 readme 항목이 README.md 를 가리키므로 함께 복사해야 한다.
# (빠뜨리면 hatchling 메타데이터 생성이 실패한다)
COPY pyproject.toml README.md ./
COPY src/ ./src/

# 컨테이너 안에서는 소스를 고칠 일이 없으므로 일반 설치로 충분하다.
RUN pip install --no-cache-dir .

# 기업코드 목록·통계표 목록 같은 파일 캐시 저장 위치.
# 볼륨으로 연결하면 컨테이너를 다시 띄워도 재다운로드하지 않는다.
RUN mkdir -p /app/.cache
ENV MCP_CACHE_DIR=/app/.cache

# MCP는 stdio(표준입출력)로 통신하므로 노출할 포트가 없다.
# 인증키는 이미지에 굽지 말고 실행 시점에 주입한다:
#   docker run -i --rm --env-file .env korea-public-data-mcp
ENTRYPOINT ["python", "-m", "korea_public_data_mcp.server"]

# hwprest

`rhwp` 기반 HWP/HWPX 변환용 REST API 프로젝트입니다.

- API 서버: `rest_api`
- 변환 엔진: `rhwp`
- Swagger: `/docs`
- 업로드 테스트 페이지: `/test`

## 구성

- `/to_pdf`: PDF 변환
- `/to_png`: PNG 변환
- `/to_svg`: SVG 변환
- `/to_text`: TXT 변환
- `/to_md`: Markdown 변환

## 요구사항

- Python 3.12+
- Docker
- Linux/macOS 셸 환경

선택 사항:

- Rust/Cargo
  - `pdf`, `svg`, `txt`, `md`를 호스트에서 직접 실행할 때 사용

## 디렉토리

```text
.
├── README.md
├── rest_api
│   ├── app.py
│   ├── requirements.txt
│   ├── Dockerfile.native-skia
│   └── rhwp_png_docker.sh
└── rhwp
```

## 빠른 시작

### 1. Python 가상환경 준비

```bash
cd /home/youlsa/hwp_converter/rest_api
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

### 2. rhwp 빌드

호스트 변환용 바이너리를 먼저 빌드합니다.

```bash
cd /home/youlsa/hwp_converter/rhwp
. "$HOME/.cargo/env"
cargo build --release
```

빌드 결과:

```text
/home/youlsa/hwp_converter/rhwp/target/release/rhwp
```

### 3. PNG용 Docker 이미지 빌드

`/to_png`는 `native-skia` 경로를 사용하므로 Docker 이미지가 필요합니다.

```bash
docker build \
  -t rhwp-native-skia:latest \
  -f /home/youlsa/hwp_converter/rest_api/Dockerfile.native-skia \
  /home/youlsa/hwp_converter
```

### 4. 서버 실행

```bash
cd /home/youlsa/hwp_converter/rest_api
. .venv/bin/activate

RHWP_CMD=/home/youlsa/hwp_converter/rhwp/target/release/rhwp \
RHWP_PNG_CMD=/home/youlsa/hwp_converter/rest_api/rhwp_png_docker.sh \
uvicorn app:app --host 0.0.0.0 --port 8001
```

접속:

- Swagger: `http://localhost:8001/docs`
- 테스트 페이지: `http://localhost:8001/test`
- 헬스 체크: `http://localhost:8001/health`

## 엔드포인트

모든 변환 API는 `multipart/form-data`로 `file` 필드를 받습니다.

### PDF

```bash
curl -X POST \
  -F "file=@/path/to/sample.hwp" \
  http://localhost:8001/to_pdf \
  -o sample.pdf
```

### PNG

```bash
curl -X POST \
  -F "file=@/path/to/sample.hwp" \
  -F "page=0" \
  http://localhost:8001/to_png \
  -o sample.png
```

### SVG

```bash
curl -X POST \
  -F "file=@/path/to/sample.hwp" \
  -F "page=0" \
  http://localhost:8001/to_svg \
  -o sample.svg
```

### TXT

```bash
curl -X POST \
  -F "file=@/path/to/sample.hwp" \
  -F "page=0" \
  http://localhost:8001/to_text \
  -o sample.txt
```

### Markdown

```bash
curl -X POST \
  -F "file=@/path/to/sample.hwp" \
  -F "page=0" \
  http://localhost:8001/to_md \
  -o sample.zip
```

`/to_md`는 이미지 에셋이 함께 생길 수 있어서 zip으로 내려옵니다.

## 테스트 페이지 사용법

`/test` 페이지에서 다음 순서로 테스트할 수 있습니다.

1. `.hwp` 또는 `.hwpx` 파일 선택
2. 타입 선택: `pdf`, `png`, `svg`, `md`, `txt`
3. `변환` 버튼 클릭
4. 결과 파일 다운로드 확인

## 현재 동작 방식

- `/to_pdf`, `/to_svg`, `/to_text`, `/to_md`
  - 호스트의 `rhwp` 릴리스 바이너리 사용
- `/to_png`
  - `rest_api/rhwp_png_docker.sh`를 통해 Docker 내부 `native-skia` 경로 사용

## 문제 해결

### `cargo: command not found`

Rust 툴체인이 설치되지 않은 상태입니다.

```bash
curl https://sh.rustup.rs -sSf | sh -s -- -y
. "$HOME/.cargo/env"
```

### `/to_png`가 실패하는 경우

아래를 순서대로 확인합니다.

1. Docker 데몬이 실행 중인지 확인
2. `rhwp-native-skia:latest` 이미지가 빌드됐는지 확인
3. `RHWP_PNG_CMD=/home/youlsa/hwp_converter/rest_api/rhwp_png_docker.sh`로 서버를 실행했는지 확인

### `8001` 포트 충돌

다른 포트로 바꾸면 됩니다.

```bash
uvicorn app:app --host 0.0.0.0 --port 8010
```

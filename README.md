# hwprest

`rhwp` 기반 HWP/HWPX 변환 REST API입니다.  
`8001` 포트에서 `/docs`, `/test`, `/to_*` 엔드포인트를 단일 Docker 이미지로 서빙합니다.

## 엔드포인트

- `POST /to_pdf`
- `POST /to_png`
- `POST /to_svg`
- `POST /to_text`
- `POST /to_md`
- `GET /health`
- `GET /docs` (Swagger)
- `GET /test` (업로드 테스트 UI)

## 단일 이미지 기동

```bash
cd .
docker build -t hwprest:latest .
docker run --rm -p 8001:8001 hwprest:latest
```

이미지에는 한글 렌더링용 폰트(`Noto CJK`, `Nanum`, `Unfonts`)를 내장하고 `fc-cache`를 생성합니다.

접속:

- `http://localhost:8001/docs`
- `http://localhost:8001/test`
- `http://localhost:8001/health`

## 로컬(비 Docker) 기동

```bash
cd rhwp
. "$HOME/.cargo/env"
cargo build --release --features native-skia --target-dir /tmp/rhwp-target

cd ../rest_api
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt

RHWP_CMD=/tmp/rhwp-target/release/rhwp \
RHWP_CMD_NATIVE_SKIA=/tmp/rhwp-target/release/rhwp \
uvicorn app:app --host 0.0.0.0 --port 8001
```

## API 호출 예시

```bash
curl -X POST \
  -F "file=@/path/to/sample.hwp" \
  http://localhost:8001/to_pdf \
  -o sample.pdf
```

```bash
curl -X POST \
  -F "file=@/path/to/sample.hwp" \
  -F "page=0" \
  http://localhost:8001/to_png \
  -o sample.png
```

```bash
curl -X POST \
  -F "file=@/path/to/sample.hwp" \
  -F "page=0" \
  http://localhost:8001/to_md \
  -o sample.md
```

참고:

- `png`, `md`는 결과가 여러 파일이면 zip으로 응답됩니다.
- `/test` 페이지는 zip 응답을 `.zip` 확장자로 다운로드하도록 보정되어 있습니다.
- 폰트가 깨질 때는 `docker build --no-cache -t hwprest:latest .`로 이미지 재빌드를 먼저 수행하세요.

# rhwp REST API

`rhwp` 변환 엔진을 FastAPI로 감싼 서버입니다.

## 엔드포인트

- `POST /to_pdf`
- `POST /to_png`
- `POST /to_svg`
- `POST /to_text`
- `POST /to_md`
- `GET /health`
- `GET /docs`
- `GET /test`

모든 변환 API는 `multipart/form-data`로 `file` 필드를 받습니다.

## 권장 실행: 단일 Docker 이미지

프로젝트 루트에서:

```bash
docker build -t hwprest:latest .
docker run --rm -p 8001:8001 hwprest:latest
```

접속:

- Swagger: `http://localhost:8001/docs`
- 테스트 페이지: `http://localhost:8001/test`

## 로컬 실행

```bash
cd /home/youlsa/hwp_converter/rhwp
. "$HOME/.cargo/env"
cargo build --release --features native-skia --target-dir /tmp/rhwp-target

cd /home/youlsa/hwp_converter/rest_api
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt

RHWP_CMD=/tmp/rhwp-target/release/rhwp \
RHWP_CMD_NATIVE_SKIA=/tmp/rhwp-target/release/rhwp \
uvicorn app:app --host 0.0.0.0 --port 8001
```

## 참고

- `png`, `md`는 결과가 여러 파일이면 zip으로 응답됩니다.
- `/test` UI는 zip 응답을 `.zip` 확장자로 저장하도록 처리되어 있습니다.

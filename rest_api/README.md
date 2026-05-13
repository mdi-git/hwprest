# rhwp REST API

`rhwp` CLI를 감싸는 별도 FastAPI 서버입니다.

## 엔드포인트

- `POST /to_pdf`
- `POST /to_png`
- `POST /to_svg`
- `POST /to_text`
- `POST /to_md`
- `GET /health`

모든 변환 엔드포인트는 `multipart/form-data` 업로드를 사용합니다.

- 필수 필드: `file`
- 선택 필드: `page`
- `to_png` 추가 선택 필드: `scale`, `max_dimension`, `dpi`, `vlm_target`

## 동작 방식

- 기본적으로 내부에서 `cargo run --release --manifest-path ../rhwp/Cargo.toml -- ...`를 실행합니다.
- `/to_png`는 `native-skia`가 필요하므로 내부적으로 `--features native-skia`를 붙입니다.
- 단일 결과물은 원본 파일로 응답합니다.
- 여러 페이지 결과물은 `.zip`으로 묶어 응답합니다.
- `/to_md`는 이미지 에셋 디렉토리가 생길 수 있으므로 항상 `.zip`으로 응답합니다.

## 실행

```bash
cd /home/youlsa/hwp_converter/rest_api
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 8000
```

Swagger UI:

```text
http://localhost:8000/docs
```

## 환경변수

- `RHWP_CMD`
  - 기본 변환 명령 전체를 덮어씁니다.
  - 예: `RHWP_CMD="/path/to/rhwp"`
- `RHWP_PNG_CMD`
  - PNG 변환 명령 전체를 덮어씁니다.
  - 예: `RHWP_PNG_CMD="/path/to/rhwp"`
- `RHWP_CMD_NATIVE_SKIA`
  - `RHWP_PNG_CMD`가 없을 때 PNG 전용 명령을 덮어씁니다.

사전 빌드된 바이너리를 쓰고 싶다면 예를 들어:

```bash
export RHWP_CMD="/home/youlsa/hwp_converter/rhwp/target/release/rhwp"
export RHWP_PNG_CMD="/home/youlsa/hwp_converter/rhwp/target/release/rhwp"
```

단, PNG는 해당 바이너리가 `native-skia` feature로 빌드되어 있어야 합니다.

## 예시

```bash
curl -X POST \
  -F "file=@sample.hwp" \
  http://localhost:8000/to_pdf \
  -o sample.pdf
```

```bash
curl -X POST \
  -F "file=@sample.hwp" \
  -F "page=0" \
  http://localhost:8000/to_svg \
  -o sample.svg
```

```bash
curl -X POST \
  -F "file=@sample.hwp" \
  http://localhost:8000/to_png \
  -o sample_png.zip
```

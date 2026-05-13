from __future__ import annotations

import os
import shlex
import subprocess
import tempfile
import zipfile
import shutil
from pathlib import Path
from typing import Iterable

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import HTMLResponse
from starlette.background import BackgroundTask
from fastapi.responses import FileResponse


APP_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = APP_ROOT.parent
RHWP_ROOT = PROJECT_ROOT / "rhwp"
RHWP_MANIFEST = RHWP_ROOT / "Cargo.toml"

app = FastAPI(
    title="rhwp REST API",
    version="0.1.0",
    description="FastAPI wrapper around the rhwp CLI.",
)


def _default_rhwp_command(*, native_skia: bool = False) -> list[str]:
    cmd = [
        "cargo",
        "run",
        "--release",
        "--manifest-path",
        str(RHWP_MANIFEST),
    ]
    if native_skia:
        cmd.extend(["--features", "native-skia"])
    cmd.append("--")
    return cmd


def _resolve_rhwp_command(*, native_skia: bool = False) -> list[str]:
    env_name = "RHWP_PNG_CMD" if native_skia else "RHWP_CMD"
    configured = os.environ.get(env_name)
    if configured:
        return shlex.split(configured)

    if native_skia:
        configured = os.environ.get("RHWP_CMD_NATIVE_SKIA")
        if configured:
            return shlex.split(configured)

    return _default_rhwp_command(native_skia=native_skia)


def _safe_filename(name: str | None, default: str = "document.hwp") -> str:
    if not name:
        return default
    base = Path(name).name
    return base or default


def _save_upload(upload: UploadFile, target_dir: Path) -> Path:
    filename = _safe_filename(upload.filename)
    destination = target_dir / filename
    with destination.open("wb") as fh:
        while True:
            chunk = upload.file.read(1024 * 1024)
            if not chunk:
                break
            fh.write(chunk)
    return destination


def _run_rhwp(
    *,
    subcommand: str,
    input_path: Path,
    output_path: Path,
    page: int | None = None,
    extra_args: Iterable[str] | None = None,
    native_skia: bool = False,
) -> subprocess.CompletedProcess[str]:
    cmd = _resolve_rhwp_command(native_skia=native_skia)
    cmd.extend([subcommand, str(input_path), "-o", str(output_path)])

    if page is not None:
        cmd.extend(["-p", str(page)])

    if extra_args:
        cmd.extend(list(extra_args))

    try:
        return subprocess.run(
            cmd,
            cwd=str(PROJECT_ROOT),
            text=True,
            capture_output=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=500,
            detail=f"rhwp command is unavailable: {exc}",
        ) from exc


def _ensure_success(result: subprocess.CompletedProcess[str]) -> None:
    if result.returncode == 0:
        return

    detail = (result.stderr or result.stdout or "rhwp command failed").strip()
    raise HTTPException(status_code=500, detail=detail)


def _collect_files(output_dir: Path) -> list[Path]:
    return sorted(path for path in output_dir.rglob("*") if path.is_file())


def _zip_outputs(output_dir: Path, archive_path: Path) -> Path:
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in _collect_files(output_dir):
            zf.write(path, path.relative_to(output_dir))
    return archive_path


def _single_or_zip_response(
    *,
    output_dir: Path,
    download_stem: str,
    media_type_single: str,
    suffix_single: str,
    cleanup_dir: Path,
    always_zip: bool = False,
) -> FileResponse:
    files = _collect_files(output_dir)
    if not files:
        raise HTTPException(status_code=500, detail="No output files were generated.")

    if len(files) == 1 and not always_zip:
        file_path = files[0]
        return FileResponse(
            path=file_path,
            media_type=media_type_single,
            filename=f"{download_stem}{suffix_single}",
            background=BackgroundTask(shutil.rmtree, cleanup_dir, ignore_errors=True),
        )

    archive_path = output_dir.parent / f"{download_stem}.zip"
    _zip_outputs(output_dir, archive_path)
    return FileResponse(
        path=archive_path,
        media_type="application/zip",
        filename=archive_path.name,
        background=BackgroundTask(shutil.rmtree, cleanup_dir, ignore_errors=True),
    )


def _cleanup_tmpdir(tmpdir: Path) -> None:
    shutil.rmtree(tmpdir, ignore_errors=True)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/test", response_class=HTMLResponse)
def test_page() -> str:
    return """<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>rhwp API Test</title>
  <style>
    :root {
      --bg: #f4f1ea;
      --panel: #fffdf8;
      --ink: #1f2937;
      --muted: #6b7280;
      --line: #d6d0c4;
      --accent: #0f766e;
      --accent-strong: #115e59;
      --danger: #b42318;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: "Pretendard", "Noto Sans KR", sans-serif;
      background:
        radial-gradient(circle at top left, #efe4cf 0, transparent 32%),
        linear-gradient(180deg, #f7f3eb 0%, var(--bg) 100%);
      color: var(--ink);
      min-height: 100vh;
    }
    .wrap {
      max-width: 760px;
      margin: 0 auto;
      padding: 48px 20px 64px;
    }
    .card {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 20px;
      padding: 28px;
      box-shadow: 0 18px 50px rgba(36, 33, 27, 0.08);
    }
    h1 {
      margin: 0 0 10px;
      font-size: 32px;
      line-height: 1.1;
    }
    p {
      margin: 0 0 24px;
      color: var(--muted);
      line-height: 1.6;
    }
    label {
      display: block;
      margin: 0 0 8px;
      font-size: 14px;
      font-weight: 600;
    }
    input[type="file"],
    select {
      width: 100%;
      padding: 14px 16px;
      border: 1px solid var(--line);
      border-radius: 12px;
      background: #fff;
      font: inherit;
      color: var(--ink);
    }
    .field + .field {
      margin-top: 18px;
    }
    button {
      margin-top: 24px;
      width: 100%;
      padding: 15px 18px;
      border: 0;
      border-radius: 14px;
      background: var(--accent);
      color: #fff;
      font: inherit;
      font-weight: 700;
      cursor: pointer;
      transition: background 0.2s ease, transform 0.2s ease;
    }
    button:hover { background: var(--accent-strong); }
    button:disabled {
      cursor: wait;
      opacity: 0.7;
      transform: none;
    }
    .status {
      margin-top: 18px;
      min-height: 24px;
      font-size: 14px;
      color: var(--muted);
      white-space: pre-wrap;
    }
    .status.error { color: var(--danger); }
    .status.success { color: var(--accent-strong); }
    .hint {
      margin-top: 18px;
      padding: 14px 16px;
      border-radius: 12px;
      background: #f5f7f6;
      border: 1px solid #d7e3e1;
      font-size: 13px;
      color: #44525a;
      line-height: 1.5;
    }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="card">
      <h1>rhwp REST API Test</h1>
      <p>`.hwp` 또는 `.hwpx` 파일을 업로드하고 변환 타입을 선택한 뒤 직접 API를 테스트할 수 있습니다.</p>

      <form id="convert-form">
        <div class="field">
          <label for="file">파일 업로드</label>
          <input id="file" name="file" type="file" accept=".hwp,.hwpx" required />
        </div>

        <div class="field">
          <label for="type">변환 타입</label>
          <select id="type" name="type">
            <option value="pdf">pdf</option>
            <option value="png">png</option>
            <option value="svg">svg</option>
            <option value="md">md</option>
            <option value="txt">txt</option>
          </select>
        </div>

        <button id="submit" type="submit">변환</button>
      </form>

      <div id="status" class="status"></div>
      <div class="hint">
        결과는 브라우저에서 바로 다운로드됩니다. `png`, `md`처럼 여러 파일이 생길 수 있는 경우 zip으로 내려올 수 있습니다.
      </div>
    </div>
  </div>

  <script>
    const form = document.getElementById("convert-form");
    const fileInput = document.getElementById("file");
    const typeSelect = document.getElementById("type");
    const submitButton = document.getElementById("submit");
    const statusBox = document.getElementById("status");

    const endpointMap = {
      pdf: "/to_pdf",
      png: "/to_png",
      svg: "/to_svg",
      md: "/to_md",
      txt: "/to_text",
    };

    function setStatus(message, kind = "") {
      statusBox.textContent = message;
      statusBox.className = kind ? `status ${kind}` : "status";
    }

    function getFilename(disposition, fallbackName) {
      if (!disposition) return fallbackName;
      const match = disposition.match(/filename="?([^"]+)"?/i);
      return match ? match[1] : fallbackName;
    }

    form.addEventListener("submit", async (event) => {
      event.preventDefault();

      const file = fileInput.files[0];
      if (!file) {
        setStatus("파일을 선택하세요.", "error");
        return;
      }

      const type = typeSelect.value;
      const endpoint = endpointMap[type];
      const formData = new FormData();
      formData.append("file", file);

      submitButton.disabled = true;
      setStatus(`변환 중: ${endpoint}`, "");

      try {
        const response = await fetch(endpoint, {
          method: "POST",
          body: formData,
        });

        if (!response.ok) {
          let detail = `HTTP ${response.status}`;
          try {
            const data = await response.json();
            if (data.detail) detail = data.detail;
          } catch (_) {}
          throw new Error(detail);
        }

        const blob = await response.blob();
        const disposition = response.headers.get("content-disposition");
        const fallbackExt = type === "txt" ? "txt" : type;
        const fallbackName = `${file.name.replace(/\\.[^.]+$/, "")}.${fallbackExt}`;
        const downloadName = getFilename(disposition, fallbackName);
        const url = URL.createObjectURL(blob);
        const anchor = document.createElement("a");
        anchor.href = url;
        anchor.download = downloadName;
        document.body.appendChild(anchor);
        anchor.click();
        anchor.remove();
        URL.revokeObjectURL(url);

        setStatus(`완료: ${downloadName}`, "success");
      } catch (error) {
        setStatus(`실패: ${error.message}`, "error");
      } finally {
        submitButton.disabled = false;
      }
    });
  </script>
</body>
</html>
"""


@app.post("/to_pdf")
def to_pdf(
    file: UploadFile = File(...),
    page: int | None = Form(default=None),
) -> FileResponse:
    tmpdir = Path(tempfile.mkdtemp(prefix="rhwp_api_pdf_"))
    try:
        input_path = _save_upload(file, tmpdir)
        download_stem = input_path.stem
        output_path = tmpdir / f"{download_stem}.pdf"

        result = _run_rhwp(
            subcommand="export-pdf",
            input_path=input_path,
            output_path=output_path,
            page=page,
        )
        _ensure_success(result)

        if not output_path.exists():
            raise HTTPException(status_code=500, detail="PDF output was not generated.")

        return FileResponse(
            path=output_path,
            media_type="application/pdf",
            filename=output_path.name,
            background=BackgroundTask(_cleanup_tmpdir, tmpdir),
        )
    except Exception:
        _cleanup_tmpdir(tmpdir)
        raise


@app.post("/to_png")
def to_png(
    file: UploadFile = File(...),
    page: int | None = Form(default=None),
    scale: float | None = Form(default=None),
    max_dimension: int | None = Form(default=None),
    dpi: float | None = Form(default=None),
    vlm_target: str | None = Form(default=None),
) -> FileResponse:
    extra_args: list[str] = []
    if scale is not None:
        extra_args.extend(["--scale", str(scale)])
    if max_dimension is not None:
        extra_args.extend(["--max-dimension", str(max_dimension)])
    if dpi is not None:
        extra_args.extend(["--dpi", str(dpi)])
    if vlm_target:
        extra_args.extend(["--vlm-target", vlm_target])

    tmpdir = Path(tempfile.mkdtemp(prefix="rhwp_api_png_"))
    try:
        input_path = _save_upload(file, tmpdir)
        output_dir = tmpdir / "out"
        output_dir.mkdir(parents=True, exist_ok=True)

        result = _run_rhwp(
            subcommand="export-png",
            input_path=input_path,
            output_path=output_dir,
            page=page,
            extra_args=extra_args,
            native_skia=True,
        )
        _ensure_success(result)

        return _single_or_zip_response(
            output_dir=output_dir,
            download_stem=input_path.stem,
            media_type_single="image/png",
            suffix_single=".png",
            cleanup_dir=tmpdir,
        )
    except Exception:
        _cleanup_tmpdir(tmpdir)
        raise


@app.post("/to_svg")
def to_svg(
    file: UploadFile = File(...),
    page: int | None = Form(default=None),
) -> FileResponse:
    tmpdir = Path(tempfile.mkdtemp(prefix="rhwp_api_svg_"))
    try:
        input_path = _save_upload(file, tmpdir)
        output_dir = tmpdir / "out"
        output_dir.mkdir(parents=True, exist_ok=True)

        result = _run_rhwp(
            subcommand="export-svg",
            input_path=input_path,
            output_path=output_dir,
            page=page,
        )
        _ensure_success(result)

        return _single_or_zip_response(
            output_dir=output_dir,
            download_stem=input_path.stem,
            media_type_single="image/svg+xml",
            suffix_single=".svg",
            cleanup_dir=tmpdir,
        )
    except Exception:
        _cleanup_tmpdir(tmpdir)
        raise


@app.post("/to_text")
def to_text(
    file: UploadFile = File(...),
    page: int | None = Form(default=None),
) -> FileResponse:
    tmpdir = Path(tempfile.mkdtemp(prefix="rhwp_api_text_"))
    try:
        input_path = _save_upload(file, tmpdir)
        output_dir = tmpdir / "out"
        output_dir.mkdir(parents=True, exist_ok=True)

        result = _run_rhwp(
            subcommand="export-text",
            input_path=input_path,
            output_path=output_dir,
            page=page,
        )
        _ensure_success(result)

        return _single_or_zip_response(
            output_dir=output_dir,
            download_stem=input_path.stem,
            media_type_single="text/plain; charset=utf-8",
            suffix_single=".txt",
            cleanup_dir=tmpdir,
        )
    except Exception:
        _cleanup_tmpdir(tmpdir)
        raise


@app.post("/to_md")
def to_md(
    file: UploadFile = File(...),
    page: int | None = Form(default=None),
) -> FileResponse:
    tmpdir = Path(tempfile.mkdtemp(prefix="rhwp_api_md_"))
    try:
        input_path = _save_upload(file, tmpdir)
        output_dir = tmpdir / "out"
        output_dir.mkdir(parents=True, exist_ok=True)

        result = _run_rhwp(
            subcommand="export-markdown",
            input_path=input_path,
            output_path=output_dir,
            page=page,
        )
        _ensure_success(result)

        return _single_or_zip_response(
            output_dir=output_dir,
            download_stem=input_path.stem,
            media_type_single="text/markdown; charset=utf-8",
            suffix_single=".md",
            cleanup_dir=tmpdir,
        )
    except Exception:
        _cleanup_tmpdir(tmpdir)
        raise

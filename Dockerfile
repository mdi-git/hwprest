FROM rust:latest

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        python3 \
        python3-pip \
        python3-venv \
        clang \
        libfontconfig1-dev \
        libfreetype6-dev \
        fonts-noto-cjk \
        fonts-nanum \
        fonts-unfonts-core \
        pkg-config \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY rhwp /app/rhwp
COPY rest_api /app/rest_api

RUN mkdir -p /usr/local/share/fonts/rhwp \
    && cp -a /app/rhwp/web/fonts/. /usr/local/share/fonts/rhwp/ \
    && fc-cache -f -v

RUN cd /app/rhwp \
    && cargo build --release --features native-skia

RUN python3 -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir -r /app/rest_api/requirements.txt

ENV PYTHONUNBUFFERED=1
ENV RHWP_CMD=/app/rhwp/target/release/rhwp
ENV RHWP_CMD_NATIVE_SKIA=/app/rhwp/target/release/rhwp
ENV PATH=/opt/venv/bin:${PATH}

WORKDIR /app/rest_api
EXPOSE 8001

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8001"]

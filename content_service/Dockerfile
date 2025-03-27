FROM python:3.10-slim

WORKDIR /content_service

COPY content_service/requirements.txt /content_service/requirements.txt

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu torch==2.6.0+cpu \
    && pip install --no-cache-dir -r /content_service/requirements.txt \
    && rm -rf /root/.cache/pip

ENV HF_HOME="/content_service/hf_cache"

COPY content_service /content_service

EXPOSE 8002

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8002"]
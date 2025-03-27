FROM python:3.10-slim

WORKDIR /user_service

COPY user_service/requirements.txt /user_service/requirements.txt

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r /user_service/requirements.txt \
    && rm -rf /root/.cache/pip

COPY user_service /user_service

EXPOSE 8001

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
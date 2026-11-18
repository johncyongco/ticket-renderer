FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends fonts-dejavu-core libqrencode4 \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir 'Pillow>=10,<13'
WORKDIR /app
COPY renderer.py header.png ./
USER 65534
EXPOSE 8080
CMD ["python", "renderer.py"]

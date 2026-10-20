FROM python:3.13-slim
WORKDIR /app
COPY pyproject.toml README.md ./
COPY mender ./mender
COPY bench ./bench
RUN pip install --no-cache-dir -e . pytest \
    && useradd --create-home mender && chown -R mender /app
USER mender
ENTRYPOINT ["mender"]
CMD ["bench", "--provider", "reference"]

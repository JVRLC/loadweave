FROM python:3.14-slim
WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY loadweave ./loadweave
RUN pip install --no-cache-dir .
ENTRYPOINT ["loadweave"]
CMD ["--help"]


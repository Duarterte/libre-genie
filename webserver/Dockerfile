# --- Stage 1: Minify Assets ---
FROM node:18-alpine AS minifier
WORKDIR /src

# Install minification tools
RUN npm install -g html-minifier terser clean-css-cli

# Copy source assets
COPY html ./html
COPY static ./static

# Prepare output directory
RUN mkdir -p /dist/html

# 1. Minify HTML
RUN html-minifier --input-dir ./html --output-dir /dist/html \
    --collapse-whitespace \
    --remove-comments \
    --minify-css true \
    --minify-js true

# 2. Static Assets: Copy ALL first (preserving images, fonts, etc), then overwrite with minified versions
RUN cp -r ./static /dist/static

# 3. Minify CSS (Overwriting original)
RUN cleancss -o /dist/static/style.css ./static/style.css

# 4. Minify JS (Safely with error checking)
RUN for f in ./static/scripts/*.js; do \
        echo "Minifying $f..." && \
        terser "$f" --compress --mangle -o "/dist/static/scripts/$(basename "$f")" || exit 1; \
    done


# --- Stage 2: Final Python Image ---
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy Python Code (Server)
COPY *.py .
COPY quickinit.sh .

ENV PYTHONPATH=/app

# Copy Minified Assets from Stage 1
COPY --from=minifier /dist/html ./html
COPY --from=minifier /dist/static ./static

EXPOSE 8000

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]


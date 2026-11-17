# Stage 1: build the static site from Markdown and templates.
FROM python:3.12-slim AS build
WORKDIR /site
COPY site/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY site/ .
ARG PANORAMA_NOTICE=""
ENV PANORAMA_NOTICE=${PANORAMA_NOTICE}
RUN python build.py --out /dist

# Stage 2: serve it with nginx.
FROM nginx:1.27-alpine
COPY web/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /dist /usr/share/nginx/html

FROM python:3.7

COPY . /calibre-web/app
WORKDIR /calibre-web/app
RUN set -eux; \
  apt-get update; \
  apt-get install -y gosu libldap2-dev libsasl2-dev; \
  rm -rf /var/lib/apt/lists/*; \
  # verify that the binary works
  gosu nobody true; \
  pip install -r requirements.txt; \
  pip install -r optional-requirements.txt

ENV PUSER  500
ENV PGROUP 1000
EXPOSE 8083
VOLUME /config
VOLUME /books

HEALTHCHECK --interval=10s --timeout=5s --retries=3 \
CMD curl -f http://localhost:8083/ || exit 1

ENTRYPOINT ["/calibre-web/app/docker-entrypoint.sh"]

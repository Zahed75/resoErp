# resoERP — Docker image for Odoo 19 Enterprise-style multi-property resort ERP
FROM python:3.11-slim-bookworm

LABEL maintainer="Syscomatic LLC / ProspireNext" \
      description="resoERP - Odoo 19 based Resort & Hotel Management ERP"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

# ---- System dependencies ----
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        wget \
        gnupg \
        ca-certificates \
        git \
        libxml2-dev \
        libxslt1-dev \
        libjpeg-dev \
        zlib1g-dev \
        libfreetype6-dev \
        liblcms2-dev \
        libwebp-dev \
        libpq-dev \
        libldap2-dev \
        libsasl2-dev \
        libssl-dev \
        libffi-dev \
        node-less \
        npm \
        fonts-noto-cjk \
        xfonts-75dpi \
        xfonts-base \
        postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# ---- wkhtmltopdf (for PDF reports) ----
RUN ARCH=$(dpkg --print-architecture) && \
    curl -sSL -o /tmp/wkhtmltox.deb \
        "https://github.com/wkhtmltopdf/packaged/releases/download/0.12.6.1-3/wkhtmltox_0.12.6.1-3.bookworm_${ARCH}.deb" && \
    apt-get update && apt-get install -y --no-install-recommends /tmp/wkhtmltox.deb && \
    rm -rf /tmp/wkhtmltox.deb /var/lib/apt/lists/*

WORKDIR /opt/resoerp

# ---- Python dependencies ----
COPY requirements.txt /opt/resoerp/requirements.txt
RUN pip install --no-cache-dir -U pip wheel setuptools && \
    pip install --no-cache-dir -r requirements.txt

# ---- Application source ----
COPY odoo /opt/resoerp/odoo
COPY odoo-bin /opt/resoerp/odoo-bin
COPY custom_addons /opt/resoerp/custom_addons
COPY setup.py setup.cfg MANIFEST.in /opt/resoerp/
COPY docker/entrypoint.sh /entrypoint.sh
COPY docker/odoo.conf /etc/odoo/odoo.conf

RUN chmod +x /opt/resoerp/odoo-bin /entrypoint.sh && \
    mkdir -p /var/lib/odoo /var/log/odoo && \
    useradd -ms /bin/bash odoo && \
    chown -R odoo:odoo /opt/resoerp /var/lib/odoo /var/log/odoo /etc/odoo

USER odoo

EXPOSE 8069 8071 8072

VOLUME ["/var/lib/odoo"]

ENTRYPOINT ["/entrypoint.sh"]
CMD ["odoo"]

FROM python:3.10-slim

RUN apt-get update && \
    apt-get install -y software-properties-common && \
    apt-get install -y python3-pip
EXPOSE 8080
# Install unrar
ARG UNRAR_VERSION=6.2.12
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        g++ \
        make \
        curl
RUN mkdir /tmp/unrar && \
    curl -o \
        /tmp/unrar.tar.gz -L \
        "https://www.rarlab.com/rar/unrarsrc-${UNRAR_VERSION}.tar.gz"
RUN cd /tmp/unrar && \
    tar xf \
        /tmp/unrar.tar.gz -C \
        /tmp/unrar --strip-components=1 && \
   # sed -i 's|LDFLAGS=-pthread|LDFLAGS=-pthread -static|' makefile && \
    make && \
    make install

# install wget
RUN apt-get -y update
RUN apt-get -y install wget apt-utils gnupg
RUN apt-get update && \
    ## Download wkhtmltopdf
    curl -L https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6-1/wkhtmltox_0.12.6-1.stretch_amd64.deb \
        -o wkhtmltox_0.12.6-1.stretch_amd64.deb && \
    ## Install wkhtmltopdf dependency
    wget http://archive.ubuntu.com/ubuntu/pool/main/o/openssl/libssl1.1_1.1.0g-2ubuntu4_amd64.deb && \
    dpkg -i libssl1.1_1.1.0g-2ubuntu4_amd64.deb && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y -q --no-install-recommends     \
        xorg \
        xvfb \
        build-essential     \
        libfontconfig1-dev   \
        libfreetype6-dev     \
        libjpeg-dev    \
        libpng-dev     \
        libssl-dev     \
        libx11-dev     \
        libxext-dev    \
         libxrender-dev \
         zlib1g-dev \
         fontconfig \
         xfonts-75dpi \
         xfonts-base
RUN rm -rf /var/lib/apt/lists/* && \
    dpkg -i wkhtmltox_0.12.6-1.stretch_amd64.deb && \
    rm -f wkhtmltox_0.12.6-1.stretch_amd64.deb

# Cleanup
RUN apt-get remove -y g++ make curl && \
    apt-get -y autoremove && \
    apt-get clean
RUN rm -rf \
    /root/.cache \
    /tmp/* \
    /var/lib/apt/lists/* \
    /var/tmp/*
ENV PYTHONUNBUFFERED True
WORKDIR /app
COPY *.txt .
RUN pip install --no-cache-dir --upgrade pip -r requirements.txt
COPY . ./

CMD ["python3", "tg_input.py"]
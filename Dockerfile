FROM python:3.8-slim
EXPOSE 8080
# install wget
RUN apt-get -y update
RUN apt-get -y install wget apt-utils gnupg
RUN apt-get update && \
    apt-get -y install \
        curl && \
    ## Install wkhtmltopdf
    curl -L https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6-1/wkhtmltox_0.12.6-1.stretch_amd64.deb \
        -o wkhtmltox_0.12.6-1.stretch_amd64.deb && \
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
RUN apt-get -y autoremove && \
    apt-get clean

ENV PYTHONUNBUFFERED True
WORKDIR /app
COPY *.txt .
RUN pip install --no-cache-dir --upgrade pip -r requirements.txt
COPY . ./

CMD ["python", "tg_input.py"]
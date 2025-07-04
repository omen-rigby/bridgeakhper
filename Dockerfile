FROM python:3.12-slim

RUN apt-get update && \
    apt-get install -y software-properties-common && \
    apt-get install -y python3-pip
EXPOSE 8080
# Install unrar
ARG UNRAR_VERSION=6.2.12
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc \
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
# Install 7zip
RUN apt-get install -y --no-install-recommends p7zip-full && 7z -h
WORKDIR /app
ENV PYTHONUNBUFFERED True
COPY . ./
RUN pip3 install --no-cache-dir --upgrade pip -r requirements.txt
# Cleanup
RUN apt-get remove -y g++ gcc make curl && \
    apt-get -y autoremove && \
    apt-get clean
RUN rm -rf \
    /root/.cache \
    /tmp/* \
    /var/lib/apt/lists/* \
    /var/tmp/*

CMD ["python3", "tg_input.py"]
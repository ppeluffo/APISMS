FROM spymovil/commsv3_imagen_base:latest

WORKDIR /apisms
COPY *.py ./
COPY *.sql ./
COPY entrypoint.sh .
RUN chmod 777 /apisms/*
RUN mkdir -p /dbase/
ENTRYPOINT ["sh", "entrypoint.sh"]

EXPOSE 6000

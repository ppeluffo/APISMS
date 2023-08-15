FROM spymovil/commsv3_imagen_base:latest

WORKDIR /smsdaemon
COPY *.py ./
COPY entrypoint.sh .
RUN chmod 777 /smsdaemon/*
CMD ["python3", "-u", "/smsdaemon/sms_daemon.py"]
#ENTRYPOINT ["sh", "entrypoint.sh"]

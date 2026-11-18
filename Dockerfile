FROM python:3.11-slim

WORKDIR /app

COPY server.py /app/

ENV PORT=7000
EXPOSE 7000

CMD ["python", "server.py"]

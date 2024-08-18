FROM python:3.10

WORKDIR /usr/src/app

COPY requirements.txt .
RUN python3 -m venv venv
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN chmod +x main.py

CMD [ "python", "main.py" ]

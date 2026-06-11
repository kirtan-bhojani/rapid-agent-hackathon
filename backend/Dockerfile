FROM python:3.11-slim

# Install Node.js
RUN apt-get update && apt-get install -y curl

RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash -

RUN apt-get install -y nodejs

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

RUN npm install

EXPOSE 10000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "10000"]
FROM node:22-alpine3.18

WORKDIR /app

COPY package*.json .

RUN npm install

COPY --chown=node:node . .

EXPOSE 8080

CMD [ "node", "index.js" ]

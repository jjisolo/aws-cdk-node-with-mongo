FROM node:20

ARG GIT_HASH
ENV GIT_HASH=${GIT_HASH}

WORKDIR /usr/src/app

COPY package*.json ./

RUN npm install

COPY . .

EXPOSE 80 

CMD ["./entrypoint.sh"]

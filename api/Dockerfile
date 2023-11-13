FROM node:20

WORKDIR /usr/src/app

ARG GIT_HASH
ENV GIT_HASH=${GIT_HASH}

COPY package*.json ./

RUN npm install

COPY . .

EXPOSE 80 

CMD ["GIT_HASH=", GIT_HASH, "./entrypoint.sh"]

FROM node:20

WORKDIR /usr/src/app

RUN --mount=type=secret,id=git_hash
RUN GIT_HASH=$(cat /run/secrets/git_hash)

COPY package*.json ./

RUN npm install

COPY . .

EXPOSE 80 

CMD ["GIT_HASH=", "${GIT_HASH}", "./entrypoint.sh"]

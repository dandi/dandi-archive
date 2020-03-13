FROM node

COPY web/package.json /client/package.json
COPY web/yarn.lock /client/yarn.lock
WORKDIR /client
RUN yarn install --frozen-lockfile
COPY web /client
RUN yarn run build --mode docker

FROM nginx
RUN rm -rf /usr/share/nginx/html/*
COPY --from=0 /client/dist /usr/share/nginx/html

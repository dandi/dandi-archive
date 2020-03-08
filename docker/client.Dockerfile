FROM node

COPY web/package.json /client/package.json
WORKDIR /client
RUN npm install
COPY web /client
RUN yarn run build --mode docker

FROM nginx
RUN rm -rf /usr/share/nginx/html/*
COPY --from=0 /client/dist /usr/share/nginx/html
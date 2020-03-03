FROM node

COPY web /client
WORKDIR /client
RUN npm install
RUN yarn run build --mode docker

FROM nginx
COPY --from=0 /client/dist /usr/share/nginx/html
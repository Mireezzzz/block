# Кладёт dist/ в shared volume
# nginx подхватывает dist/ из того же volume.
FROM node:20-alpine

WORKDIR /app

COPY package.json ./
RUN npm install

COPY . .

RUN npm run build

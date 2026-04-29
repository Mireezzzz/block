# Этот контейнер существует только для сборки.
# Он запускается, делает "npm run build", кладёт dist/ в shared volume — и всё.
# nginx подхватывает dist/ из того же volume.
FROM node:20-alpine

WORKDIR /app

# Зависимости отдельно (кэш Docker)
COPY package.json ./
RUN npm install

# Исходный код
COPY . .

# Собираем. Результат → /app/dist/
RUN npm run build

# Этот контейнер не нужен после сборки.
# В docker-compose он помечен как "service" без restart,
# чтобы запустился один раз и завершился.
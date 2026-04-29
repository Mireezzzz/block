# Лёгкий официальный nginx образ (~50MB)
FROM nginx:alpine

# Убираем дефолтный конфиг nginx и кладём наш
RUN rm /etc/nginx/conf.d/default.conf
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Статика монтируется через volume из docker-compose,
# поэтому COPY dist/ здесь нет — папка появится при запуске
EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
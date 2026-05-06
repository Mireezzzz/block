# BLOCK

Инструмент для автоматического расчёта загрузки железобетонных изделий на полуприцеп. Распределяет грузы по рейсам, минимизирует их количество и балансирует центр тяжести.

## Стек

- Фронтенд - React 19 + TypeScript + Tailwind CSS 

- Бэкенд - Python 3.12 + Flask

- Веб-сервер - nginx 

- Контейнеры - Docker + Docker Compose

## Структура проекта

```
├── docker-compose.yml
├── .gitignore
├── backend/
│   ├── Dockerfile
│   ├── .dockerignore
│   ├── requirements.txt
│   ├── app.py          # Flask API
│   ├── optimizer.py    # алгоритм размещения
│   └── models.py       # структуры данных
├── frontend/
│   ├── Dockerfile
│   ├── .dockerignore
│   ├── vite.config.ts
│   ├── package.json
│   ├── index.html
│   └── src/
│       ├── App.tsx
│       ├── types.ts
│       ├── constants.ts
│       ├── index.css
│       ├── main.tsx
│       └── components/
│           └── TripVisualizer.tsx
└── nginx/
    ├── Dockerfile
    └── nginx.conf
```

Подробное описание слоёв, потока данных и контейнерной схемы см. в [ARCHITECTURE.md](ARCHITECTURE.md).

## Запуск

**Требования:** Docker и Docker Compose.

```bash
docker-compose up -d --build
```

Приложение откроется на [http://localhost](http://localhost).

## Как работает алгоритм

1. Все изделия разворачиваются в плоский список (с учётом `count`)
2. Начальная сортировка — тяжёлые и длинные первыми
3. **Имитация отжига** (600 итераций) подбирает оптимальный порядок укладки
4. Для каждого изделия ищется лучшая позиция на прицепе по критерию минимального отклонения центра тяжести от идеального (`idealCGFromRear = 7340 мм`)
5. Прицеп двухуровневый: нижняя палуба (11 180 мм) + верхняя «гусак» (3 500 мм)

## API

### `POST /api/optimize`

Тело запроса:
```json
{
  "items": [
    {
      "id": "1",
      "code": "ПТ",
      "name": "Плита перекрытия",
      "width": 2400,
      "length": 6940,
      "height": 160,
      "weight": 6779,
      "count": 5
    }
  ],
  "trailer": {
    "maxWeight": 24000,
    "totalWidth": 2400,
    "lowerLength": 11180,
    "lowerMaxHeight": 2950,
    "upperLength": 3500,
    "upperMaxHeight": 2600,
    "heightDiff": 350,
    "idealCGFromRear": 7340
  }
}
```

Поле `trailer` необязательно - без него используются параметры по умолчанию.

Ответ:
```json
{
  "trips": [
    {
      "id": 1,
      "totalWeight": 22593,
      "cgXFromRear": 7369.4,
      "cgMismatch": 29.4,
      "items": [...]
    }
  ]
}
```

### `GET /api/health`

Проверка доступности сервера. Используется Docker healthcheck.

## Локальная разработка (без Docker)

```bash
# Терминал 1 — бэкенд
cd backend
pip install -r requirements.txt
python app.py
# → http://localhost:5000

# Терминал 2 — фронтенд
cd frontend
npm install
npm run dev
# → http://localhost:3000
```

Vite автоматически проксирует `/api/*` на `localhost:5000` (настроено в `vite.config.ts`).
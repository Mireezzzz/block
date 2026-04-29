from flask import Flask, request, jsonify
from flask_cors import CORS
from backend.models import JBIItem, TrailerConfig
from backend.optimizer import calculate_optimizer

app = Flask(__name__)
CORS(app)  # разрешаем запросы с Vite dev server (порт 3000)

DEFAULT_TRAILER = TrailerConfig(
    max_weight=24000,
    total_width=2400,
    lower_length=11180,
    lower_max_height=2950,
    upper_length=3500,
    upper_max_height=2600,
    height_diff=350,
    ideal_cg_from_rear=7340,
)


@app.route("/api/optimize", methods=["POST"])
def optimize():
    """
    Принимает:
        {
          "items": [ { id, code, name, width, length, height, weight, count } ],
          "trailer": { maxWeight, totalWidth, lowerLength, ... }   // необязательно
        }
    Возвращает:
        { "trips": [ Trip, ... ] }
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "No JSON body"}), 400

    # Парсим items
    raw_items = data.get("items", [])
    items = []
    for it in raw_items:
        items.append(JBIItem(
            id=str(it["id"]),
            code=it["code"],
            name=it["name"],
            width=float(it["width"]),
            length=float(it["length"]),
            height=float(it["height"]),
            weight=float(it["weight"]),
            count=int(it["count"]),
        ))

    # Парсим trailer (или используем дефолтный)
    raw_trailer = data.get("trailer")
    if raw_trailer:
        trailer = TrailerConfig(
            max_weight=float(raw_trailer["maxWeight"]),
            total_width=float(raw_trailer["totalWidth"]),
            lower_length=float(raw_trailer["lowerLength"]),
            lower_max_height=float(raw_trailer["lowerMaxHeight"]),
            upper_length=float(raw_trailer["upperLength"]),
            upper_max_height=float(raw_trailer["upperMaxHeight"]),
            height_diff=float(raw_trailer["heightDiff"]),
            ideal_cg_from_rear=float(raw_trailer["idealCGFromRear"]),
        )
    else:
        trailer = DEFAULT_TRAILER

    trips = calculate_optimizer(items, trailer)
    return jsonify({"trips": [t.to_dict() for t in trips]})


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(port=5000, debug=True)
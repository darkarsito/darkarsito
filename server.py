from flask import Flask, request, render_template_string, jsonify
import base64
from datetime import datetime, timedelta
import random
import json
import os

app = Flask(__name__)

LICENCIAS_FILE = "licencias.json"
USO_FILE = "licencias_en_uso.json"

# Cargar datos desde archivos o inicializar vacíos
def cargar_json(file_path):
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def guardar_json(file_path, data):
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# Convertir string ISO a datetime
def str_a_datetime(fecha_str):
    return datetime.fromisoformat(fecha_str)

# Convertir datetime a string ISO
def datetime_a_str(dt):
    return dt.isoformat()

# Cargar licencias
licencias_raw = cargar_json(LICENCIAS_FILE)
licencias = {lic: str_a_datetime(fecha) for lic, fecha in licencias_raw.items()}

# Cargar licencias en uso
uso_raw = cargar_json(USO_FILE)
licencias_en_uso = {}
for lic, datos in uso_raw.items():
    licencias_en_uso[lic] = {
        "pc_name": datos["pc_name"],
        "mb_id": datos["mb_id"],
        "fecha_uso": str_a_datetime(datos["fecha_uso"])
    }

# Generador de licencias
def generar_codigo_licencia(dias_validez: int) -> str:
    fecha_exp = (datetime.now() + timedelta(days=dias_validez)).strftime("%Y-%m-%d")
    b64_fecha = base64.b64encode(fecha_exp.encode()).decode()

    p1 = ''.join(random.choices("ABCDEFGHJKLMNPQRSTUVWXYZ23456789", k=6))
    p2 = ''.join(random.choices("ABCDEFGHJKLMNPQRSTUVWXYZ23456789", k=7))
    p3 = ''.join(random.choices("ABCDEFGHJKLMNPQRSTUVWXYZ23456789", k=8))

    licencia = f"{p1}-{p2}-{p3}-{b64_fecha}"
    return licencia

index_html = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Gestión Licencias</title>
    <style>
        body { font-family: Arial, sans-serif; padding: 20px; max-width: 900px; margin: auto; }
        table { border-collapse: collapse; width: 100%; margin-bottom: 30px; }
        th, td { border: 1px solid #ccc; padding: 8px; text-align: left; }
        th { background-color: #eee; }
        .btn { padding: 8px 15px; background-color: #007bff; color: white; border: none; cursor: pointer; font-weight: bold; }
        .btn:hover { background-color: #0056b3; }
        .section { margin-bottom: 50px; }
        h1, h2 { color: #333; }
        p { font-size: 1.1em; }
        .success { color: green; font-weight: bold; }
    </style>
</head>
<body>
    <h1>Gestión de Licencias</h1>

    <div class="section">
        <h2>Generar Nueva Licencia</h2>
        <form method="POST" action="/generar">
            <label for="dias">Días de validez:</label>
            <select name="dias" id="dias" required>
                <option value="7">7 días</option>
                <option value="15">15 días</option>
                <option value="30">30 días</option>
            </select>
            <button class="btn" type="submit">Generar Licencia</button>
        </form>
        {% if nueva_licencia %}
            <p class="success">Licencia generada: <code>{{ nueva_licencia }}</code></p>
        {% endif %}
    </div>

    <div class="section">
        <h2>Licencias Generadas</h2>
        {% if licencias %}
        <table>
            <thead>
                <tr><th>Licencia</th><th>Fecha Expiración</th></tr>
            </thead>
            <tbody>
            {% for lic, fecha in licencias.items() %}
                <tr>
                    <td><code>{{ lic }}</code></td>
                    <td>{{ fecha.strftime("%Y-%m-%d") }}</td>
                </tr>
            {% endfor %}
            </tbody>
        </table>
        {% else %}
            <p>No hay licencias generadas.</p>
        {% endif %}
    </div>

    <div class="section">
        <h2>Licencias en Uso</h2>
        {% if licencias_en_uso %}
        <table>
            <thead>
                <tr><th>Licencia</th><th>PC Nombre</th><th>ID Motherboard</th><th>Fecha de Uso</th></tr>
            </thead>
            <tbody>
            {% for lic, datos in licencias_en_uso.items() %}
                <tr>
                    <td><code>{{ lic }}</code></td>
                    <td>{{ datos['pc_name'] }}</td>
                    <td>{{ datos['mb_id'] }}</td>
                    <td>{{ datos['fecha_uso'].strftime("%Y-%m-%d %H:%M:%S") }}</td>
                </tr>
            {% endfor %}
            </tbody>
        </table>
        {% else %}
            <p>No hay licencias en uso.</p>
        {% endif %}
    </div>
</body>
</html>
"""

@app.route("/", methods=["GET"])
def index():
    return render_template_string(index_html, licencias=licencias, licencias_en_uso=licencias_en_uso)

@app.route("/generar", methods=["POST"])
def generar():
    try:
        dias = int(request.form.get("dias", 7))
    except ValueError:
        dias = 7
    nueva_lic = generar_codigo_licencia(dias)
    fecha_exp = datetime.now() + timedelta(days=dias)
    licencias[nueva_lic] = fecha_exp
    # Guardar licencias actualizadas
    licencias_serializable = {k: datetime_a_str(v) for k,v in licencias.items()}
    guardar_json(LICENCIAS_FILE, licencias_serializable)
    return render_template_string(index_html, licencias=licencias, licencias_en_uso=licencias_en_uso, nueva_licencia=nueva_lic)

@app.route("/validar", methods=["POST"])
def validar():
    data = request.json
    if not data:
        return jsonify({"estado": "error", "mensaje": "No se recibieron datos JSON."}), 400

    licencia = data.get("licencia")
    pc_name = data.get("pc_name")
    mb_id = data.get("mb_id")

    if not licencia or not pc_name or not mb_id:
        return jsonify({"estado": "error", "mensaje": "Faltan campos obligatorios."}), 400

    if licencia not in licencias:
        return jsonify({"estado": "error", "mensaje": "Licencia no existe."}), 400

    fecha_exp = licencias[licencia]
    if datetime.now() > fecha_exp:
        return jsonify({"estado": "error", "mensaje": "Licencia expirada."}), 400

    # Verifica si licencia ya está en uso por otro equipo
    if licencia in licencias_en_uso:
        uso = licencias_en_uso[licencia]
        if uso["pc_name"] != pc_name or uso["mb_id"] != mb_id:
            return jsonify({"estado": "error", "mensaje": "Licencia ya está en uso en otro equipo."}), 400

    # Registrar uso o actualizar fecha
    licencias_en_uso[licencia] = {
        "pc_name": pc_name,
        "mb_id": mb_id,
        "fecha_uso": datetime.now()
    }

    # Guardar licencias en uso actualizadas
    uso_serializable = {
        lic: {
            "pc_name": datos["pc_name"],
            "mb_id": datos["mb_id"],
            "fecha_uso": datetime_a_str(datos["fecha_uso"])
        }
        for lic, datos in licencias_en_uso.items()
    }
    guardar_json(USO_FILE, uso_serializable)

    return jsonify({"estado": "ok", "mensaje": "Licencia validada correctamente."})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

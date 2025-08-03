from flask import Flask, request, render_template_string, jsonify
import base64
from datetime import datetime, timedelta
import random
import json
import os
import threading
import subprocess
import json
app = Flask(__name__)

LICENCIAS_FILE = "licencias.json"
USO_FILE = "licencias_en_uso.json"

# Cargar datos desde archivos o inicializar vacíos
def cargar_json(file_path):
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def hacer_commit_y_push(mensaje_commit="Actualizado licencias.json automáticamente"):
    try:
        # Configura usuario Git si no está configurado
        subprocess.run(["git", "config", "user.name", "darkarsito"], check=True)
        subprocess.run(["git", "config", "user.email", "blizzobm@gmail.com"], check=True)

        # Agrega y comitea cambios
        subprocess.run(["git", "add", "."], check=True)
        subprocess.run(["git", "commit", "-m", mensaje_commit], check=True)

        # Construye URL remota con token
        token = os.getenv("GITHUB_TOKEN")
        if not token:
            print("⚠️ No se encontró GITHUB_TOKEN en las variables de entorno.")
            return

        repo_url = f"https://{token}@github.com/darkarsito/darkarsito.git"
        subprocess.run(["git", "remote", "set-url", "origin", repo_url], check=True)

        # Empuja los cambios
        subprocess.run(["git", "push", "origin", "main"], check=True)
        print("✅ Cambios empujados correctamente.")
    
    except subprocess.CalledProcessError as e:
        print(f"⚠️ Error al hacer commit/push automático: {e}")

def guardar_json(file_path, data):
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    # Ejecutar git commit/push en hilo aparte para no bloquear
    threading.Thread(target=hacer_commit_y_push, args=(file_path,)).start()

def str_a_datetime(fecha_str):
    return datetime.fromisoformat(fecha_str)

def datetime_a_str(dt):
    return dt.isoformat()

licencias_raw = cargar_json(LICENCIAS_FILE)
licencias = {lic: str_a_datetime(fecha) for lic, fecha in licencias_raw.items()}

uso_raw = cargar_json(USO_FILE)
licencias_en_uso = {}
for lic, datos in uso_raw.items():
    licencias_en_uso[lic] = {
        "pc_name": datos["pc_name"],
        "mb_id": datos["mb_id"],
        "fecha_uso": str_a_datetime(datos["fecha_uso"])
    }

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
        .danger { background-color: #dc3545; }
        .danger:hover { background-color: #a71d2a; }
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

    <div class="section">
        <h2>Eliminar Todas las Licencias</h2>
        <form id="eliminarForm" method="POST" action="/eliminar_todo?token=midesecreto123" onsubmit="return confirm('¿Estás seguro de eliminar todas las licencias?');">
            <button class="btn danger" type="submit">🗑️ Eliminar Todas las Licencias</button>
        </form>
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
    licencias_serializable = {k: datetime_a_str(v) for k, v in licencias.items()}
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

    if licencia in licencias_en_uso:
        uso = licencias_en_uso[licencia]
        if uso["pc_name"] != pc_name or uso["mb_id"] != mb_id:
            return jsonify({"estado": "error", "mensaje": "Licencia ya está en uso en otro equipo."}), 400

    licencias_en_uso[licencia] = {
        "pc_name": pc_name,
        "mb_id": mb_id,
        "fecha_uso": datetime.now()
    }

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

@app.route("/eliminar_todo", methods=["POST"])
def eliminar_todo():
    token = request.args.get("token")
    if token != "midesecreto123":
        return jsonify({"estado": "error", "mensaje": "Token inválido"}), 403

    licencias.clear()
    licencias_en_uso.clear()
    guardar_json(LICENCIAS_FILE, {})
    guardar_json(USO_FILE, {})
    return render_template_string(index_html, licencias=licencias, licencias_en_uso=licencias_en_uso, nueva_licencia=None)

if __name__ == "__main__":
    puerto = int(os.environ.get("PORT", 5000))  # toma la variable PORT o 5000 si no existe
    app.run(host="0.0.0.0", port=puerto, debug=True)

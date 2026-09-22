from flask import Flask, render_template, request, redirect, url_for
import sqlite3
from pathlib import Path
import math
import time

import requests
from ortools.constraint_solver import pywrapcp, routing_enums_pb2

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "rotas.db"

app = Flask(__name__)
app.secret_key = "projeto-rotas-academico"

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "ProjetoRotasAcademico/2.4 (projeto academico)"
_last_geocode_request = 0.0


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS caminhoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            placa TEXT NOT NULL UNIQUE,
            capacidade_kg REAL NOT NULL,
            status TEXT NOT NULL DEFAULT 'Disponível'
        );

        CREATE TABLE IF NOT EXISTS pedidos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente TEXT NOT NULL,
            endereco TEXT NOT NULL,
            cidade TEXT,
            latitude REAL,
            longitude REAL,
            endereco_geocodificado TEXT,
            peso_kg REAL NOT NULL,
            prazo TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Pendente'
        );
        """
    )

    # Migração simples de versões anteriores.
    colunas = {
        row["name"] for row in conn.execute("PRAGMA table_info(pedidos)").fetchall()
    }
    if "cidade" not in colunas:
        conn.execute("ALTER TABLE pedidos ADD COLUMN cidade TEXT")
    if "latitude" not in colunas:
        conn.execute("ALTER TABLE pedidos ADD COLUMN latitude REAL")
    if "longitude" not in colunas:
        conn.execute("ALTER TABLE pedidos ADD COLUMN longitude REAL")
    if "endereco_geocodificado" not in colunas:
        conn.execute("ALTER TABLE pedidos ADD COLUMN endereco_geocodificado TEXT")

    conn.commit()
    conn.close()


def hora_para_minutos(hora):
    h, m = map(int, hora.split(":"))
    return h * 60 + m


def minutos_para_hora(minutos):
    minutos = max(0, int(minutos))
    return f"{minutos // 60:02d}:{minutos % 60:02d}"


def geocodificar_endereco(endereco, cidade=""):
    """
    Converte texto de endereço em latitude/longitude usando Nominatim.

    O serviço público deve ser usado com baixa frequência. Por isso a função
    aguarda pelo menos ~1 segundo entre consultas feitas por este processo.
    """
    global _last_geocode_request

    endereco = endereco.strip()
    cidade = (cidade or "").strip()

    if not endereco:
        return None, "Informe o endereço."

    consulta = f"{endereco}, {cidade}, Brasil" if cidade else f"{endereco}, Brasil"

    agora = time.monotonic()
    espera = 1.05 - (agora - _last_geocode_request)
    if espera > 0:
        time.sleep(espera)

    try:
        resposta = requests.get(
            NOMINATIM_URL,
            params={
                "q": consulta,
                "format": "jsonv2",
                "limit": 1,
                "countrycodes": "br",
                "addressdetails": 1,
            },
            headers={"User-Agent": USER_AGENT},
            timeout=10,
        )
        _last_geocode_request = time.monotonic()
        resposta.raise_for_status()
    except requests.RequestException as exc:
        _last_geocode_request = time.monotonic()
        return None, f"Não foi possível consultar o serviço de mapas: {exc}"

    resultados = resposta.json()
    if not resultados:
        return None, "Endereço não encontrado. Confira o endereço e a cidade/UF."

    item = resultados[0]
    try:
        latitude = float(item["lat"])
        longitude = float(item["lon"])
    except (KeyError, TypeError, ValueError):
        return None, "O serviço de mapas não retornou coordenadas válidas."

    return {
        "latitude": latitude,
        "longitude": longitude,
        "display_name": item.get("display_name", consulta),
    }, None


def distancia_entre_pontos(lat1, lon1, lat2, lon2):
    if None in (lat1, lon1, lat2, lon2):
        return None

    raio_terra = 6371.0
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)

    a = (
        math.sin(dp / 2) ** 2
        + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    )
    return 2 * raio_terra * math.asin(math.sqrt(a))


def construir_matriz(pedidos):
    # Coordenada inicial do depósito do protótipo.
    deposito = (-20.3155, -40.3128)
    pontos = [deposito]

    for pedido in pedidos:
        if pedido["latitude"] is None or pedido["longitude"] is None:
            return None
        pontos.append((float(pedido["latitude"]), float(pedido["longitude"])))

    matriz = []
    for lat1, lon1 in pontos:
        linha = []
        for lat2, lon2 in pontos:
            if lat1 == lat2 and lon1 == lon2:
                linha.append(0.0)
            else:
                linha.append(round(distancia_entre_pontos(lat1, lon1, lat2, lon2), 3))
        matriz.append(linha)
    return matriz


def minutos_de_viagem(distancia_km):
    # Estimativa simples para o protótipo. A V2.5 poderá usar tempos pelas ruas.
    return max(1, round((distancia_km / 35) * 60))


def otimizar(pedidos, caminhoes):
    if not pedidos:
        return {"erro": "Não existem pedidos pendentes."}
    if not caminhoes:
        return {"erro": "Não existem caminhões disponíveis."}

    matriz_km = construir_matriz(pedidos)
    if matriz_km is None:
        return {"erro": "Todos os pedidos precisam estar geocodificados."}

    n = len(pedidos) + 1
    matriz_tempo = [
        [minutos_de_viagem(matriz_km[i][j]) if i != j else 0 for j in range(n)]
        for i in range(n)
    ]

    demandas = [0] + [int(p["peso_kg"]) for p in pedidos]
    capacidades = [int(c["capacidade_kg"]) for c in caminhoes]

    janelas = [(360, 1080)]
    for pedido in pedidos:
        janelas.append((360, hora_para_minutos(pedido["prazo"])))

    manager = pywrapcp.RoutingIndexManager(n, len(caminhoes), 0)
    routing = pywrapcp.RoutingModel(manager)

    def demanda_callback(index):
        return demandas[manager.IndexToNode(index)]

    demanda_index = routing.RegisterUnaryTransitCallback(demanda_callback)
    routing.AddDimensionWithVehicleCapacity(
        demanda_index,
        0,
        capacidades,
        True,
        "Capacity",
    )

    def tempo_callback(from_index, to_index):
        origem = manager.IndexToNode(from_index)
        destino = manager.IndexToNode(to_index)
        deslocamento = matriz_tempo[origem][destino]
        servico = 10 if origem != 0 else 0
        return deslocamento + servico

    tempo_index = routing.RegisterTransitCallback(tempo_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(tempo_index)
    routing.AddDimension(tempo_index, 720, 1080, False, "Time")

    time_dimension = routing.GetDimensionOrDie("Time")
    for node, janela in enumerate(janelas):
        index = manager.NodeToIndex(node)
        time_dimension.CumulVar(index).SetRange(janela[0], janela[1])

    # Custos fixos tornam o uso de menos caminhões preferível, sem permitir rota vazia.
    for vehicle_id in range(len(caminhoes)):
        routing.SetFixedCostOfVehicle(1000, vehicle_id)

    params = pywrapcp.DefaultRoutingSearchParameters()
    params.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    params.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    params.time_limit.seconds = 5

    solution = routing.SolveWithParameters(params)
    if not solution:
        return {
            "erro": (
                "Não foi encontrada uma solução viável. "
                "Verifique capacidades, prazos e endereços."
            )
        }

    rotas = []
    pedidos_atendidos = set()
    distancia_total = 0.0

    for vehicle_id, caminhao in enumerate(caminhoes):
        index = routing.Start(vehicle_id)
        if solution.Value(routing.NextVar(index)) == routing.End(vehicle_id):
            continue

        carga_total = 0
        paradas = []
        pontos_rota = [[-20.3155, -40.3128]]
        ordem = 1

        while not routing.IsEnd(index):
            node = manager.IndexToNode(index)
            chegada = solution.Value(time_dimension.CumulVar(index))

            if node != 0:
                pedido = pedidos[node - 1]
                pedidos_atendidos.add(pedido["id"])
                carga_total += int(pedido["peso_kg"])
                pontos_rota.append([
                    float(pedido["latitude"]),
                    float(pedido["longitude"])
                ])

                paradas.append({
                    "pedido_id": pedido["id"],
                    "cliente": pedido["cliente"],
                    "endereco": pedido["endereco"],
                    "latitude": float(pedido["latitude"]),
                    "longitude": float(pedido["longitude"]),
                    "peso_kg": int(pedido["peso_kg"]),
                    "prazo": pedido["prazo"],
                    "chegada": minutos_para_hora(chegada),
                    "atraso": chegada > hora_para_minutos(pedido["prazo"]),
                    "ordem": ordem,
                })
                ordem += 1

            next_index = solution.Value(routing.NextVar(index))
            a = manager.IndexToNode(index)
            b = manager.IndexToNode(next_index)
            distancia_total += matriz_km[a][b]
            index = next_index

        pontos_rota.append([-20.3155, -40.3128])

        rotas.append({
            "caminhao_id": caminhao["id"],
            "placa": caminhao["placa"],
            "capacidade_kg": int(caminhao["capacidade_kg"]),
            "carga_kg": carga_total,
            "ocupacao": round((carga_total / caminhao["capacidade_kg"]) * 100, 1),
            "paradas": paradas,
            "pontos_rota": pontos_rota,
        })

    if len(pedidos_atendidos) != len(pedidos):
        return {"erro": "A solução não conseguiu atender todos os pedidos."}

    atrasos = sum(
        1 for rota in rotas for parada in rota["paradas"] if parada["atraso"]
    )

    return {
        "rotas": rotas,
        "pedidos_atendidos": len(pedidos_atendidos),
        "caminhoes_utilizados": len(rotas),
        "distancia_total": round(distancia_total, 2),
        "atrasos": atrasos,
    }


def carregar_dados():
    conn = get_db()
    caminhoes = conn.execute(
        "SELECT * FROM caminhoes ORDER BY id DESC"
    ).fetchall()
    pedidos = conn.execute(
        "SELECT * FROM pedidos ORDER BY prazo"
    ).fetchall()
    conn.close()
    return caminhoes, pedidos


def render_inicio(resultado=None, mensagem=None, tipo="info"):
    caminhoes, pedidos = carregar_dados()
    return render_template(
        "index.html",
        caminhoes=caminhoes,
        pedidos=pedidos,
        resultado=resultado,
        mensagem=mensagem,
        tipo_mensagem=tipo,
    )


@app.route("/")
def index():
    return render_inicio()


@app.post("/caminhoes")
def adicionar_caminhao():
    placa = request.form["placa"].strip().upper()
    try:
        capacidade = float(request.form["capacidade_kg"])
        if not placa or capacidade <= 0:
            raise ValueError
    except ValueError:
        return render_inicio(mensagem="Informe uma placa e uma capacidade válida.", tipo="error")

    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO caminhoes (placa, capacidade_kg) VALUES (?, ?)",
            (placa, capacidade),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return render_inicio(mensagem="Essa placa já está cadastrada.", tipo="error")
    conn.close()
    return redirect(url_for("index"))


@app.post("/pedidos")
def adicionar_pedido():
    cliente = request.form["cliente"].strip()
    endereco = request.form["endereco"].strip()
    cidade = request.form.get("cidade", "").strip()

    try:
        peso = float(request.form["peso_kg"])
        if not cliente or not endereco or peso <= 0:
            raise ValueError
    except ValueError:
        return render_inicio(mensagem="Confira cliente, endereço e peso.", tipo="error")

    prazo = request.form["prazo"]

    geocodificado, erro = geocodificar_endereco(endereco, cidade)
    if erro:
        return render_inicio(mensagem=erro, tipo="error")

    conn = get_db()
    conn.execute(
        """
        INSERT INTO pedidos
        (cliente, endereco, cidade, latitude, longitude,
         endereco_geocodificado, peso_kg, prazo)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            cliente,
            endereco,
            cidade,
            geocodificado["latitude"],
            geocodificado["longitude"],
            geocodificado["display_name"],
            peso,
            prazo,
        ),
    )
    conn.commit()
    conn.close()

    mensagem = (
        f"Pedido cadastrado. Localização encontrada: "
        f"{geocodificado['display_name']}"
    )
    return render_inicio(mensagem=mensagem, tipo="success")


@app.post("/caminhoes/<int:caminhao_id>/excluir")
def excluir_caminhao(caminhao_id):
    conn = get_db()
    conn.execute("DELETE FROM caminhoes WHERE id = ?", (caminhao_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("index"))


@app.post("/pedidos/<int:pedido_id>/excluir")
def excluir_pedido(pedido_id):
    conn = get_db()
    conn.execute("DELETE FROM pedidos WHERE id = ?", (pedido_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("index"))


@app.post("/otimizar")
def executar_otimizacao():
    conn = get_db()
    pedidos = conn.execute(
        "SELECT * FROM pedidos WHERE status = 'Pendente' ORDER BY prazo"
    ).fetchall()
    caminhoes = conn.execute(
        "SELECT * FROM caminhoes WHERE status = 'Disponível'"
    ).fetchall()
    conn.close()

    resultado = otimizar(pedidos, caminhoes)
    return render_inicio(resultado=resultado)


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
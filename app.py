from flask import Flask, render_template, request, redirect, url_for
import sqlite3
from pathlib import Path

from ortools.constraint_solver import pywrapcp, routing_enums_pb2

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "rotas.db"

app = Flask(__name__)


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.executescript("""
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
            peso_kg REAL NOT NULL,
            prazo TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Pendente'
        );

        CREATE TABLE IF NOT EXISTS rotas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            caminhao_id INTEGER NOT NULL,
            ordem INTEGER NOT NULL,
            pedido_id INTEGER NOT NULL,
            chegada_min INTEGER NOT NULL,
            FOREIGN KEY (caminhao_id) REFERENCES caminhoes(id),
            FOREIGN KEY (pedido_id) REFERENCES pedidos(id)
        );
    """)
    conn.commit()
    conn.close()


def hora_para_minutos(hora):
    """Converte HH:MM para minutos desde meia-noite."""
    h, m = map(int, hora.split(":"))
    return h * 60 + m


def minutos_para_hora(minutos):
    return f"{minutos // 60:02d}:{minutos % 60:02d}"


def construir_dados(pedidos, caminhoes):
    """
    Constrói um problema pequeno de roteamento.
    Como os pedidos ainda não têm coordenadas reais, usamos uma matriz
    fictícia baseada no índice dos pontos. Isso mantém a V2 simples.
    """
    n = len(pedidos) + 1  # + depósito
    distance_matrix = [[0] * n for _ in range(n)]

    # Distâncias fictícias assimétricas em minutos.
    # Futuramente será substituída por uma matriz real.
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            distance_matrix[i][j] = 5 + abs(i - j) * 4

    demands = [0] + [int(p["peso_kg"]) for p in pedidos]

    # Depósito: operação das 06:00 às 18:00.
    time_windows = [(360, 1080)]
    for p in pedidos:
        limite = hora_para_minutos(p["prazo"])
        # Nesta V2, a entrega pode ocorrer a partir das 06:00 até o prazo.
        time_windows.append((360, limite))

    service_time = [0] + [10 for _ in pedidos]

    capacities = [int(c["capacidade_kg"]) for c in caminhoes]

    return {
        "distance_matrix": distance_matrix,
        "demands": demands,
        "time_windows": time_windows,
        "service_time": service_time,
        "vehicle_capacities": capacities,
        "num_vehicles": len(caminhoes),
        "depot": 0,
    }


def otimizar(pedidos, caminhoes):
    if not pedidos:
        return {"erro": "Não existem pedidos pendentes."}

    if not caminhoes:
        return {"erro": "Não existem caminhões disponíveis."}

    data = construir_dados(pedidos, caminhoes)

    manager = pywrapcp.RoutingIndexManager(
        len(data["distance_matrix"]),
        data["num_vehicles"],
        data["depot"]
    )
    routing = pywrapcp.RoutingModel(manager)

    # Capacidade
    def demanda_callback(index):
        node = manager.IndexToNode(index)
        return data["demands"][node]

    demanda_index = routing.RegisterUnaryTransitCallback(demanda_callback)

    routing.AddDimensionWithVehicleCapacity(
        demanda_index,
        0,
        data["vehicle_capacities"],
        True,
        "Capacity"
    )

    # Tempo
    def tempo_callback(from_index, to_index):
        origem = manager.IndexToNode(from_index)
        destino = manager.IndexToNode(to_index)
        deslocamento = data["distance_matrix"][origem][destino]
        servico = data["service_time"][origem]
        return deslocamento + servico

    tempo_index = routing.RegisterTransitCallback(tempo_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(tempo_index)

    routing.AddDimension(
        tempo_index,
        720,  # espera permitida
        1080, # limite máximo do dia
        False,
        "Time"
    )

    time_dimension = routing.GetDimensionOrDie("Time")

    for node, janela in enumerate(data["time_windows"]):
        index = manager.NodeToIndex(node)
        time_dimension.CumulVar(index).SetRange(janela[0], janela[1])

    # Incentiva o uso de menos caminhões.
    for vehicle_id in range(data["num_vehicles"]):
        routing.SetFixedCostOfVehicle(100, vehicle_id)

    params = pywrapcp.DefaultRoutingSearchParameters()
    params.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    )
    params.local_search_metaheuristic = (
        routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    )
    params.time_limit.seconds = 5

    solution = routing.SolveWithParameters(params)

    if not solution:
        return {
            "erro": (
                "Não foi encontrada uma solução viável. "
                "Verifique capacidade dos caminhões e prazos."
            )
        }

    resultado = []
    pedidos_atendidos = set()
    distancia_total = 0

    for vehicle_id, caminhao in enumerate(caminhoes):
        index = routing.Start(vehicle_id)

        # Caminhão não utilizado.
        if solution.Value(routing.NextVar(index)) == routing.End(vehicle_id):
            continue

        carga_total = 0
        paradas = []

        while not routing.IsEnd(index):
            node = manager.IndexToNode(index)
            chegada = solution.Value(time_dimension.CumulVar(index))

            if node != 0:
                pedido = pedidos[node - 1]
                pedido_id = pedido["id"]
                pedidos_atendidos.add(pedido_id)

                carga_total += int(pedido["peso_kg"])

                paradas.append({
                    "pedido_id": pedido_id,
                    "cliente": pedido["cliente"],
                    "endereco": pedido["endereco"],
                    "peso_kg": int(pedido["peso_kg"]),
                    "prazo": pedido["prazo"],
                    "chegada": minutos_para_hora(chegada),
                    "chegada_min": chegada,
                })

            next_index = solution.Value(routing.NextVar(index))

            if not routing.IsEnd(next_index):
                a = manager.IndexToNode(index)
                b = manager.IndexToNode(next_index)
                distancia_total += data["distance_matrix"][a][b]

            index = next_index

        resultado.append({
            "caminhao_id": caminhao["id"],
            "placa": caminhao["placa"],
            "capacidade_kg": int(caminhao["capacidade_kg"]),
            "carga_kg": carga_total,
            "ocupacao": round((carga_total / caminhao["capacidade_kg"]) * 100, 1),
            "paradas": paradas,
        })

    if len(pedidos_atendidos) != len(pedidos):
        return {"erro": "A solução encontrada não atendeu todos os pedidos."}

    return {
        "rotas": resultado,
        "pedidos_atendidos": len(pedidos_atendidos),
        "caminhoes_utilizados": len(resultado),
        "distancia_total": distancia_total,
    }


@app.route("/")
def index():
    conn = get_db()

    caminhoes = conn.execute(
        "SELECT * FROM caminhoes ORDER BY id DESC"
    ).fetchall()

    pedidos = conn.execute(
        "SELECT * FROM pedidos ORDER BY id DESC"
    ).fetchall()

    conn.close()

    resultado = None
    return render_template(
        "index.html",
        caminhoes=caminhoes,
        pedidos=pedidos,
        resultado=resultado
    )


@app.post("/caminhoes")
def adicionar_caminhao():
    placa = request.form["placa"].strip().upper()
    capacidade = float(request.form["capacidade_kg"])

    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO caminhoes (placa, capacidade_kg) VALUES (?, ?)",
            (placa, capacidade)
        )
        conn.commit()
    except sqlite3.IntegrityError:
        pass
    finally:
        conn.close()

    return redirect(url_for("index"))


@app.post("/pedidos")
def adicionar_pedido():
    cliente = request.form["cliente"].strip()
    endereco = request.form["endereco"].strip()
    peso = float(request.form["peso_kg"])
    prazo = request.form["prazo"]

    conn = get_db()
    conn.execute(
        """
        INSERT INTO pedidos (cliente, endereco, peso_kg, prazo)
        VALUES (?, ?, ?, ?)
        """,
        (cliente, endereco, peso, prazo)
    )
    conn.commit()
    conn.close()

    return redirect(url_for("index"))


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

    # Renderiza a página diretamente com o resultado.
    conn = get_db()
    caminhoes_todos = conn.execute(
        "SELECT * FROM caminhoes ORDER BY id DESC"
    ).fetchall()
    pedidos_todos = conn.execute(
        "SELECT * FROM pedidos ORDER BY id DESC"
    ).fetchall()
    conn.close()

    return render_template(
        "index.html",
        caminhoes=caminhoes_todos,
        pedidos=pedidos_todos,
        resultado=resultado
    )


if __name__ == "__main__":
    init_db()
    app.run(debug=True)

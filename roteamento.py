"""Motor de roteamento: monta o problema de VRP e resolve com OR-Tools.

Usa distância/duração real por estrada (API pública OSRM), com fallback em
linha reta (haversine) quando a API não responde ou não acha rota para um
par de pontos.
"""
from ortools.constraint_solver import pywrapcp, routing_enums_pb2

from enderecos import haversine_km, matriz_rotas

# Velocidade média assumida para converter distância (km) em tempo de
# deslocamento (min) no fallback, quando a API OSRM não está disponível.
VELOCIDADE_MEDIA_KMH = 30


def hora_para_minutos(hora):
    """Converte HH:MM para minutos desde meia-noite."""
    h, m = map(int, hora.split(":"))
    return h * 60 + m


def minutos_para_hora(minutos):
    return f"{minutos // 60:02d}:{minutos % 60:02d}"


def construir_dados(pedidos, caminhoes, deposito):
    """
    Constrói o problema de roteamento a partir de coordenadas reais.
    As coordenadas do depósito e dos pedidos vêm da geocodificação
    (API pública Nominatim/OpenStreetMap). A distância/duração entre os
    pontos vem da API pública OSRM (rota real por estrada); se a API não
    responder (ou não achar rota para algum par), cai para a estimativa em
    linha reta (haversine) com velocidade média fixa.
    """
    n = len(pedidos) + 1  # + depósito
    coordenadas = [(deposito["latitude"], deposito["longitude"])]
    coordenadas += [(p["latitude"], p["longitude"]) for p in pedidos]

    matriz_osrm = matriz_rotas(coordenadas)
    distancias_km = matriz_osrm[0] if matriz_osrm else None
    duracoes_min = matriz_osrm[1] if matriz_osrm else None

    distance_matrix = [[0] * n for _ in range(n)]
    distancia_km_matrix = [[0] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            if i == j:
                continue

            km = distancias_km[i][j] if distancias_km else None
            minutos = duracoes_min[i][j] if duracoes_min else None

            if km is None or minutos is None:
                lat1, lon1 = coordenadas[i]
                lat2, lon2 = coordenadas[j]
                km = haversine_km(lat1, lon1, lat2, lon2)
                minutos = km / VELOCIDADE_MEDIA_KMH * 60

            distancia_km_matrix[i][j] = round(km, 1)
            distance_matrix[i][j] = max(round(minutos), 1)

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
        "distancia_km_matrix": distancia_km_matrix,
        "coordenadas": coordenadas,
        "demands": demands,
        "time_windows": time_windows,
        "service_time": service_time,
        "vehicle_capacities": capacities,
        "num_vehicles": len(caminhoes),
        "depot": 0,
    }


def otimizar(pedidos, caminhoes, deposito):
    if deposito is None or deposito["latitude"] is None:
        return {
            "erro": (
                "Cadastre e geocodifique o endereço do depósito antes de "
                "otimizar as rotas."
            )
        }

    if not pedidos:
        return {"erro": "Não existem pedidos pendentes com endereço geocodificado."}

    if not caminhoes:
        return {"erro": "Não existem caminhões disponíveis."}

    data = construir_dados(pedidos, caminhoes, deposito)

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

    # Torna cada pedido "opcional": se não houver como encaixá-lo (capacidade
    # ou prazo), o solver paga uma penalidade alta em vez de descartar toda a
    # solução. Isso evita o tudo-ou-nada de antes.
    penalidade_pedido_nao_atendido = 1_000_000
    for node in range(1, len(data["distance_matrix"])):
        routing.AddDisjunction(
            [manager.NodeToIndex(node)], penalidade_pedido_nao_atendido
        )

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
        no_anterior = 0  # depósito
        distancia_acumulada_km = 0

        while not routing.IsEnd(index):
            node = manager.IndexToNode(index)
            chegada = solution.Value(time_dimension.CumulVar(index))

            if node != 0:
                pedido = pedidos[node - 1]
                pedido_id = pedido["id"]
                pedidos_atendidos.add(pedido_id)

                carga_total += int(pedido["peso_kg"])

                distancia_km = data["distancia_km_matrix"][no_anterior][node]
                distancia_acumulada_km = round(distancia_acumulada_km + distancia_km, 1)

                paradas.append({
                    "pedido_id": pedido_id,
                    "cliente": pedido["cliente"],
                    "endereco": pedido["endereco"],
                    "peso_kg": int(pedido["peso_kg"]),
                    "prazo": pedido["prazo"],
                    "chegada": minutos_para_hora(chegada),
                    "chegada_min": chegada,
                    "distancia_km": distancia_km,
                    "distancia_acumulada_km": distancia_acumulada_km,
                })
                no_anterior = node

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

    pedidos_nao_atendidos = [
        {"cliente": p["cliente"], "endereco": p["endereco"]}
        for p in pedidos if p["id"] not in pedidos_atendidos
    ]

    return {
        "rotas": resultado,
        "pedidos_atendidos": len(pedidos_atendidos),
        "pedidos_nao_atendidos": pedidos_nao_atendidos,
        "caminhoes_utilizados": len(resultado),
        "distancia_total": distancia_total,
    }

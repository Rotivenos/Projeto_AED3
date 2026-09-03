from ortools.constraint_solver import pywrapcp, routing_enums_pb2


def criar_dados():
    # Distâncias/tempos fictícios em minutos.
    # A posição 0 representa o depósito.
    data = {
        "distance_matrix": [
            [0, 10, 18, 22, 15, 28],
            [10, 0, 12, 20, 17, 25],
            [18, 12, 0, 14, 16, 21],
            [22, 20, 14, 0, 11, 19],
            [15, 17, 16, 11, 0, 13],
            [28, 25, 21, 19, 13, 0],
        ],
        "demands": [0, 2000, 3000, 4000, 2000, 3000],
        "time_windows": [
            (0, 720),   # depósito: 00:00-12:00
            (420, 540), # A: 07:00-09:00
            (480, 600), # B: 08:00-10:00
            (540, 660), # C: 09:00-11:00
            (570, 690), # D: 09:30-11:30
            (600, 720), # E: 10:00-12:00
        ],
        "service_time": [0, 15, 15, 20, 15, 15],
        "vehicle_capacities": [10000, 10000, 10000],
        "num_vehicles": 3,
        "depot": 0,
        "names": [
            "Deposito",
            "Cliente A",
            "Cliente B",
            "Cliente C",
            "Cliente D",
            "Cliente E",
        ],
    }
    return data


def minutos_para_hora(minutos):
    horas = minutos // 60
    mins = minutos % 60
    return f"{horas:02d}:{mins:02d}"


def formatar_distancia(valor):
    return f"{valor} min de deslocamento"


def resolver_rotas(data):
    manager = pywrapcp.RoutingIndexManager(
        len(data["distance_matrix"]),
        data["num_vehicles"],
        data["depot"],
    )
    routing = pywrapcp.RoutingModel(manager)

    # -------------------------
    # Restrição de capacidade
    # -------------------------
    def demanda_callback(from_index):
        node = manager.IndexToNode(from_index)
        return data["demands"][node]

    demand_callback_index = routing.RegisterUnaryTransitCallback(demanda_callback)
    routing.AddDimensionWithVehicleCapacity(
        demand_callback_index,
        0,  # sem capacidade extra
        data["vehicle_capacities"],
        True,
        "Capacity",
    )

    # -------------------------
    # Dimensão de tempo
    # -------------------------
    def tempo_callback(from_index, to_index):
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        deslocamento = data["distance_matrix"][from_node][to_node]
        servico = data["service_time"][from_node]
        return deslocamento + servico

    transit_callback_index = routing.RegisterTransitCallback(tempo_callback)

    # O custo principal será o tempo/distância total.
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    routing.AddDimension(
        transit_callback_index,
        120,  # espera máxima permitida antes de um cliente
        24 * 60,
        False,
        "Time",
    )

    time_dimension = routing.GetDimensionOrDie("Time")

    for node, window in enumerate(data["time_windows"]):
        index = manager.NodeToIndex(node)
        time_dimension.CumulVar(index).SetRange(window[0], window[1])

    # Permitir que o veículo espere quando chegar antes da janela.
    for vehicle_id in range(data["num_vehicles"]):
        start_index = routing.Start(vehicle_id)
        end_index = routing.End(vehicle_id)
        time_dimension.CumulVar(start_index).SetRange(360, 720)  # 06:00-12:00
        time_dimension.CumulVar(end_index).SetRange(360, 900)    # 06:00-15:00

    # -------------------------
    # Forçar uso de veículos somente se houver pedidos
    # -------------------------
    # Um veículo vazio não precisa ser usado.
    # A rota será considerada vazia se Start == End.
    # O OR-Tools decide automaticamente quantos veículos utilizar.
    # Para evitar penalização excessiva por usar veículo, damos
    # um custo fixo moderado de uso.
    for vehicle_id in range(data["num_vehicles"]):
        routing.SetFixedCostOfVehicle(50, vehicle_id)

    # -------------------------
    # Estratégia de busca
    # -------------------------
    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    )
    search_parameters.local_search_metaheuristic = (
        routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    )
    search_parameters.time_limit.seconds = 5

    solution = routing.SolveWithParameters(search_parameters)

    if not solution:
        return None

    rotas = []

    for vehicle_id in range(data["num_vehicles"]):
        index = routing.Start(vehicle_id)
        if solution.Value(routing.NextVar(index)) == routing.End(vehicle_id):
            # Veículo não utilizado.
            continue

        carga = 0
        sequencia = []
        distancia_total = 0
        chegada_anterior = solution.Value(time_dimension.CumulVar(index))

        while not routing.IsEnd(index):
            node = manager.IndexToNode(index)
            time_value = solution.Value(time_dimension.CumulVar(index))

            sequencia.append({
                "node": node,
                "nome": data["names"][node],
                "chegada": time_value,
                "janela": data["time_windows"][node],
                "demanda": data["demands"][node],
            })

            carga += data["demands"][node]

            next_index = solution.Value(routing.NextVar(index))
            if not routing.IsEnd(next_index):
                next_node = manager.IndexToNode(next_index)
                distancia_total += data["distance_matrix"][node][next_node]

            index = next_index

        # Registrar o depósito de retorno.
        end_time = solution.Value(time_dimension.CumulVar(index))
        rotas.append({
            "veiculo": vehicle_id + 1,
            "sequencia": sequencia,
            "carga": carga,
            "capacidade": data["vehicle_capacities"][vehicle_id],
            "distancia": distancia_total,
            "hora_saida": sequencia[0]["chegada"] if sequencia else chegada_anterior,
            "hora_retorno": end_time,
        })

    return rotas


def validar_rotas(rotas, data):
    problemas = []

    for rota in rotas:
        if rota["carga"] <= 0:
            problemas.append(
                f"Veículo C{rota['veiculo']} saiu vazio."
            )

        if rota["carga"] > rota["capacidade"]:
            problemas.append(
                f"Veículo C{rota['veiculo']} excedeu a capacidade."
            )

        for parada in rota["sequencia"]:
            if parada["node"] == data["depot"]:
                continue

            chegada = parada["chegada"]
            inicio, fim = parada["janela"]

            if chegada > fim:
                problemas.append(
                    f"{parada['nome']} recebeu chegada às "
                    f"{minutos_para_hora(chegada)}, após o limite "
                    f"{minutos_para_hora(fim)}."
                )

    return problemas


def imprimir_resultado(rotas, data):
    print("\n" + "=" * 65)
    print("SISTEMA DE OTIMIZAÇÃO DE ROTAS DE ENTREGA")
    print("=" * 65)

    if not rotas:
        print("Nenhuma rota foi encontrada.")
        return

    total_distancia = sum(r["distancia"] for r in rotas)
    total_pedidos = sum(len(r["sequencia"]) - 1 for r in rotas)  # desconta depósito
    total_carga = sum(r["carga"] for r in rotas)

    print(f"Caminhões utilizados: {len(rotas)}")
    print(f"Pedidos atendidos:    {total_pedidos}")
    print(f"Tempo/distância total: {formatar_distancia(total_distancia)}")
    print(f"Carga total:           {total_carga:,} kg")

    print("\nROTAS")
    print("-" * 65)

    for rota in rotas:
        print(f"\nCaminhão C{rota['veiculo']}")
        print(
            f"Saída: {minutos_para_hora(rota['hora_saida'])} | "
            f"Retorno: {minutos_para_hora(rota['hora_retorno'])}"
        )
        print(
            f"Carga: {rota['carga']:,}/{rota['capacidade']:,} kg "
            f"({rota['carga'] / rota['capacidade'] * 100:.1f}%)"
        )
        print(f"Distância/tempo: {formatar_distancia(rota['distancia'])}")

        print("Sequência:")
        for i, parada in enumerate(rota["sequencia"]):
            if parada["node"] == data["depot"]:
                print(f"  {i + 1}. {parada['nome']}")
            else:
                janela_ini, janela_fim = parada["janela"]
                print(
                    f"  {i + 1}. {parada['nome']} | "
                    f"Chegada: {minutos_para_hora(parada['chegada'])} | "
                    f"Janela: {minutos_para_hora(janela_ini)}-"
                    f"{minutos_para_hora(janela_fim)} | "
                    f"Carga: {parada['demanda']:,} kg"
                )


def main():
    data = criar_dados()
    rotas = resolver_rotas(data)

    if rotas is None:
        print("\nNÃO FOI ENCONTRADA UMA SOLUÇÃO VIÁVEL.")
        print(
            "Isso significa que, com os caminhões, capacidades e "
            "janelas de tempo informados, o problema não pode ser atendido."
        )
        return

    problemas = validar_rotas(rotas, data)

    imprimir_resultado(rotas, data)

    print("\n" + "=" * 65)
    if problemas:
        print("VALIDAÇÃO: FALHOU")
        for problema in problemas:
            print(f"- {problema}")
    else:
        print("VALIDAÇÃO: OK")
        print("Todas as rotas respeitam as restrições implementadas.")
    print("=" * 65)


if __name__ == "__main__":
    main()

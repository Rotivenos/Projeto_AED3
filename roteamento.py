"""Motor de roteamento próprio: inserção gulosa e busca local para VRP.

Usa distância/duração real por estrada (API pública OSRM), com fallback em
linha reta (haversine) quando a API não responde ou não acha rota para um
par de pontos.
"""
from time import monotonic as relogio_monotonico

from enderecos import haversine_km, matriz_rotas

# Velocidade média assumida para converter distância (km) em tempo de
# deslocamento (min) no fallback, quando a API OSRM não está disponível.
VELOCIDADE_MEDIA_KMH = 30


def gethoraparaminutos(hora):
    """Converte HH:MM para minutos desde meia-noite."""
    h, m = map(int, hora.split(":"))
    return h * 60 + m


def getminutosparahora(minutos):
    return f"{minutos // 60:02d}:{minutos % 60:02d}"


def getconstruirdados(pedidos, caminhoes, deposito):
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

    matriz_tempos_min = [[0] * n for _ in range(n)]
    matriz_distancias_km = [[0] * n for _ in range(n)]
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

            matriz_distancias_km[i][j] = round(km, 1)
            matriz_tempos_min[i][j] = max(round(minutos), 1)

    cargas_kg = [0] + [float(p["peso_kg"]) for p in pedidos]

    # Depósito: operação das 06:00 às 18:00.
    janelas_horario = [(360, 1080)]
    for p in pedidos:
        limite = gethoraparaminutos(p["prazo"])
        # Nesta V2, a entrega pode ocorrer a partir das 06:00 até o prazo.
        janelas_horario.append((360, limite))

    tempos_atendimento_min = [0] + [10 for _ in pedidos]

    capacidades_kg = [float(c["capacidade_kg"]) for c in caminhoes]

    return {
        "matriz_tempos_min": matriz_tempos_min,
        "matriz_distancias_km": matriz_distancias_km,
        "coordenadas": coordenadas,
        "cargas_kg": cargas_kg,
        "janelas_horario": janelas_horario,
        "tempos_atendimento_min": tempos_atendimento_min,
        "capacidades_kg": capacidades_kg,
        "quantidade_caminhoes": len(caminhoes),
        "indice_deposito": 0,
    }


CUSTO_CAMINHAO = 100
LIMITE_BUSCA_SEGUNDOS = 5


def getavaliarrota(rota, capacidade, dados):
    """Simula a viagem completa. Retorna None se alguma restrição falhar.

    Cada rota contém índices de pedidos; o depósito (0) é implícito nas
    duas pontas. Saída às 06h, atendimento de 10 min e retorno até 18h.
    O prazo de cada pedido limita a chegada, como na versão anterior.
    """
    carga = sum(dados["cargas_kg"][no] for no in rota)
    if carga > capacidade:
        return None
    horario = dados["janelas_horario"][0][0]
    anterior = 0
    deslocamento = 0
    chegadas = []
    for no in rota:
        trecho = dados["matriz_tempos_min"][anterior][no]
        deslocamento += trecho
        horario = max(horario + trecho, dados["janelas_horario"][no][0])
        if horario > dados["janelas_horario"][no][1]:
            return None
        chegadas.append(horario)
        horario += dados["tempos_atendimento_min"][no]
        anterior = no
    retorno = dados["matriz_tempos_min"][anterior][0]
    deslocamento += retorno
    horario += retorno
    if horario > dados["janelas_horario"][0][1]:
        return None
    return {
        "carga": carga,
        "chegadas": chegadas,
        "retorno": horario,
        "deslocamento": deslocamento,
        "custo": deslocamento + sum(dados["tempos_atendimento_min"][no] for no in rota)
        + (CUSTO_CAMINHAO if rota else 0),
    }


def setinserirpendentes(rotas, pendentes, dados, limite=None):
    """Insere o pedido viável de menor custo adicional, em qualquer posição.

    Em empates, prioriza o prazo mais curto. Reavalia todos os horários e
    a volta ao depósito em cada tentativa, sem pressupor matriz simétrica.
    A construção inicial termina sem limite; novas tentativas na busca
    local compartilham o orçamento de tempo da busca.
    """
    while pendentes:
        melhor = None
        for veiculo, rota in enumerate(rotas):
            capacidade = dados["capacidades_kg"][veiculo]
            custo_atual = getavaliarrota(rota, capacidade, dados)["custo"]
            for no in sorted(pendentes):
                for posicao in range(len(rota) + 1):
                    if limite is not None and relogio_monotonico() >= limite:
                        return
                    candidata = rota[:posicao] + [no] + rota[posicao:]
                    avaliacao = getavaliarrota(candidata, capacidade, dados)
                    if avaliacao is None:
                        continue
                    chave = (avaliacao["custo"] - custo_atual,
                             dados["janelas_horario"][no][1], no, veiculo, posicao)
                    if melhor is None or chave < melhor[0]:
                        melhor = (chave, veiculo, no, candidata)
        if melhor is None:
            return
        _, veiculo, no, candidata = melhor
        rotas[veiculo] = candidata
        pendentes.remove(no)


def getvizinhos(rotas):
    """Gera alterações: inverter sequência, realocar e trocar entregas.

    Retorna apenas as rotas alteradas para evitar copiar toda a solução.
    As listas originais nunca são modificadas durante a avaliação.
    """
    for veiculo, rota in enumerate(rotas):
        for inicio in range(len(rota)):
            for fim in range(inicio + 2, len(rota) + 1):
                yield {veiculo: rota[:inicio] + rota[inicio:fim][::-1] + rota[fim:]}
        for posicao, no in enumerate(rota):
            sem_no = rota[:posicao] + rota[posicao + 1:]
            for destino, outra in enumerate(rotas):
                base = sem_no if destino == veiculo else outra
                for insercao in range(len(base) + 1):
                    nova = base[:insercao] + [no] + base[insercao:]
                    if destino == veiculo:
                        if nova != rota:
                            yield {veiculo: nova}
                    else:
                        yield {veiculo: sem_no, destino: nova}
            for destino in range(veiculo + 1, len(rotas)):
                for indice, outro_no in enumerate(rotas[destino]):
                    nova_origem = rota[:posicao] + [outro_no] + rota[posicao + 1:]
                    nova_destino = (rotas[destino][:indice] + [no]
                                    + rotas[destino][indice + 1:])
                    yield {veiculo: nova_origem, destino: nova_destino}


def setmelhorarrotas(rotas, pendentes, dados):
    """Busca local de primeira melhoria, limitada a cinco segundos.

    Só aceita movimentos viáveis que reduzam o custo. Não remove pedidos
    atendidos. Depois de melhorar, tenta encaixar novamente os pendentes.
    É uma heurística: não prova otimalidade nem inviabilidade dos pendentes.
    """
    limite = relogio_monotonico() + LIMITE_BUSCA_SEGUNDOS
    while relogio_monotonico() < limite:
        custos = [getavaliarrota(rota, capacidade, dados)["custo"]
                  for rota, capacidade in zip(rotas, dados["capacidades_kg"])]
        melhorou = False
        for alteracoes in getvizinhos(rotas):
            if relogio_monotonico() >= limite:
                return
            novo_custo = 0
            for veiculo, candidata in alteracoes.items():
                avaliacao = getavaliarrota(
                    candidata, dados["capacidades_kg"][veiculo], dados)
                if avaliacao is None:
                    break
                novo_custo += avaliacao["custo"]
            else:
                if novo_custo < sum(custos[v] for v in alteracoes):
                    for veiculo, candidata in alteracoes.items():
                        rotas[veiculo] = candidata
                    setinserirpendentes(rotas, pendentes, dados, limite)
                    melhorou = True
                    break
        if not melhorou:
            return


def getotimizar(pedidos, caminhoes, deposito):
    if deposito is None or deposito["latitude"] is None or deposito["longitude"] is None:
        return {"erro": "Cadastre e geocodifique o endereço do depósito antes de otimizar as rotas."}
    if not pedidos:
        return {"erro": "Não existem pedidos pendentes com endereço geocodificado."}
    if not caminhoes:
        return {"erro": "Não existem caminhões disponíveis."}

    dados = getconstruirdados(pedidos, caminhoes, deposito)
    rotas = [[] for _ in caminhoes]
    pendentes = set(range(1, len(pedidos) + 1))
    setinserirpendentes(rotas, pendentes, dados)
    setmelhorarrotas(rotas, pendentes, dados)

    resultado = []
    for veiculo, rota in enumerate(rotas):
        if not rota:
            continue
        caminhao = caminhoes[veiculo]
        avaliacao = getavaliarrota(rota, dados["capacidades_kg"][veiculo], dados)
        paradas = []
        anterior = 0
        acumulada = 0
        for no, chegada in zip(rota, avaliacao["chegadas"]):
            pedido = pedidos[no - 1]
            trecho = dados["matriz_distancias_km"][anterior][no]
            acumulada = round(acumulada + trecho, 1)
            paradas.append({
                "pedido_id": pedido["id"], "cliente": pedido["cliente"],
                "endereco": pedido["endereco"], "peso_kg": dados["cargas_kg"][no],
                "prazo": pedido["prazo"], "chegada": getminutosparahora(chegada),
                "chegada_min": chegada, "distancia_km": trecho,
                "distancia_acumulada_km": acumulada,
            })
            anterior = no
        retorno_km = dados["matriz_distancias_km"][anterior][0]
        total_km = round(acumulada + retorno_km, 1)
        capacidade = dados["capacidades_kg"][veiculo]
        resultado.append({
            "caminhao_id": caminhao["id"], "placa": caminhao["placa"],
            "capacidade_kg": capacidade, "carga_kg": avaliacao["carga"],
            "ocupacao": round(avaliacao["carga"] / capacidade * 100, 1) if capacidade else 0,
            "paradas": paradas, "tempo_deslocamento_min": avaliacao["deslocamento"],
            "distancia_total_km": total_km,
            "retorno_deposito": {
                "endereco": deposito["endereco"], "distancia_km": retorno_km,
                "distancia_acumulada_km": total_km,
                "chegada": getminutosparahora(avaliacao["retorno"]),
            },
        })
    return {
        "rotas": resultado,
        "pedidos_atendidos": len(pedidos) - len(pendentes),
        "pedidos_nao_atendidos": [
            {"cliente": p["cliente"], "endereco": p["endereco"]}
            for no, p in enumerate(pedidos, 1) if no in pendentes
        ],
        "caminhoes_utilizados": len(resultado),
        "tempo_deslocamento_total_min": sum(r["tempo_deslocamento_min"] for r in resultado),
        "distancia_total_km": round(sum(r["distancia_total_km"] for r in resultado), 1),
    }

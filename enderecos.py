"""Integrações com APIs públicas de endereço e rotas.

- ViaCEP: consulta de logradouro/bairro/cidade/UF a partir do CEP.
- Nominatim (OpenStreetMap): geocodificação (endereço -> latitude/longitude).
- OSRM (Project OSRM, também sobre dados do OpenStreetMap): matriz de
  distância/duração por estrada real entre vários pontos de uma vez.
"""
import os
import re
from math import radians, sin, cos, asin, sqrt

import requests

VIACEP_URL = "https://viacep.com.br/ws/{cep}/json/"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"

# Servidor de demonstração pública do OSRM. Gratuito, mas é um recurso
# compartilhado e não recomendado para uso pesado/produção — pode ser
# apontado para uma instância própria via variável de ambiente.
OSRM_URL = os.environ.get(
    "OSRM_URL", "https://router.project-osrm.org/table/v1/driving/{coords}"
)

# A política de uso do Nominatim pede um User-Agent que identifique a
# aplicação. Pode ser sobrescrito via variável de ambiente para incluir um
# contato, sem precisar alterar o código.
NOMINATIM_USER_AGENT = os.environ.get(
    "NOMINATIM_USER_AGENT", "ProjetoAED3-RoteirizacaoUCL/1.0"
)

TIMEOUT = 8
TIMEOUT_OSRM = 20
RAIO_TERRA_KM = 6371


def normalizar_cep(cep):
    return re.sub(r"\D", "", cep or "")


def buscar_cep(cep):
    """Consulta a API pública ViaCEP. Retorna dict de endereço ou None."""
    cep = normalizar_cep(cep)
    if len(cep) != 8:
        return None

    try:
        resp = requests.get(VIACEP_URL.format(cep=cep), timeout=TIMEOUT)
        resp.raise_for_status()
        dados = resp.json()
    except (requests.RequestException, ValueError):
        return None

    if dados.get("erro"):
        return None

    return {
        "logradouro": dados.get("logradouro", ""),
        "bairro": dados.get("bairro", ""),
        "cidade": dados.get("localidade", ""),
        "uf": dados.get("uf", ""),
    }


def geocodificar(endereco):
    """Consulta a API pública Nominatim. Retorna (lat, lon) ou None."""
    if not endereco or not endereco.strip():
        return None

    params = {
        "format": "json",
        "q": endereco,
        "limit": 1,
        "countrycodes": "br",
    }
    headers = {"User-Agent": NOMINATIM_USER_AGENT}

    try:
        resp = requests.get(
            NOMINATIM_URL, params=params, headers=headers, timeout=TIMEOUT
        )
        resp.raise_for_status()
        resultados = resp.json()
    except (requests.RequestException, ValueError):
        return None

    if not resultados:
        return None

    try:
        return float(resultados[0]["lat"]), float(resultados[0]["lon"])
    except (KeyError, TypeError, ValueError):
        return None


def haversine_km(lat1, lon1, lat2, lon2):
    """Distância em linha reta (km) entre duas coordenadas."""
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return 2 * RAIO_TERRA_KM * asin(sqrt(a))


def matriz_rotas(coordenadas):
    """
    Consulta a API pública OSRM para obter, em uma única chamada, a matriz
    de distância (km) e duração (min) por estrada real entre todos os
    pontos informados (lista de (lat, lon), depósito incluso).

    Retorna (distancias_km, duracoes_min), matrizes NxN podendo conter
    ``None`` em pares sem rota conhecida, ou None se a API não respondeu.
    """
    if len(coordenadas) < 2:
        return None

    coords_str = ";".join(f"{lon},{lat}" for lat, lon in coordenadas)
    params = {"annotations": "distance,duration"}

    try:
        resp = requests.get(
            OSRM_URL.format(coords=coords_str), params=params, timeout=TIMEOUT_OSRM
        )
        resp.raise_for_status()
        dados = resp.json()
    except (requests.RequestException, ValueError):
        return None

    if dados.get("code") != "Ok":
        return None

    distancias = dados.get("distances")
    duracoes = dados.get("durations")
    if not distancias or not duracoes:
        return None

    distancias_km = [
        [(v / 1000 if v is not None else None) for v in linha]
        for linha in distancias
    ]
    duracoes_min = [
        [(v / 60 if v is not None else None) for v in linha]
        for linha in duracoes
    ]
    return distancias_km, duracoes_min

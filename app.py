from flask import Flask, render_template, request, redirect, url_for
import sqlite3
from pathlib import Path

from enderecos import buscar_cep, geocodificar, normalizar_cep
from roteamento import otimizar

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "rotas.db"

# Depósito padrão (base de onde as rotas partem). Coordenadas já
# geocodificadas via Nominatim para não depender de rede no primeiro start;
# pode ser alterado depois pela tela "Depósito".
DEPOSITO_PADRAO = {
    "endereco": "Rodovia ES-010, Km 6, Manguinhos, Serra - ES",
    "cep": "29173087",
    "latitude": -20.202429,
    "longitude": -40.220567,
}

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
            cep TEXT,
            latitude REAL,
            longitude REAL,
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

        CREATE TABLE IF NOT EXISTS deposito (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            endereco TEXT,
            cep TEXT,
            latitude REAL,
            longitude REAL
        );
    """)

    # Migração para bancos criados por versões anteriores, que não tinham
    # as colunas de geocodificação em "pedidos".
    colunas = {row["name"] for row in conn.execute("PRAGMA table_info(pedidos)")}
    for coluna, tipo in (("cep", "TEXT"), ("latitude", "REAL"), ("longitude", "REAL")):
        if coluna not in colunas:
            conn.execute(f"ALTER TABLE pedidos ADD COLUMN {coluna} {tipo}")

    # Garante que sempre exista um depósito configurado (não sobrescreve um
    # já cadastrado pela tela "Depósito").
    conn.execute(
        """
        INSERT OR IGNORE INTO deposito (id, endereco, cep, latitude, longitude)
        VALUES (1, ?, ?, ?, ?)
        """,
        (
            DEPOSITO_PADRAO["endereco"],
            DEPOSITO_PADRAO["cep"],
            DEPOSITO_PADRAO["latitude"],
            DEPOSITO_PADRAO["longitude"],
        )
    )

    conn.commit()
    conn.close()


def get_deposito(conn):
    return conn.execute("SELECT * FROM deposito WHERE id = 1").fetchone()


def resolver_endereco(endereco, cep):
    """
    Enriquece o endereço com dados do CEP (ViaCEP) e geocodifica o
    resultado (Nominatim/OpenStreetMap).
    Retorna (endereco_completo, cep_normalizado, coordenadas | None).
    """
    cep_normalizado = normalizar_cep(cep)
    endereco_completo = endereco

    if cep_normalizado:
        info = buscar_cep(cep_normalizado)
        if info:
            extras = [v for v in (info["bairro"], info["cidade"]) if v]
            if extras:
                endereco_completo += ", " + ", ".join(extras)
            if info["uf"]:
                endereco_completo += f" - {info['uf']}"
        endereco_completo += f", {cep_normalizado}"

    coords = geocodificar(endereco_completo)
    if coords is None and endereco_completo != endereco:
        coords = geocodificar(endereco)

    return endereco_completo, cep_normalizado, coords


@app.route("/")
def index():
    conn = get_db()

    caminhoes = conn.execute(
        "SELECT * FROM caminhoes ORDER BY id DESC"
    ).fetchall()

    pedidos = conn.execute(
        "SELECT * FROM pedidos ORDER BY id DESC"
    ).fetchall()

    deposito = get_deposito(conn)

    conn.close()

    resultado = None
    return render_template(
        "index.html",
        caminhoes=caminhoes,
        pedidos=pedidos,
        deposito=deposito,
        resultado=resultado,
        aviso=request.args.get("aviso"),
        aviso_tipo=request.args.get("tipo", "erro"),
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
    cep = request.form.get("cep", "").strip()
    peso = float(request.form["peso_kg"])
    prazo = request.form["prazo"]

    endereco_completo, cep_normalizado, coords = resolver_endereco(endereco, cep)
    latitude, longitude = coords if coords else (None, None)

    conn = get_db()
    conn.execute(
        """
        INSERT INTO pedidos (cliente, endereco, cep, latitude, longitude, peso_kg, prazo)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (cliente, endereco_completo, cep_normalizado or None, latitude, longitude, peso, prazo)
    )
    conn.commit()
    conn.close()

    if coords is None:
        return redirect(url_for(
            "index",
            aviso=(
                f'Não foi possível localizar "{endereco}" no mapa. O pedido '
                "foi salvo, mas não entrará na otimização até o endereço "
                "ser corrigido."
            ),
            tipo="erro",
        ))

    return redirect(url_for("index"))


@app.post("/deposito")
def atualizar_deposito():
    endereco = request.form["endereco"].strip()
    cep = request.form.get("cep", "").strip()

    endereco_completo, cep_normalizado, coords = resolver_endereco(endereco, cep)
    latitude, longitude = coords if coords else (None, None)

    conn = get_db()
    conn.execute(
        """
        INSERT INTO deposito (id, endereco, cep, latitude, longitude)
        VALUES (1, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            endereco = excluded.endereco,
            cep = excluded.cep,
            latitude = excluded.latitude,
            longitude = excluded.longitude
        """,
        (endereco_completo, cep_normalizado or None, latitude, longitude)
    )
    conn.commit()
    conn.close()

    if coords is None:
        return redirect(url_for(
            "index",
            aviso=f'Não foi possível localizar "{endereco}" no mapa. Corrija o endereço do depósito.',
            tipo="erro",
        ))

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

    deposito = get_deposito(conn)

    conn.close()

    pedidos_geocodificados = [p for p in pedidos if p["latitude"] is not None]
    pedidos_sem_geo = [p for p in pedidos if p["latitude"] is None]

    resultado = otimizar(pedidos_geocodificados, caminhoes, deposito)

    if pedidos_sem_geo:
        resultado = dict(resultado)
        resultado["pedidos_sem_geo"] = [
            {"cliente": p["cliente"], "endereco": p["endereco"]}
            for p in pedidos_sem_geo
        ]

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
        deposito=deposito,
        resultado=resultado
    )


if __name__ == "__main__":
    init_db()
    app.run(debug=True)

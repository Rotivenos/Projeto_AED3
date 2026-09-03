# Sistema de Otimização de Rotas de Entrega — V1

Primeiro protótipo acadêmico do projeto.

## O que esta versão faz

O programa usa o Google OR-Tools para encontrar rotas para uma frota de caminhões considerando:

- capacidade de carga;
- horário limite de entrega;
- tempo de deslocamento entre pontos;
- tempo de serviço/descarga;
- utilização de caminhões;
- minimização do custo total de rota.

A solução encontrada também passa por uma etapa de validação.

## Tecnologias

- Python 3.10+
- Google OR-Tools

## Como executar

### 1. Criar ambiente virtual (opcional)

Windows:

```bash
python -m venv .venv
.venv\Scripts\activate
```

Linux/macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Instalar dependências

```bash
pip install -r requirements.txt
```

### 3. Executar

```bash
python main.py
```

## Estrutura

```text
projeto_rotas/
├── main.py
├── requirements.txt
└── README.md
```

## Próxima evolução

A V2 pode trocar os dados fictícios por:

- SQLite;
- cadastro de clientes;
- cadastro de caminhões;
- cadastro de pedidos;
- tela web com Flask;
- mapa;
- comparação entre rota comum e rota otimizada.

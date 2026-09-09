# Projeto de Rotas — V2.2

Agora o sistema possui Flask + SQLite + OR-Tools.

## Recursos

- cadastro de caminhões;
- cadastro de pedidos;
- armazenamento em SQLite;
- botão de otimização;
- roteamento com OR-Tools;
- restrição de capacidade;
- restrição de horário limite;
- tentativa de usar menos caminhões;
- exibição das rotas e ocupação.

## Executar

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Abrir:

http://127.0.0.1:5000

## Observação

As distâncias ainda são fictícias. O endereço é armazenado, mas ainda
não é convertido em latitude/longitude. Essa será uma evolução posterior.

## Teste sugerido

Cadastre:

Caminhões:
- ABC1234 — 10.000 kg
- DEF5678 — 10.000 kg
- GHI9012 — 10.000 kg

Pedidos:
- Mercado A — 2.000 kg — 09:00
- Loja B — 3.000 kg — 10:00
- Mercado C — 4.000 kg — 11:00
- Loja D — 2.000 kg — 11:30
- Mercado E — 3.000 kg — 12:00

Clique em OTIMIZAR ROTAS.
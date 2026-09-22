# Projeto de Rotas — V2.4

Nesta versão o usuário NÃO precisa informar latitude e longitude.

## O que mudou

- O formulário recebe endereço e cidade/UF.
- O backend consulta o Nominatim para geocodificar o endereço.
- A latitude e longitude retornadas são armazenadas no SQLite.
- O resultado encontrado pelo serviço é armazenado em `endereco_geocodificado`.
- A otimização usa as coordenadas salvas.
- O mapa mostra os clientes e conecta os pontos na ordem calculada.
- Bancos criados em versões anteriores recebem as novas colunas automaticamente.

## Serviço usado

A geocodificação usa o serviço público Nominatim do OpenStreetMap.
A documentação oficial descreve a busca por endereço textual com `/search`,
retornando `lat`, `lon` e `display_name` em JSON/JSONv2.

Nesta versão, as consultas são feitas individualmente e com um User-Agent
identificando a aplicação, além de uma espera aproximada de 1 segundo entre
consultas neste processo.

Para um projeto acadêmico pequeno isso é suficiente. Para uso em produção,
o ideal é utilizar um serviço de geocodificação/roteamento adequado ao volume
ou hospedar sua própria infraestrutura.

## Executar

```bash
python -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
python app.py
```

Abrir:

http://127.0.0.1:5000

## Teste

Cadastre, por exemplo:

Caminhões:
- ABC1234 — 10.000 kg
- DEF5678 — 10.000 kg

Pedidos:
- Mercado A — Avenida Nossa Senhora da Penha, 1000 — Vitória - ES — 2000 kg — 09:00
- Mercado B — Avenida Central, 500 — Serra - ES — 3000 kg — 10:00

Ao salvar o pedido, o sistema tenta encontrar a localização automaticamente.

## Observação importante

A V2.4 ainda usa uma estimativa de distância geográfica (Haversine) e uma
velocidade média para estimar tempo. Ela ainda NÃO calcula o caminho real pelas
ruas. Essa é a próxima evolução do projeto.
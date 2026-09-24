# Projeto de Rotas — V2.4

Agora o sistema possui Flask + SQLite + OR-Tools + geocodificação e roteamento por APIs públicas.

## Recursos

- cadastro de caminhões;
- cadastro de pedidos, com CEP (ViaCEP) e geocodificação de endereço (Nominatim/OpenStreetMap);
- cadastro do endereço do depósito (origem das rotas), também geocodificado;
- armazenamento em SQLite;
- botão de otimização;
- roteamento com OR-Tools usando distância/duração reais por estrada (OSRM), com fallback em linha reta (haversine) se a API não responder;
- restrição de capacidade;
- restrição de horário limite;
- otimização parcial: se algum pedido não couber em nenhuma rota (capacidade ou prazo), ele fica de fora com aviso, em vez de a otimização inteira falhar;
- tentativa de usar menos caminhões;
- exibição das rotas, distância de cada trecho, ocupação e status de geocodificação de cada pedido.

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

Os endereços (depósito e pedidos) são geocodificados automaticamente ao
cadastrar, usando duas APIs públicas gratuitas:

- [ViaCEP](https://viacep.com.br/) — a partir do CEP, complementa o endereço
  com bairro, cidade e UF antes de geocodificar (o CEP é opcional).
- [Nominatim (OpenStreetMap)](https://nominatim.org/) — converte o endereço
  em latitude/longitude.

A distância/duração usada na otimização vem do [OSRM](https://project-osrm.org/)
(rota real por estrada, não linha reta), consultando o servidor de
demonstração pública em uma única chamada por otimização. Se a API não
responder (ou não achar rota para algum par de pontos), o sistema cai para
uma estimativa em linha reta (haversine) com velocidade média fixa, só para
aquele par.

Se um endereço não for localizado, o pedido é salvo mesmo assim, mas fica
fora da otimização até ser corrigido (a tela mostra um aviso e um selo
✗ na tabela de pedidos). Da mesma forma, se um pedido não couber em nenhuma
rota por causa de capacidade ou prazo, ele fica de fora com aviso — a
otimização não falha por inteiro por causa de um pedido problemático. É
necessário cadastrar e geocodificar o endereço do depósito antes de
otimizar.

Por usarem serviços públicos e gratuitos:
- defina a variável de ambiente `NOMINATIM_USER_AGENT` com um identificador
  da sua aplicação (e um contato, se possível), seguindo a
  [política de uso do Nominatim](https://operations.osmfoundation.org/policies/nominatim/);
- o servidor de demonstração do OSRM não é recomendado para uso pesado ou em
  produção — para isso, aponte `OSRM_URL` para uma instância própria.

## Teste sugerido

Cadastre o depósito:
- Endereço: Avenida Paulista, 1578 — CEP: 01310-200

Cadastre:

Caminhões:
- ABC1234 — 10.000 kg
- DEF5678 — 10.000 kg
- GHI9012 — 10.000 kg

Pedidos (endereço + CEP):
- Mercado A — Rua Augusta, 500 — CEP 01305-000 — 2.000 kg — 09:00
- Loja B — Avenida Rebouças, 300 — CEP 05402-000 — 3.000 kg — 10:00
- Mercado C — Rua Oscar Freire, 200 — CEP 01426-000 — 4.000 kg — 11:00
- Loja D — Avenida Brigadeiro Faria Lima, 1000 — CEP 01452-000 — 2.000 kg — 11:30
- Mercado E — Rua da Consolação, 2000 — CEP 01302-000 — 3.000 kg — 12:00

Clique em OTIMIZAR ROTAS.
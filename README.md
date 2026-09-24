# Projeto de Rotas — V2.4

O sistema possui Flask + SQLite + algoritmo próprio de otimização em Python, com geocodificação e dados de deslocamento por APIs públicas.

## Recursos

- cadastro de caminhões;
- cadastro de pedidos, com CEP (ViaCEP) e geocodificação de endereço (Nominatim/OpenStreetMap);
- cadastro do endereço do depósito (origem das rotas), também geocodificado;
- armazenamento em SQLite;
- botão de otimização;
- roteamento com inserção gulosa e busca local próprias, usando distância/duração por estrada (OSRM), com fallback em linha reta (haversine) se a API não responder;
- restrição de capacidade;
- restrição de horário limite;
- otimização parcial: pedidos que o algoritmo não conseguir encaixar ficam de fora com aviso, em vez de a otimização inteira falhar;
- tentativa de usar menos caminhões;
- exibição das rotas, distância de cada trecho, ocupação e status de geocodificação de cada pedido;
- retorno ao depósito até as 18h, incluído nos totais e exibido como último trecho.

## Algoritmo próprio

O motor está em `roteamento.py` e não depende do Google OR-Tools.

1. `getconstruirdados` monta as matrizes de tempo e distância entre depósito e entregas.
2. `getavaliarrota` simula o percurso desde as 06h, soma 10 minutos de atendimento
   por entrega e verifica capacidade, prazo de chegada e retorno até as 18h.
   A carga mantém valores fracionários em kg. `matriz_tempos_min` contém
   minutos; `matriz_distancias_km` contém km.
3. `setinserirpendentes` testa cada pedido em todas as posições de todas as rotas
   e aceita a inserção viável com menor aumento de custo. Empates priorizam o
   prazo mais curto. O custo soma deslocamento, atendimento e 100 por caminhão
   utilizado. Esse 100 é um peso de otimização, não um valor em reais.
4. `setmelhorarrotas` tenta inverter sequências, mover entregas e trocar pedidos
   entre caminhões. Só aceita reduções de custo que preservem as restrições e
   os pedidos já atendidos. Após uma melhoria, tenta inserir os pendentes novamente.
   A busca local tem orçamento de 5 segundos; a construção inicial e consultas
   às APIs ocorrem antes desse orçamento.

As matrizes podem ser assimétricas: ir de A para B pode custar diferente de
voltar de B para A. Todos os movimentos são avaliados com o percurso completo.
Os totais de deslocamento excluem atendimento e espera; o horário de retorno
inclui esses tempos.

As funções usam nomes em português: `get` para obter resultados e `set` para
alterar as rotas recebidas. `getotimizar` é a entrada chamada pelo Flask;
`setinserirpendentes` e `setmelhorarrotas` modificam as listas de rotas internas.

É uma heurística, sem garantia de ótimo global ou de atender o máximo possível
de pedidos. Um pedido pendente significa que o algoritmo não encontrou um
encaixe, e não uma prova de que nenhuma solução existe. A implementação explora
as combinações explicitamente e é voltada a instâncias pequenas do projeto.

Para executar os testes locais, sem consultar as APIs:

```bash
python -m unittest discover -s tests -v
```

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
✗ na tabela de pedidos). Da mesma forma, se a heurística não encontrar um
encaixe respeitando capacidade, prazo e retorno, o pedido fica de fora com aviso — a
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

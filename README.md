# Projeto AED3 - Melhor Rota com Ordenacao em C#

Trabalho de faculdade sobre uso de ordenacao para montar rotas de veiculos com menor distancia percorrida e menor consumo de combustivel.

O projeto agora possui uma interface grafica em Windows Forms.

O projeto trabalha com:

- pedidos com peso, prioridade, latitude e longitude;
- veiculos com capacidade maxima de carga;
- deposito de origem e retorno;
- calculo de distancia pela formula de Haversine;
- montagem de rotas respeitando a capacidade dos veiculos;
- ordenacao dos enderecos mais proximos para reduzir a quilometragem.

## Metodo de ordenacao usado

O projeto usa `Selection Sort` porque ele combina bem com a ideia didatica do trabalho:

- olhar a lista de pedidos disponiveis;
- encontrar o pedido mais proximo do ponto atual;
- colocar esse pedido como proxima entrega;
- repetir o processo ate montar a rota.

Assim, os enderecos proximos ficam juntos na mesma rota, reduzindo a distancia total percorrida.

## Como a rota economica e montada

1. Os veiculos sao ordenados por maior capacidade.
2. Os pedidos sao ordenados pela menor distancia ate o deposito.
3. Cada pedido e colocado na rota viavel que gera menor aumento de distancia.
4. Dentro de cada rota, as entregas sao reordenadas pelo endereco mais proximo do ponto atual.
5. A distancia final e calculada com a formula de Haversine.

O resultado nao prova a menor rota perfeita do mundo real, mas gera uma rota boa para o objetivo do trabalho: usar ordenacao para aproximar entregas e diminuir consumo.

## Como executar

No terminal, dentro da pasta do projeto:

```bash
dotnet run
```

A tela mostra:

- tabela de veiculos;
- tabela de pedidos;
- botoes para adicionar, editar e excluir veiculos;
- botoes para adicionar, editar e excluir pedidos;
- botao para calcular as rotas;
- indicadores de distancia total, pedidos atendidos e veiculos usados;
- mapa esquematico com as rotas desenhadas por cor.

## Estrutura

- `Program.cs`: inicializacao da aplicacao grafica.
- `MainForm.cs`: tela principal com tabelas, indicadores e mapa das rotas.
- `EntityForms.cs`: formularios de cadastro e edicao de veiculos e pedidos.
- `DadosExemplo.cs`: dados usados na demonstracao.
- `Models.cs`: classes de pedido, veiculo, ponto, rota e resultado.
- `CalculadoraDistancia.cs`: calculo da distancia entre coordenadas pela formula de Haversine.
- `OtimizadorRotas.cs`: monta e compara as rotas.
- `OtimizadorRotas.cs`: implementacao manual do Selection Sort e montagem das rotas.
- `ProjetoOrdenacao.csproj`: arquivo do projeto C#.

## Objetivo didatico

O objetivo e demonstrar como uma ordenacao por proximidade pode ser aplicada para resolver um problema pratico de roteirizacao com restricao de carga.

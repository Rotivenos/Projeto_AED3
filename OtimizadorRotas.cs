#nullable enable

namespace ProjetoOrdenacao;

public static class OtimizadorRotas
{
    public static ResultadoRoteirizacao Otimizar(
        List<Pedido> pedidos,
        List<Veiculo> veiculos,
        Ponto deposito)
    {
        List<Veiculo> veiculosOrdenados = new(veiculos);

        // coloca os veiculos com mais capacidade primeiro
        for (int posicaoAtual = 0; posicaoAtual < veiculosOrdenados.Count - 1; posicaoAtual++)
        {
            int posicaoMaiorCapacidade = posicaoAtual;

            for (int posicaoBusca = posicaoAtual + 1; posicaoBusca < veiculosOrdenados.Count; posicaoBusca++)
            {
                if (veiculosOrdenados[posicaoBusca].CapacidadeKg > veiculosOrdenados[posicaoMaiorCapacidade].CapacidadeKg)
                {
                    posicaoMaiorCapacidade = posicaoBusca;
                }
            }

            if (posicaoMaiorCapacidade != posicaoAtual)
            {
                Veiculo temporario = veiculosOrdenados[posicaoAtual];
                veiculosOrdenados[posicaoAtual] = veiculosOrdenados[posicaoMaiorCapacidade];
                veiculosOrdenados[posicaoMaiorCapacidade] = temporario;
            }
        }

        List<Rota> rotas = new();

        // monta as rotas vazias
        foreach (Veiculo veiculo in veiculosOrdenados)
        {
            rotas.Add(new Rota(veiculo));
        }

        // comeca pelos pedidos mais perto do deposito
        List<Pedido> pedidosPendentes = OrdenarPorDistancia(pedidos, deposito);
        List<Pedido> pedidosNaoAtendidos = new();

        foreach (Pedido pedido in pedidosPendentes)
        {
            // escolhe a rota em que esse pedido aumenta menos a distancia
            Rota? melhorRota = EscolherRotaMaisEconomica(rotas, pedido, deposito);

            if (melhorRota is null)
            {
                pedidosNaoAtendidos.Add(pedido);
            }
            else
            {
                melhorRota.Pedidos.Add(pedido);
            }
        }

        foreach (Rota rota in rotas)
        {
            // reorganiza as entregas depois de distribuir os pedidos
            OrdenarEntregasPorProximidade(rota, deposito);
            rota.DistanciaTotal = CalcularDistanciaRota(rota, deposito);
        }

        return new ResultadoRoteirizacao
        {
            Metodo = "Selection Sort por proximidade para reduzir distancia e consumo",
            Rotas = FiltrarRotasComPedidos(rotas),
            PedidosNaoAtendidos = pedidosNaoAtendidos
        };
    }

    private static Rota? EscolherRotaMaisEconomica(List<Rota> rotas, Pedido pedido, Ponto deposito)
    {
        List<Rota> rotasViaveis = new();

        // so considera rotas com espaco para o peso do pedido
        foreach (Rota rota in rotas)
        {
            if (rota.CargaDisponivel >= pedido.PesoKg)
            {
                rotasViaveis.Add(rota);
            }
        }

        if (rotasViaveis.Count == 0)
        {
            return null;
        }

        // deixa a rota mais barata na primeira posicao
        for (int posicaoAtual = 0; posicaoAtual < rotasViaveis.Count - 1; posicaoAtual++)
        {
            int posicaoMenorCusto = posicaoAtual;

            for (int posicaoBusca = posicaoAtual + 1; posicaoBusca < rotasViaveis.Count; posicaoBusca++)
            {
                double custoBusca = CalcularCustoInsercao(rotasViaveis[posicaoBusca], pedido, deposito);
                double custoMenor = CalcularCustoInsercao(rotasViaveis[posicaoMenorCusto], pedido, deposito);

                if (custoBusca < custoMenor)
                {
                    posicaoMenorCusto = posicaoBusca;
                }
            }

            if (posicaoMenorCusto != posicaoAtual)
            {
                Rota temporaria = rotasViaveis[posicaoAtual];
                rotasViaveis[posicaoAtual] = rotasViaveis[posicaoMenorCusto];
                rotasViaveis[posicaoMenorCusto] = temporaria;
            }
        }

        return rotasViaveis[0];
    }

    private static List<Rota> FiltrarRotasComPedidos(List<Rota> rotas)
    {
        List<Rota> rotasComPedidos = new();

        // tira as rotas sem pedido
        foreach (Rota rota in rotas)
        {
            if (rota.Pedidos.Count > 0)
            {
                rotasComPedidos.Add(rota);
            }
        }

        return rotasComPedidos;
    }

    private static double CalcularCustoInsercao(Rota rota, Pedido pedido, Ponto deposito)
    {
        // pega o ultimo ponto da rota
        Ponto ultimoPonto = rota.Pedidos.Count == 0
            ? deposito
            : rota.Pedidos[rota.Pedidos.Count - 1].Ponto;

        double idaAtePedido = Distancia(ultimoPonto, pedido.Ponto);
        double voltaAntes = Distancia(ultimoPonto, deposito);
        double voltaDepois = Distancia(pedido.Ponto, deposito);

        // desconta a volta antiga para achar o aumento da distancia
        return idaAtePedido + voltaDepois - voltaAntes;
    }

    private static void OrdenarEntregasPorProximidade(Rota rota, Ponto deposito)
    {
        List<Pedido> pendentes = new(rota.Pedidos);
        rota.Pedidos.Clear();
        Ponto pontoAtual = deposito;

        while (pendentes.Count > 0)
        {
            // procura o pedido mais perto do ponto atual
            for (int posicaoAtual = 0; posicaoAtual < pendentes.Count - 1; posicaoAtual++)
            {
                int posicaoMaisProxima = posicaoAtual;

                for (int posicaoBusca = posicaoAtual + 1; posicaoBusca < pendentes.Count; posicaoBusca++)
                {
                    double distanciaBusca = Distancia(pontoAtual, pendentes[posicaoBusca].Ponto);
                    double distanciaMaisProxima = Distancia(pontoAtual, pendentes[posicaoMaisProxima].Ponto);

                    if (distanciaBusca < distanciaMaisProxima)
                    {
                        posicaoMaisProxima = posicaoBusca;
                    }
                }

                if (posicaoMaisProxima != posicaoAtual)
                {
                    Pedido temporario = pendentes[posicaoAtual];
                    pendentes[posicaoAtual] = pendentes[posicaoMaisProxima];
                    pendentes[posicaoMaisProxima] = temporario;
                }
            }

            Pedido proximoPedido = pendentes[0];
            rota.Pedidos.Add(proximoPedido);
            pendentes.RemoveAt(0);
            pontoAtual = proximoPedido.Ponto;
        }
    }

    private static List<Pedido> OrdenarPorDistancia(List<Pedido> pedidos, Ponto deposito)
    {
        List<Pedido> ordenados = new(pedidos);

        // selection sort pela distancia do deposito
        for (int posicaoAtual = 0; posicaoAtual < ordenados.Count - 1; posicaoAtual++)
        {
            int posicaoMaisProxima = posicaoAtual;

            for (int posicaoBusca = posicaoAtual + 1; posicaoBusca < ordenados.Count; posicaoBusca++)
            {
                double distanciaBusca = Distancia(deposito, ordenados[posicaoBusca].Ponto);
                double distanciaMaisProxima = Distancia(deposito, ordenados[posicaoMaisProxima].Ponto);

                if (distanciaBusca < distanciaMaisProxima)
                {
                    posicaoMaisProxima = posicaoBusca;
                }
            }

            if (posicaoMaisProxima != posicaoAtual)
            {
                Pedido temporario = ordenados[posicaoAtual];
                ordenados[posicaoAtual] = ordenados[posicaoMaisProxima];
                ordenados[posicaoMaisProxima] = temporario;
            }
        }

        return ordenados;
    }

    private static double CalcularDistanciaRota(Rota rota, Ponto deposito)
    {
        double total = 0;
        Ponto pontoAtual = deposito;

        // soma cada entrega e depois a volta ao deposito
        foreach (Pedido pedido in rota.Pedidos)
        {
            total += Distancia(pontoAtual, pedido.Ponto);
            pontoAtual = pedido.Ponto;
        }

        total += Distancia(pontoAtual, deposito);
        return total;
    }

    private static double Distancia(Ponto origem, Ponto destino)
    {
        return CalculadoraDistancia.CalcularHaversine(origem, destino);
    }
}

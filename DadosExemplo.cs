namespace ProjetoOrdenacao;

public static class DadosExemplo
{
    public static Ponto Deposito => new("Deposito - Avenida Paulista", -23.55052, -46.633308);

    public static List<Veiculo> CriarVeiculos()
    {
        return new List<Veiculo>
        {
            new Veiculo(1, "ABC-1234", 1000),
            new Veiculo(2, "DEF-5678", 800),
            new Veiculo(3, "GHI-9012", 600)
        };
    }

    public static List<Pedido> CriarPedidos()
    {
        return new List<Pedido>
        {
            new Pedido(1, "Mercado A", 220, -23.561732, -46.656007, 1),
            new Pedido(2, "Loja B", 350, -23.567320, -46.648250, 2),
            new Pedido(3, "Farmacia C", 180, -23.548943, -46.638818, 1),
            new Pedido(4, "Padaria D", 420, -23.570120, -46.645900, 3),
            new Pedido(5, "Restaurante E", 300, -23.555771, -46.662083, 2),
            new Pedido(6, "Mercado F", 260, -23.585040, -46.678720, 1),
            new Pedido(7, "Loja G", 160, -23.544846, -46.642719, 3),
            new Pedido(8, "Cliente H", 500, -23.598901, -46.676300, 2)
        };
    }
}

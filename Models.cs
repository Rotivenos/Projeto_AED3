namespace ProjetoOrdenacao;

// guarda o nome e as coordenadas de um lugar
public record Ponto(string Nome, double Latitude, double Longitude);

// pedido de entrega
public record Pedido(
    int Id,
    string Cliente,
    int PesoKg,
    double Latitude,
    double Longitude,
    int Prioridade)
{
    // usa as coordenadas do pedido como ponto para calcular a distancia
    public Ponto Ponto => new(Cliente, Latitude, Longitude);
}

// dados do veiculo
public record Veiculo(int Id, string Placa, int CapacidadeKg);

public class Rota
{
    public Rota(Veiculo veiculo)
    {
        Veiculo = veiculo;
    }

    public Veiculo Veiculo { get; }
    public List<Pedido> Pedidos { get; } = new();

    // soma o peso dos pedidos que estao nessa rota
    public int CargaTotal
    {
        get
        {
            int total = 0;

            foreach (Pedido pedido in Pedidos)
            {
                total += pedido.PesoKg;
            }

            return total;
        }
    }

    public double DistanciaTotal { get; set; }

    // capacidade do veiculo menos o peso que ja foi carregado
    public int CargaDisponivel => Veiculo.CapacidadeKg - CargaTotal;
}

public class ResultadoRoteirizacao
{
    public string Metodo { get; init; } = "";
    public List<Rota> Rotas { get; init; } = new();
    public List<Pedido> PedidosNaoAtendidos { get; init; } = new();

    // soma das distancias das rotas
    public double DistanciaTotal
    {
        get
        {
            double total = 0;

            foreach (Rota rota in Rotas)
            {
                total += rota.DistanciaTotal;
            }

            return total;
        }
    }

    // conta os pedidos que entraram em alguma rota
    public int TotalPedidosAtendidos
    {
        get
        {
            int total = 0;

            foreach (Rota rota in Rotas)
            {
                total += rota.Pedidos.Count;
            }

            return total;
        }
    }
}

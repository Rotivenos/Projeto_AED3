namespace ProjetoOrdenacao;

public static class CalculadoraDistancia
{
    // raio medio da terra em km
    private const double RaioTerraKm = 6371.0;

    public static double CalcularHaversine(Ponto origem, Ponto destino)
    {
        // converte as coordenadas para radianos antes do calculo
        double lat1 = GrausParaRadianos(origem.Latitude);
        double lon1 = GrausParaRadianos(origem.Longitude);
        double lat2 = GrausParaRadianos(destino.Latitude);
        double lon2 = GrausParaRadianos(destino.Longitude);

        // diferenca entre origem e destino
        double diferencaLat = lat2 - lat1;
        double diferencaLon = lon2 - lon1;

        // haversine calcula a distancia entre os dois pontos na terra
        double a = Math.Pow(Math.Sin(diferencaLat / 2), 2)
            + Math.Cos(lat1) * Math.Cos(lat2) * Math.Pow(Math.Sin(diferencaLon / 2), 2);

        double c = 2 * Math.Atan2(Math.Sqrt(a), Math.Sqrt(1 - a));
        return RaioTerraKm * c;
    }

    private static double GrausParaRadianos(double graus)
    {
        return graus * Math.PI / 180.0;
    }
}

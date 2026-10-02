#nullable enable

namespace ProjetoOrdenacao;

public class VeiculoForm : Form
{
    private readonly TextBox placa = new();
    private readonly NumericUpDown capacidade = new();

    public VeiculoForm(Veiculo? veiculo = null)
    {
        Text = veiculo is null ? "Adicionar veiculo" : "Editar veiculo";
        FormBorderStyle = FormBorderStyle.FixedDialog;
        StartPosition = FormStartPosition.CenterParent;
        MaximizeBox = false;
        MinimizeBox = false;
        ClientSize = new Size(330, 170);
        Font = new Font("Segoe UI", 9F);

        CriarCampoTexto("Placa", placa, 18, veiculo?.Placa ?? "");
        CriarCampoNumero("Capacidade kg", capacidade, 74, 1, 50000, veiculo?.CapacidadeKg ?? 1000, 0);
        CriarBotoes();
    }

    public string Placa => placa.Text.Trim().ToUpperInvariant();
    public int CapacidadeKg => (int)capacidade.Value;

    protected override void OnFormClosing(FormClosingEventArgs e)
    {
        if (DialogResult == DialogResult.OK && string.IsNullOrWhiteSpace(placa.Text))
        {
            MessageBox.Show("Informe a placa do veiculo.", "Campo obrigatorio", MessageBoxButtons.OK, MessageBoxIcon.Warning);
            e.Cancel = true;
        }

        base.OnFormClosing(e);
    }

    private void CriarCampoTexto(string rotulo, TextBox campo, int top, string valor)
    {
        Label label = new() { Text = rotulo, Left = 18, Top = top, Width = 120 };
        campo.Left = 145;
        campo.Top = top - 3;
        campo.Width = 155;
        campo.Text = valor;
        Controls.Add(label);
        Controls.Add(campo);
    }

    private void CriarCampoNumero(
        string rotulo,
        NumericUpDown campo,
        int top,
        decimal minimo,
        decimal maximo,
        decimal valor,
        int casasDecimais)
    {
        Label label = new() { Text = rotulo, Left = 18, Top = top, Width = 120 };
        campo.Left = 145;
        campo.Top = top - 3;
        campo.Width = 155;
        campo.Minimum = minimo;
        campo.Maximum = maximo;
        campo.Value = Math.Min(Math.Max(valor, minimo), maximo);
        campo.DecimalPlaces = casasDecimais;
        Controls.Add(label);
        Controls.Add(campo);
    }

    private void CriarBotoes()
    {
        Button salvar = new()
        {
            Text = "Salvar",
            DialogResult = DialogResult.OK,
            Left = 145,
            Top = 120,
            Width = 75
        };
        Button cancelar = new()
        {
            Text = "Cancelar",
            DialogResult = DialogResult.Cancel,
            Left = 225,
            Top = 120,
            Width = 75
        };

        AcceptButton = salvar;
        CancelButton = cancelar;
        Controls.Add(salvar);
        Controls.Add(cancelar);
    }
}

public class PedidoForm : Form
{
    private readonly TextBox cliente = new();
    private readonly NumericUpDown peso = new();
    private readonly NumericUpDown prioridade = new();
    private readonly NumericUpDown latitude = new();
    private readonly NumericUpDown longitude = new();

    public PedidoForm(Pedido? pedido = null)
    {
        Text = pedido is null ? "Adicionar pedido" : "Editar pedido";
        FormBorderStyle = FormBorderStyle.FixedDialog;
        StartPosition = FormStartPosition.CenterParent;
        MaximizeBox = false;
        MinimizeBox = false;
        ClientSize = new Size(360, 300);
        Font = new Font("Segoe UI", 9F);

        CriarCampoTexto("Cliente", cliente, 20, pedido?.Cliente ?? "");
        CriarCampoNumero("Peso kg", peso, 76, 1, 50000, pedido?.PesoKg ?? 100, 0, 1);
        CriarCampoNumero("Prioridade", prioridade, 120, 1, 10, pedido?.Prioridade ?? 1, 0, 1);
        CriarCampoNumero("Latitude", latitude, 164, -90, 90, (decimal)(pedido?.Latitude ?? -23.55052), 6, 0.000001M);
        CriarCampoNumero("Longitude", longitude, 208, -180, 180, (decimal)(pedido?.Longitude ?? -46.633308), 6, 0.000001M);
        CriarBotoes();
    }

    public string Cliente => cliente.Text.Trim();
    public int PesoKg => (int)peso.Value;
    public int Prioridade => (int)prioridade.Value;
    public double Latitude => (double)latitude.Value;
    public double Longitude => (double)longitude.Value;

    protected override void OnFormClosing(FormClosingEventArgs e)
    {
        if (DialogResult == DialogResult.OK && string.IsNullOrWhiteSpace(cliente.Text))
        {
            MessageBox.Show("Informe o nome do cliente.", "Campo obrigatorio", MessageBoxButtons.OK, MessageBoxIcon.Warning);
            e.Cancel = true;
        }

        base.OnFormClosing(e);
    }

    private void CriarCampoTexto(string rotulo, TextBox campo, int top, string valor)
    {
        Label label = new() { Text = rotulo, Left = 18, Top = top, Width = 120 };
        campo.Left = 150;
        campo.Top = top - 3;
        campo.Width = 175;
        campo.Text = valor;
        Controls.Add(label);
        Controls.Add(campo);
    }

    private void CriarCampoNumero(
        string rotulo,
        NumericUpDown campo,
        int top,
        decimal minimo,
        decimal maximo,
        decimal valor,
        int casasDecimais,
        decimal incremento)
    {
        Label label = new() { Text = rotulo, Left = 18, Top = top, Width = 120 };
        campo.Left = 150;
        campo.Top = top - 3;
        campo.Width = 175;
        campo.Minimum = minimo;
        campo.Maximum = maximo;
        campo.Value = Math.Min(Math.Max(valor, minimo), maximo);
        campo.DecimalPlaces = casasDecimais;
        campo.Increment = incremento;
        Controls.Add(label);
        Controls.Add(campo);
    }

    private void CriarBotoes()
    {
        Button salvar = new()
        {
            Text = "Salvar",
            DialogResult = DialogResult.OK,
            Left = 170,
            Top = 252,
            Width = 75
        };
        Button cancelar = new()
        {
            Text = "Cancelar",
            DialogResult = DialogResult.Cancel,
            Left = 250,
            Top = 252,
            Width = 75
        };

        AcceptButton = salvar;
        CancelButton = cancelar;
        Controls.Add(salvar);
        Controls.Add(cancelar);
    }
}

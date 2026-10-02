#nullable enable

namespace ProjetoOrdenacao;

public class MainForm : Form
{
    private readonly Ponto deposito = DadosExemplo.Deposito;
    private readonly List<Veiculo> veiculos = DadosExemplo.CriarVeiculos();
    private readonly List<Pedido> pedidos = DadosExemplo.CriarPedidos();

    private readonly RouteMapPanel mapa = new();
    private readonly DataGridView gradeVeiculos = new();
    private readonly DataGridView gradePedidos = new();
    private readonly TextBox resumo = new();
    private readonly Label indicadorDistancia = new();
    private readonly Label indicadorPedidos = new();
    private readonly Label indicadorVeiculos = new();

    public MainForm()
    {
        Text = "Projeto AED3 - Melhor rota por proximidade";
        MinimumSize = new Size(1100, 720);
        StartPosition = FormStartPosition.CenterScreen;
        BackColor = Color.FromArgb(246, 248, 251);
        Font = new Font("Segoe UI", 9F);

        MontarLayout();
        CarregarDados();
        CalcularRotas();
    }

    private void MontarLayout()
    {
        TableLayoutPanel raiz = new()
        {
            Dock = DockStyle.Fill,
            ColumnCount = 2,
            RowCount = 3,
            Padding = new Padding(18),
            BackColor = BackColor
        };
        raiz.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, 390));
        raiz.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100));
        raiz.RowStyles.Add(new RowStyle(SizeType.Absolute, 96));
        raiz.RowStyles.Add(new RowStyle(SizeType.Percent, 100));
        raiz.RowStyles.Add(new RowStyle(SizeType.Absolute, 190));
        Controls.Add(raiz);

        Panel cabecalho = CriarCabecalho();
        raiz.SetColumnSpan(cabecalho, 2);
        raiz.Controls.Add(cabecalho, 0, 0);

        TableLayoutPanel lateral = new()
        {
            Dock = DockStyle.Fill,
            RowCount = 2,
            ColumnCount = 1,
            Margin = new Padding(0, 10, 14, 10)
        };
        lateral.RowStyles.Add(new RowStyle(SizeType.Absolute, 170));
        lateral.RowStyles.Add(new RowStyle(SizeType.Percent, 100));
        raiz.Controls.Add(lateral, 0, 1);

        lateral.Controls.Add(CriarGrupo("Veiculos", gradeVeiculos, AdicionarVeiculo, EditarVeiculo, ExcluirVeiculo), 0, 0);
        lateral.Controls.Add(CriarGrupo("Pedidos", gradePedidos, AdicionarPedido, EditarPedido, ExcluirPedido), 0, 1);

        mapa.Dock = DockStyle.Fill;
        mapa.Margin = new Padding(0, 10, 0, 10);
        raiz.Controls.Add(mapa, 1, 1);

        Panel painelResumo = CriarPainelResumo();
        raiz.SetColumnSpan(painelResumo, 2);
        raiz.Controls.Add(painelResumo, 0, 2);
    }

    private Panel CriarCabecalho()
    {
        Panel painel = new()
        {
            Dock = DockStyle.Fill,
            BackColor = Color.White,
            Padding = new Padding(18),
            Margin = new Padding(0, 0, 0, 4)
        };

        Label titulo = new()
        {
            AutoSize = true,
            Text = "Melhor rota por proximidade",
            Font = new Font("Segoe UI Semibold", 18F),
            ForeColor = Color.FromArgb(24, 38, 55),
            Location = new Point(0, 4)
        };
        painel.Controls.Add(titulo);

        Label subtitulo = new()
        {
            AutoSize = true,
            Text = "Ordena enderecos proximos, respeita capacidade de carga e reduz a distancia percorrida.",
            Font = new Font("Segoe UI", 10F),
            ForeColor = Color.FromArgb(93, 107, 124),
            Location = new Point(2, 42)
        };
        painel.Controls.Add(subtitulo);

        Button botaoCalcular = new()
        {
            Text = "Calcular rotas",
            Anchor = AnchorStyles.Top | AnchorStyles.Right,
            Size = new Size(150, 38),
            Location = new Point(painel.Width - 168, 20),
            BackColor = Color.FromArgb(35, 99, 235),
            ForeColor = Color.White,
            FlatStyle = FlatStyle.Flat
        };
        botaoCalcular.FlatAppearance.BorderSize = 0;
        botaoCalcular.Click += (_, _) => CalcularRotas();
        painel.Controls.Add(botaoCalcular);
        painel.Resize += (_, _) => botaoCalcular.Left = painel.Width - botaoCalcular.Width - 18;

        return painel;
    }

    private GroupBox CriarGrupo(
        string titulo,
        DataGridView grade,
        EventHandler adicionar,
        EventHandler editar,
        EventHandler excluir)
    {
        GroupBox grupo = new()
        {
            Text = titulo,
            Dock = DockStyle.Fill,
            Padding = new Padding(10),
            BackColor = Color.White,
            ForeColor = Color.FromArgb(36, 48, 67)
        };

        ConfigurarGrade(grade);

        TableLayoutPanel conteudo = new()
        {
            Dock = DockStyle.Fill,
            RowCount = 2,
            ColumnCount = 1
        };
        conteudo.RowStyles.Add(new RowStyle(SizeType.Absolute, 34));
        conteudo.RowStyles.Add(new RowStyle(SizeType.Percent, 100));

        FlowLayoutPanel barra = new()
        {
            Dock = DockStyle.Fill,
            FlowDirection = FlowDirection.LeftToRight,
            WrapContents = false,
            Padding = new Padding(0, 0, 0, 4)
        };

        barra.Controls.Add(CriarBotaoAcao("Adicionar", adicionar));
        barra.Controls.Add(CriarBotaoAcao("Editar", editar));
        barra.Controls.Add(CriarBotaoAcao("Excluir", excluir));

        conteudo.Controls.Add(barra, 0, 0);
        conteudo.Controls.Add(grade, 0, 1);
        grupo.Controls.Add(conteudo);
        return grupo;
    }

    private static Button CriarBotaoAcao(string texto, EventHandler aoClicar)
    {
        Button botao = new()
        {
            Text = texto,
            Width = 86,
            Height = 27,
            Margin = new Padding(0, 0, 6, 0),
            FlatStyle = FlatStyle.Flat,
            BackColor = Color.FromArgb(238, 242, 247),
            ForeColor = Color.FromArgb(36, 48, 67)
        };
        botao.FlatAppearance.BorderColor = Color.FromArgb(205, 213, 225);
        botao.Click += aoClicar;
        return botao;
    }

    private Panel CriarPainelResumo()
    {
        Panel painel = new()
        {
            Dock = DockStyle.Fill,
            BackColor = Color.White,
            Padding = new Padding(18),
            Margin = new Padding(0)
        };

        TableLayoutPanel conteudo = new()
        {
            Dock = DockStyle.Fill,
            ColumnCount = 4,
            RowCount = 1
        };
        conteudo.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, 180));
        conteudo.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, 180));
        conteudo.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, 180));
        conteudo.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100));
        painel.Controls.Add(conteudo);

        conteudo.Controls.Add(CriarIndicador("Distancia total", indicadorDistancia), 0, 0);
        conteudo.Controls.Add(CriarIndicador("Pedidos atendidos", indicadorPedidos), 1, 0);
        conteudo.Controls.Add(CriarIndicador("Veiculos usados", indicadorVeiculos), 2, 0);

        resumo.Dock = DockStyle.Fill;
        resumo.Multiline = true;
        resumo.ReadOnly = true;
        resumo.ScrollBars = ScrollBars.Vertical;
        resumo.BorderStyle = BorderStyle.FixedSingle;
        resumo.Font = new Font("Consolas", 9F);
        resumo.BackColor = Color.FromArgb(250, 252, 255);
        conteudo.Controls.Add(resumo, 3, 0);

        return painel;
    }

    private static Panel CriarIndicador(string titulo, Label valor)
    {
        Panel painel = new()
        {
            Dock = DockStyle.Fill,
            Padding = new Padding(0, 8, 16, 8)
        };

        Label labelTitulo = new()
        {
            Dock = DockStyle.Top,
            Height = 26,
            Text = titulo,
            ForeColor = Color.FromArgb(93, 107, 124),
            Font = new Font("Segoe UI", 9F)
        };

        valor.Dock = DockStyle.Top;
        valor.Height = 44;
        valor.Text = "-";
        valor.ForeColor = Color.FromArgb(24, 38, 55);
        valor.Font = new Font("Segoe UI Semibold", 17F);

        painel.Controls.Add(valor);
        painel.Controls.Add(labelTitulo);
        return painel;
    }

    private static void ConfigurarGrade(DataGridView grade)
    {
        grade.Dock = DockStyle.Fill;
        grade.ReadOnly = true;
        grade.AllowUserToAddRows = false;
        grade.AllowUserToDeleteRows = false;
        grade.AllowUserToResizeRows = false;
        grade.RowHeadersVisible = false;
        grade.SelectionMode = DataGridViewSelectionMode.FullRowSelect;
        grade.AutoSizeColumnsMode = DataGridViewAutoSizeColumnsMode.Fill;
        grade.BackgroundColor = Color.White;
        grade.BorderStyle = BorderStyle.None;
        grade.EnableHeadersVisualStyles = false;
        grade.ColumnHeadersDefaultCellStyle.BackColor = Color.FromArgb(238, 242, 247);
        grade.ColumnHeadersDefaultCellStyle.ForeColor = Color.FromArgb(36, 48, 67);
        grade.ColumnHeadersDefaultCellStyle.Font = new Font("Segoe UI Semibold", 9F);
        grade.CellDoubleClick += (_, _) =>
        {
            if (grade.Name == "gradeVeiculos")
            {
                ((MainForm)grade.FindForm()!).EditarVeiculo(grade, EventArgs.Empty);
            }
            else if (grade.Name == "gradePedidos")
            {
                ((MainForm)grade.FindForm()!).EditarPedido(grade, EventArgs.Empty);
            }
        };
    }

    private void CarregarDados()
    {
        gradeVeiculos.Name = "gradeVeiculos";
        gradePedidos.Name = "gradePedidos";

        List<object> dadosVeiculos = new();
        foreach (Veiculo veiculo in veiculos)
        {
            dadosVeiculos.Add(new
            {
                veiculo.Id,
                veiculo.Placa,
                CapacidadeKg = veiculo.CapacidadeKg
            });
        }

        List<object> dadosPedidos = new();
        foreach (Pedido pedido in pedidos)
        {
            dadosPedidos.Add(new
            {
                pedido.Id,
                pedido.Cliente,
                pedido.PesoKg,
                pedido.Prioridade,
                Latitude = pedido.Latitude.ToString("F5"),
                Longitude = pedido.Longitude.ToString("F5")
            });
        }

        gradeVeiculos.DataSource = dadosVeiculos;
        gradePedidos.DataSource = dadosPedidos;

        OcultarColunaId(gradeVeiculos);
        OcultarColunaId(gradePedidos);
    }

    private static void OcultarColunaId(DataGridView grade)
    {
        DataGridViewColumn? colunaId = grade.Columns["Id"];
        if (colunaId is not null)
        {
            colunaId.Visible = false;
        }
    }

    private void AdicionarVeiculo(object? sender, EventArgs e)
    {
        using VeiculoForm form = new();
        if (form.ShowDialog(this) != DialogResult.OK)
        {
            return;
        }

        int novoId = veiculos.Count == 0 ? 1 : veiculos.Max(v => v.Id) + 1;
        veiculos.Add(new Veiculo(novoId, form.Placa, form.CapacidadeKg));
        AtualizarTela();
    }

    private void EditarVeiculo(object? sender, EventArgs e)
    {
        int? id = ObterIdSelecionado(gradeVeiculos);
        if (id is null)
        {
            MessageBox.Show("Selecione um veiculo para editar.", "Editar veiculo", MessageBoxButtons.OK, MessageBoxIcon.Information);
            return;
        }

        int indice = veiculos.FindIndex(v => v.Id == id.Value);
        if (indice < 0)
        {
            return;
        }

        using VeiculoForm form = new(veiculos[indice]);
        if (form.ShowDialog(this) != DialogResult.OK)
        {
            return;
        }

        veiculos[indice] = new Veiculo(id.Value, form.Placa, form.CapacidadeKg);
        AtualizarTela();
    }

    private void ExcluirVeiculo(object? sender, EventArgs e)
    {
        int? id = ObterIdSelecionado(gradeVeiculos);
        if (id is null)
        {
            MessageBox.Show("Selecione um veiculo para excluir.", "Excluir veiculo", MessageBoxButtons.OK, MessageBoxIcon.Information);
            return;
        }

        DialogResult confirmacao = MessageBox.Show(
            "Deseja excluir o veiculo selecionado?",
            "Excluir veiculo",
            MessageBoxButtons.YesNo,
            MessageBoxIcon.Question);

        if (confirmacao != DialogResult.Yes)
        {
            return;
        }

        veiculos.RemoveAll(v => v.Id == id.Value);
        AtualizarTela();
    }

    private void AdicionarPedido(object? sender, EventArgs e)
    {
        using PedidoForm form = new();
        if (form.ShowDialog(this) != DialogResult.OK)
        {
            return;
        }

        int novoId = pedidos.Count == 0 ? 1 : pedidos.Max(p => p.Id) + 1;
        pedidos.Add(new Pedido(novoId, form.Cliente, form.PesoKg, form.Latitude, form.Longitude, form.Prioridade));
        AtualizarTela();
    }

    private void EditarPedido(object? sender, EventArgs e)
    {
        int? id = ObterIdSelecionado(gradePedidos);
        if (id is null)
        {
            MessageBox.Show("Selecione um pedido para editar.", "Editar pedido", MessageBoxButtons.OK, MessageBoxIcon.Information);
            return;
        }

        int indice = pedidos.FindIndex(p => p.Id == id.Value);
        if (indice < 0)
        {
            return;
        }

        using PedidoForm form = new(pedidos[indice]);
        if (form.ShowDialog(this) != DialogResult.OK)
        {
            return;
        }

        pedidos[indice] = new Pedido(id.Value, form.Cliente, form.PesoKg, form.Latitude, form.Longitude, form.Prioridade);
        AtualizarTela();
    }

    private void ExcluirPedido(object? sender, EventArgs e)
    {
        int? id = ObterIdSelecionado(gradePedidos);
        if (id is null)
        {
            MessageBox.Show("Selecione um pedido para excluir.", "Excluir pedido", MessageBoxButtons.OK, MessageBoxIcon.Information);
            return;
        }

        DialogResult confirmacao = MessageBox.Show(
            "Deseja excluir o pedido selecionado?",
            "Excluir pedido",
            MessageBoxButtons.YesNo,
            MessageBoxIcon.Question);

        if (confirmacao != DialogResult.Yes)
        {
            return;
        }

        pedidos.RemoveAll(p => p.Id == id.Value);
        AtualizarTela();
    }

    private static int? ObterIdSelecionado(DataGridView grade)
    {
        if (grade.CurrentRow is null || grade.CurrentRow.Cells["Id"].Value is null)
        {
            return null;
        }

        return Convert.ToInt32(grade.CurrentRow.Cells["Id"].Value);
    }

    private void AtualizarTela()
    {
        CarregarDados();
        CalcularRotas();
    }

    private void CalcularRotas()
    {
        ResultadoRoteirizacao resultado = OtimizadorRotas.Otimizar(pedidos, veiculos, deposito);

        indicadorDistancia.Text = $"{resultado.DistanciaTotal:F2} km";
        indicadorPedidos.Text = $"{resultado.TotalPedidosAtendidos}/{pedidos.Count}";
        indicadorVeiculos.Text = resultado.Rotas.Count.ToString();
        resumo.Text = MontarResumo(resultado);

        mapa.Atualizar(deposito, pedidos, resultado);
    }

    private static string MontarResumo(ResultadoRoteirizacao resultado)
    {
        StringBuilder texto = new();
        texto.AppendLine(resultado.Metodo);
        texto.AppendLine();

        foreach (Rota rota in resultado.Rotas)
        {
            texto.AppendLine($"{rota.Veiculo.Placa} | carga {rota.CargaTotal}/{rota.Veiculo.CapacidadeKg} kg | {rota.DistanciaTotal:F2} km");
            texto.Append("Deposito");
            foreach (Pedido pedido in rota.Pedidos)
            {
                texto.Append(" -> ");
                texto.Append(pedido.Cliente);
            }

            texto.AppendLine(" -> Deposito");
            texto.AppendLine();
        }

        if (resultado.PedidosNaoAtendidos.Count > 0)
        {
            texto.AppendLine("Pedidos nao atendidos por capacidade:");
            foreach (Pedido pedido in resultado.PedidosNaoAtendidos)
            {
                texto.AppendLine($"- {pedido.Cliente}: {pedido.PesoKg} kg");
            }
        }

        return texto.ToString();
    }
}

public class RouteMapPanel : Panel
{
    private readonly Color[] cores =
    {
        Color.FromArgb(35, 99, 235),
        Color.FromArgb(16, 150, 72),
        Color.FromArgb(220, 104, 3),
        Color.FromArgb(126, 58, 242)
    };

    private Ponto? deposito;
    private List<Pedido> pedidos = new();
    private ResultadoRoteirizacao? resultado;

    public RouteMapPanel()
    {
        DoubleBuffered = true;
        BackColor = Color.White;
        Padding = new Padding(18);
    }

    public void Atualizar(Ponto novoDeposito, List<Pedido> novosPedidos, ResultadoRoteirizacao novoResultado)
    {
        deposito = novoDeposito;
        pedidos = novosPedidos;
        resultado = novoResultado;
        Invalidate();
    }

    protected override void OnPaint(PaintEventArgs e)
    {
        base.OnPaint(e);
        Graphics g = e.Graphics;
        g.SmoothingMode = System.Drawing.Drawing2D.SmoothingMode.AntiAlias;
        Rectangle area = new(Padding.Left, Padding.Top, Width - Padding.Horizontal, Height - Padding.Vertical);

        using Font titulo = new("Segoe UI Semibold", 12F);
        using Font fonte = new("Segoe UI", 8F);
        using Brush texto = new SolidBrush(Color.FromArgb(36, 48, 67));
        g.DrawString("Mapa esquematico das rotas", titulo, texto, area.Left, area.Top);

        if (deposito is null || resultado is null)
        {
            g.DrawString("Calcule as rotas para visualizar o trajeto.", fonte, texto, area.Left, area.Top + 34);
            return;
        }

        Rectangle mapaArea = new(area.Left, area.Top + 44, area.Width, area.Height - 44);
        List<Ponto> pontos = new() { deposito };
        foreach (Pedido pedido in pedidos)
        {
            pontos.Add(pedido.Ponto);
        }

        double minLat = pontos[0].Latitude;
        double maxLat = pontos[0].Latitude;
        double minLon = pontos[0].Longitude;
        double maxLon = pontos[0].Longitude;
        foreach (Ponto ponto in pontos)
        {
            if (ponto.Latitude < minLat)
            {
                minLat = ponto.Latitude;
            }

            if (ponto.Latitude > maxLat)
            {
                maxLat = ponto.Latitude;
            }

            if (ponto.Longitude < minLon)
            {
                minLon = ponto.Longitude;
            }

            if (ponto.Longitude > maxLon)
            {
                maxLon = ponto.Longitude;
            }
        }
        double margemLat = Math.Max((maxLat - minLat) * 0.12, 0.002);
        double margemLon = Math.Max((maxLon - minLon) * 0.12, 0.002);
        minLat -= margemLat;
        maxLat += margemLat;
        minLon -= margemLon;
        maxLon += margemLon;

        PointF Converter(Ponto ponto)
        {
            float x = (float)(mapaArea.Left + (ponto.Longitude - minLon) / (maxLon - minLon) * mapaArea.Width);
            float y = (float)(mapaArea.Bottom - (ponto.Latitude - minLat) / (maxLat - minLat) * mapaArea.Height);
            return new PointF(x, y);
        }

        using Pen grade = new(Color.FromArgb(230, 235, 243), 1);
        for (int i = 1; i < 5; i++)
        {
            float x = mapaArea.Left + mapaArea.Width * i / 5F;
            float y = mapaArea.Top + mapaArea.Height * i / 5F;
            g.DrawLine(grade, x, mapaArea.Top, x, mapaArea.Bottom);
            g.DrawLine(grade, mapaArea.Left, y, mapaArea.Right, y);
        }

        for (int i = 0; i < resultado.Rotas.Count; i++)
        {
            Rota rota = resultado.Rotas[i];
            Color cor = cores[i % cores.Length];
            using Pen linha = new(cor, 3);
            Ponto anterior = deposito;

            foreach (Pedido pedido in rota.Pedidos)
            {
                g.DrawLine(linha, Converter(anterior), Converter(pedido.Ponto));
                anterior = pedido.Ponto;
            }

            g.DrawLine(linha, Converter(anterior), Converter(deposito));
        }

        PointF pontoDeposito = Converter(deposito);
        using Brush depositoBrush = new SolidBrush(Color.FromArgb(20, 31, 48));
        g.FillEllipse(depositoBrush, pontoDeposito.X - 7, pontoDeposito.Y - 7, 14, 14);
        g.DrawString("Deposito", fonte, texto, pontoDeposito.X + 8, pontoDeposito.Y - 8);

        foreach (Pedido pedido in pedidos)
        {
            PointF ponto = Converter(pedido.Ponto);
            using Brush pedidoBrush = new SolidBrush(Color.FromArgb(255, 255, 255));
            using Pen borda = new(Color.FromArgb(93, 107, 124), 2);
            g.FillEllipse(pedidoBrush, ponto.X - 5, ponto.Y - 5, 10, 10);
            g.DrawEllipse(borda, ponto.X - 5, ponto.Y - 5, 10, 10);
            g.DrawString(pedido.Cliente, fonte, texto, ponto.X + 7, ponto.Y - 7);
        }
    }
}

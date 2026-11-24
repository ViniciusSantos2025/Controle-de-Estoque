"""
estilo.py - Aparência da tela: cores, fontes e estilos dos componentes.

Usamos o ttk (que já vem com o Python) com o tema "clam", porque ele
deixa trocar as cores dos botões, tabelas e abas. Não precisa instalar
nada e funciona normalmente quando o programa vira .exe (PyInstaller).

Para mudar uma cor do programa inteiro, basta mudar aqui.
"""

from tkinter import font as tkfont
from tkinter import ttk

# --- Paleta de cores ------------------------------------------------------
FUNDO = "#F4F6F8"           # cinza bem claro (fundo das telas)
BRANCO = "#FFFFFF"
TEXTO = "#1F2937"           # quase preto (texto normal)
TEXTO_SUAVE = "#5B6472"     # cinza (dicas e explicações)
BORDA = "#CBD2DB"
PRINCIPAL = "#1E3A5F"       # azul escuro (topo, cabeçalho das tabelas)
PRINCIPAL_ESCURO = "#152B47"
LINHA_ALTERNADA = "#EAF0F7" # linhas "zebradas" das tabelas
SELECAO = "#CFE3FF"         # linha selecionada na tabela
ABA_INATIVA = "#DDE3EA"

# Cores das ações (uma cor para cada tipo de movimento)
AZUL = "#1D4ED8"            # Venda
AZUL_ESCURO = "#1E3A8A"
VERDE = "#15803D"           # Entrada / sucesso
VERDE_ESCURO = "#14532D"
LARANJA = "#C2410C"         # Saída sem venda
LARANJA_ESCURO = "#7C2D12"
VERMELHO = "#B91C1C"        # erros, falta, estoque zerado/negativo

# Fundos claros usados nas mensagens que aparecem na tela
VERDE_CLARO = "#DCFCE7"
VERMELHO_CLARO = "#FEE2E2"
AMARELO_CLARO = "#FEF3C7"

# Cores do aviso no topo (o fundo do topo é escuro, então usamos tons claros)
TOPO_OK = "#86EFAC"         # verde claro
TOPO_ALERTA = "#FCD34D"     # amarelo

# Cores das mensagens: tipo -> (cor do texto, cor do fundo)
CORES_MENSAGEM = {
    "ok": (VERDE_ESCURO, VERDE_CLARO),
    "erro": (VERMELHO, VERMELHO_CLARO),
    "alerta": (LARANJA_ESCURO, AMARELO_CLARO),
}

# --- Fontes ---------------------------------------------------------------
FONTE = "Segoe UI"   # fonte padrão do Windows
TAMANHO = 12         # tamanho mínimo usado no programa


def configurar_estilo(janela):
    """Aplica cores e fontes em todos os componentes ttk da janela."""
    # 1) Aumenta as fontes padrão do Tkinter (vale para campos, listas etc.)
    for nome in ("TkDefaultFont", "TkTextFont", "TkMenuFont", "TkHeadingFont"):
        tkfont.nametofont(nome).configure(family=FONTE, size=TAMANHO)
    # Fonte da lista que abre ao clicar num Combobox (menu de escolha)
    janela.option_add("*TCombobox*Listbox.font", (FONTE, TAMANHO + 1))
    janela.configure(background=FUNDO)

    s = ttk.Style(janela)
    s.theme_use("clam")

    # 2) Padrão para todos os componentes
    s.configure(".", background=FUNDO, foreground=TEXTO, font=(FONTE, TAMANHO))

    # 3) Textos
    s.configure("TLabel", background=FUNDO, foreground=TEXTO)
    s.configure("Titulo.TLabel", font=(FONTE, 17, "bold"), foreground=PRINCIPAL)
    s.configure("Campo.TLabel", font=(FONTE, 13, "bold"))
    s.configure("Dica.TLabel", foreground=TEXTO_SUAVE)
    s.configure("Mensagem.TLabel", font=(FONTE, 13, "bold"), padding=(14, 10))

    # 4) Faixa do topo ("Quem está usando")
    s.configure("Topo.TFrame", background=PRINCIPAL)
    s.configure("Topo.TLabel", background=PRINCIPAL, foreground=BRANCO,
                font=(FONTE, 15, "bold"))
    s.configure("TopoAviso.TLabel", background=PRINCIPAL, foreground=TOPO_ALERTA,
                font=(FONTE, 13, "bold"))

    # 5) Cartões do resumo (aba Estoque)
    s.configure("Cartao.TFrame", background=BRANCO, relief="solid", borderwidth=1,
                bordercolor=BORDA)
    s.configure("CartaoTitulo.TLabel", background=BRANCO, foreground=TEXTO_SUAVE,
                font=(FONTE, 12))
    s.configure("CartaoNumero.TLabel", background=BRANCO, foreground=PRINCIPAL,
                font=(FONTE, 24, "bold"))

    # 6) Quadros com título
    s.configure("TLabelframe", background=FUNDO, bordercolor=BORDA)
    s.configure("TLabelframe.Label", background=FUNDO, foreground=PRINCIPAL,
                font=(FONTE, 13, "bold"))

    # 7) Campos de digitar e menus de escolha
    s.configure("TEntry", padding=8, fieldbackground=BRANCO, bordercolor=BORDA,
                lightcolor=BORDA)
    s.map("TEntry", bordercolor=[("focus", AZUL)], lightcolor=[("focus", AZUL)])
    s.configure("TCombobox", padding=8, fieldbackground=BRANCO, bordercolor=BORDA,
                lightcolor=BORDA, arrowsize=18)
    s.map(
        "TCombobox",
        fieldbackground=[("readonly", BRANCO)],
        selectbackground=[("readonly", BRANCO)],
        selectforeground=[("readonly", TEXTO)],
        bordercolor=[("focus", AZUL)],
    )

    # 8) Abas
    s.configure("TNotebook", background=FUNDO, borderwidth=0, tabmargins=(10, 8, 10, 0))
    s.configure("TNotebook.Tab", padding=(22, 10), font=(FONTE, 13, "bold"),
                background=ABA_INATIVA, foreground=TEXTO_SUAVE, bordercolor=BORDA)
    s.map(
        "TNotebook.Tab",
        background=[("selected", FUNDO)],
        foreground=[("selected", PRINCIPAL)],
    )

    # 9) Tabelas: linhas mais altas e cabeçalho azul escuro.
    # A altura da linha é calculada pela fonte, para não cortar o texto
    # em telas com zoom (125%, 150%...).
    altura_linha = tkfont.Font(family=FONTE, size=TAMANHO).metrics("linespace") + 14
    s.configure("Treeview", background=BRANCO, fieldbackground=BRANCO, foreground=TEXTO,
                rowheight=altura_linha, bordercolor=BORDA)
    s.map("Treeview", background=[("selected", SELECAO)], foreground=[("selected", TEXTO)])
    s.configure("Treeview.Heading", background=PRINCIPAL, foreground=BRANCO,
                font=(FONTE, TAMANHO, "bold"), padding=(8, 8), relief="flat")
    s.map("Treeview.Heading", background=[("active", PRINCIPAL_ESCURO)])

    # 10) Botões
    s.configure("TButton", padding=(16, 10))
    _botao_colorido(s, "Venda.TButton", AZUL, AZUL_ESCURO)
    _botao_colorido(s, "Entrada.TButton", VERDE, VERDE_ESCURO)
    _botao_colorido(s, "Saida.TButton", LARANJA, LARANJA_ESCURO)
    _botao_colorido(s, "Principal.TButton", PRINCIPAL, PRINCIPAL_ESCURO)


def _botao_colorido(s, nome, cor, cor_ao_passar_mouse):
    """Cria um estilo de botão grande, com fundo colorido e texto branco."""
    s.configure(
        nome,
        background=cor, foreground=BRANCO, font=(FONTE, 15, "bold"),
        padding=(26, 16), borderwidth=0,
        # No tema "clam" a borda tem 3 cores; igualamos tudo para ficar "liso"
        bordercolor=cor, lightcolor=cor, darkcolor=cor, focuscolor=BRANCO,
    )
    s.map(
        nome,
        background=[("pressed", cor_ao_passar_mouse), ("active", cor_ao_passar_mouse)],
        lightcolor=[("pressed", cor_ao_passar_mouse), ("active", cor_ao_passar_mouse)],
        darkcolor=[("pressed", cor_ao_passar_mouse), ("active", cor_ao_passar_mouse)],
    )

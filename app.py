"""
app.py - Tela do sistema (Tkinter).

Tkinter já vem junto com o Python no Windows, não precisa instalar nada.
Este arquivo só cuida da TELA. As regras ficam em banco.py e as cores e
fontes ficam em estilo.py.

Para abrir o programa:  python app.py
"""

import os
import sys
import tkinter as tk
import unicodedata
from tkinter import messagebox, ttk

import banco
import estilo


def pasta_do_programa():
    """Pasta onde o banco (estoque.db) fica guardado, ao lado do programa."""
    if getattr(sys, "frozen", False):  # quando virar .exe (PyInstaller)
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def simplificar(texto):
    """
    Deixa o texto em minúsculas e sem acentos, para a busca funcionar
    mesmo se a pessoa digitar "agua" procurando "Água".
    """
    sem_acento = unicodedata.normalize("NFD", texto)
    sem_acento = "".join(letra for letra in sem_acento if unicodedata.category(letra) != "Mn")
    return sem_acento.lower().strip()


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Controle de Estoque")
        self.geometry("1100x720")
        self.minsize(900, 600)
        try:
            self.state("zoomed")  # abre maximizado no Windows
        except tk.TclError:
            pass  # em outros sistemas "zoomed" não existe; tudo bem

        estilo.configurar_estilo(self)

        self.conn = banco.conectar(os.path.join(pasta_do_programa(), "estoque.db"))
        self.ids_por_nome = {}  # nome do produto -> id (para os menus de escolha)
        self.nomes_produtos = []  # todos os nomes, antes de aplicar a busca
        self.var_usuario = tk.StringVar()

        self._montar_topo()
        self.abas = ttk.Notebook(self)
        self.abas.pack(fill="both", expand=True, padx=16, pady=(4, 16))

        self._montar_aba_estoque()
        self._montar_aba_registrar()
        self._montar_aba_contagem()
        self._montar_aba_relatorios()

        self.atualizar_tudo()
        self.entrada_usuario.focus_set()  # o cursor já começa no campo do nome

    # ------------------------------------------------------------------
    # Ajudantes (pedaços pequenos usados em várias partes da tela)
    # ------------------------------------------------------------------
    def _criar_tabela(self, pai, colunas, altura):
        """
        Cria uma tabela (Treeview) com barra de rolagem.
        'colunas' é um dicionário: chave -> (título, largura, alinhamento).
        """
        quadro = ttk.Frame(pai)
        quadro.pack(fill="both", expand=True)

        tabela = ttk.Treeview(quadro, columns=list(colunas), show="headings", height=altura)
        for chave, (titulo, largura, alinhamento) in colunas.items():
            tabela.heading(chave, text=titulo, anchor=alinhamento)
            tabela.column(chave, width=largura, anchor=alinhamento)

        # "Etiquetas" (tags) mudam a aparência de uma linha:
        #   impar    -> fundo levemente azulado (linhas alternadas)
        #   vermelho -> texto vermelho e em negrito (problema!)
        tabela.tag_configure("impar", background=estilo.LINHA_ALTERNADA)
        tabela.tag_configure(
            "vermelho", foreground=estilo.VERMELHO, font=(estilo.FONTE, estilo.TAMANHO, "bold")
        )

        rolagem = ttk.Scrollbar(quadro, orient="vertical", command=tabela.yview)
        tabela.configure(yscrollcommand=rolagem.set)
        rolagem.pack(side="right", fill="y")
        tabela.pack(side="left", fill="both", expand=True)
        return tabela

    def _inserir_linha(self, tabela, numero_da_linha, valores, vermelho=False):
        """Coloca uma linha na tabela, alternando a cor de fundo."""
        etiquetas = []
        if numero_da_linha % 2 == 1:
            etiquetas.append("impar")
        if vermelho:
            etiquetas.append("vermelho")
        tabela.insert("", "end", values=valores, tags=etiquetas)

    def _campo(self, pai, linha, rotulo, variavel, largura, dica=""):
        """Cria um rótulo + campo de digitar, um embaixo do outro."""
        ttk.Label(pai, text=rotulo, style="Campo.TLabel").grid(
            row=linha, column=0, sticky="w", pady=(12, 4)
        )
        entrada = ttk.Entry(pai, textvariable=variavel, width=largura,
                            font=(estilo.FONTE, 13))
        entrada.grid(row=linha + 1, column=0, sticky="w")
        if dica:
            ttk.Label(pai, text=dica, style="Dica.TLabel").grid(
                row=linha + 1, column=1, sticky="w", padx=12
            )
        return entrada

    def _menu_de_produtos(self, pai, linha, variavel, mostrar_estoque=False):
        """
        Cria a linha de escolha do produto:
            Buscar: [_____]   [menu de produtos ▼]   (informação)
        O que for digitado em "Buscar" filtra a lista do menu.
        Devolve um dicionário com as partes, usado por _filtrar_menu.
        """
        ttk.Label(pai, text="Produto", style="Campo.TLabel").grid(
            row=linha, column=0, sticky="w", pady=(12, 4)
        )
        linha_produto = ttk.Frame(pai)
        linha_produto.grid(row=linha + 1, column=0, columnspan=2, sticky="w")

        var_busca = tk.StringVar()
        ttk.Label(linha_produto, text="Buscar:", style="Dica.TLabel").pack(side="left")
        ttk.Entry(linha_produto, textvariable=var_busca, width=14,
                  font=(estilo.FONTE, 13)).pack(side="left", padx=(6, 14))

        combo = ttk.Combobox(linha_produto, textvariable=variavel, state="readonly",
                             width=34, height=15, font=(estilo.FONTE, 13))
        combo.pack(side="left")

        # Texto ao lado do menu: estoque do produto ou "nenhum encontrado"
        info = ttk.Label(linha_produto, font=(estilo.FONTE, 13, "bold"))
        info.pack(side="left", padx=14)

        menu = {
            "busca": var_busca,
            "combo": combo,
            "produto": variavel,
            "info": info,
            # Na Contagem o estoque fica escondido, para a pessoa contar "às cegas"
            "mostrar_estoque": mostrar_estoque,
        }
        # Sempre que a busca ou o produto escolhido mudar, a tela se atualiza
        var_busca.trace_add("write", lambda *_: self._filtrar_menu(menu))
        variavel.trace_add("write", lambda *_: self._atualizar_info_produto(menu))
        return menu

    def _filtrar_menu(self, menu):
        """Deixa no menu só os produtos cujo nome contém o texto da busca."""
        termo = simplificar(menu["busca"].get())
        encontrados = [n for n in self.nomes_produtos if termo in simplificar(n)]
        menu["combo"]["values"] = encontrados

        if termo and len(encontrados) == 1:
            # Só sobrou um produto: já deixamos ele escolhido
            menu["produto"].set(encontrados[0])
        elif menu["produto"].get() not in encontrados:
            # O produto escolhido não bate com a busca: limpa para evitar engano
            menu["produto"].set("")
        self._atualizar_info_produto(menu)

    def _atualizar_info_produto(self, menu):
        """Mostra ao lado do menu o estoque atual (ou um aviso da busca)."""
        info = menu["info"]
        if not menu["combo"]["values"]:
            info.configure(text="Nenhum produto com esse nome", foreground=estilo.VERMELHO)
            return
        produto_id = self.ids_por_nome.get(menu["produto"].get())
        if not menu["mostrar_estoque"] or produto_id is None:
            info.configure(text="")
            return
        estoque = banco.estoque_atual(self.conn, produto_id)
        if estoque <= 0:
            info.configure(text=f"Estoque atual: {estoque} (zerado)", foreground=estilo.VERMELHO)
        else:
            info.configure(text=f"Estoque atual: {estoque}", foreground=estilo.PRINCIPAL)

    def mostrar_mensagem(self, rotulo, texto, tipo):
        """
        Mostra uma mensagem colorida na própria tela.
        tipo: "ok" (verde), "erro" (vermelho) ou "alerta" (amarelo).
        """
        cor_texto, cor_fundo = estilo.CORES_MENSAGEM[tipo]
        rotulo.configure(text=texto, foreground=cor_texto, background=cor_fundo)

    def mostrar_erro(self, rotulo, erro):
        """Erro: aparece em vermelho na tela e também numa janela de aviso."""
        self.mostrar_mensagem(rotulo, f"✗  {erro}", "erro")
        messagebox.showerror("Não foi possível concluir", str(erro))

    # ------------------------------------------------------------------
    # Pedaços da tela
    # ------------------------------------------------------------------
    def _montar_topo(self):
        """Faixa azul no topo com o campo 'Quem está usando'."""
        topo = ttk.Frame(self, style="Topo.TFrame", padding=(20, 16))
        topo.pack(fill="x")

        ttk.Label(topo, text="Quem está usando:", style="Topo.TLabel").pack(side="left")
        self.entrada_usuario = ttk.Entry(
            topo, textvariable=self.var_usuario, width=22, font=(estilo.FONTE, 15, "bold")
        )
        self.entrada_usuario.pack(side="left", padx=12)

        # Aviso ao lado do campo: amarelo se estiver vazio, verde se preenchido
        self.lbl_aviso_usuario = ttk.Label(topo, style="TopoAviso.TLabel")
        self.lbl_aviso_usuario.pack(side="left", padx=8)

        # Toda vez que o texto do campo mudar, o aviso é atualizado
        self.var_usuario.trace_add("write", lambda *_: self._atualizar_aviso_usuario())
        self._atualizar_aviso_usuario()

    def _atualizar_aviso_usuario(self):
        if self.var_usuario.get().strip():
            self.lbl_aviso_usuario.configure(
                text="✓ Seu nome vai ficar gravado em cada registro",
                foreground=estilo.TOPO_OK,
            )
        else:
            self.lbl_aviso_usuario.configure(
                text="⚠ Digite seu nome antes de registrar qualquer coisa",
                foreground=estilo.TOPO_ALERTA,
            )

    def _montar_aba_estoque(self):
        aba = ttk.Frame(self.abas, padding=16)
        self.abas.add(aba, text="  Estoque  ")

        # --- Resumo: dois "cartões" com números grandes ---
        resumo = ttk.Frame(aba)
        resumo.pack(fill="x", pady=(0, 14))
        self.lbl_total_produtos = self._cartao(resumo, "Produtos cadastrados")
        self.lbl_total_zerados = self._cartao(resumo, "Com estoque zerado ou negativo")

        # A mensagem e o formulário são colocados "de baixo para cima" (side="bottom")
        # ANTES da tabela. Assim, se a janela for pequena, quem encolhe é a tabela,
        # e o formulário de cadastro nunca some da tela.
        self.msg_cadastro = ttk.Label(aba, style="Mensagem.TLabel")
        self.msg_cadastro.pack(side="bottom", anchor="w", pady=(10, 0))

        # --- Formulário de cadastro ---
        form = ttk.LabelFrame(aba, text="Cadastrar novo produto", padding=(16, 6, 16, 14))
        form.pack(side="bottom", fill="x", pady=(14, 0))

        self.var_novo_nome = tk.StringVar()
        self.var_novo_preco = tk.StringVar()
        self.var_novo_inicial = tk.StringVar(value="0")

        # Os campos ficam lado a lado, cada um com o nome em cima
        campos = [
            ("Nome do produto", self.var_novo_nome, 32),
            ("Preço (ex.: 4,50)", self.var_novo_preco, 12),
            ("Estoque inicial", self.var_novo_inicial, 10),
        ]
        for coluna, (rotulo, variavel, largura) in enumerate(campos):
            ttk.Label(form, text=rotulo, style="Campo.TLabel").grid(
                row=0, column=coluna, sticky="w", padx=(0, 16), pady=(6, 4)
            )
            ttk.Entry(form, textvariable=variavel, width=largura,
                      font=(estilo.FONTE, 13)).grid(row=1, column=coluna, sticky="w", padx=(0, 16))

        ttk.Button(
            form, text="Cadastrar produto", style="Principal.TButton",
            command=self.cadastrar_produto,
        ).grid(row=0, column=3, rowspan=2, sticky="s")

        # --- Tabela de produtos (ocupa todo o espaço que sobrar) ---
        self.tree_estoque = self._criar_tabela(
            aba,
            {
                "nome": ("Produto", 420, "w"),
                "preco": ("Preço", 140, "e"),
                "estoque": ("Estoque (sistema)", 180, "center"),
            },
            altura=8,
        )

    def _cartao(self, pai, titulo):
        """Cria um cartão branco com um título pequeno e um número grande."""
        cartao = ttk.Frame(pai, style="Cartao.TFrame", padding=(20, 12))
        cartao.pack(side="left", padx=(0, 14))
        ttk.Label(cartao, text=titulo, style="CartaoTitulo.TLabel").pack(anchor="w")
        numero = ttk.Label(cartao, text="0", style="CartaoNumero.TLabel")
        numero.pack(anchor="w")
        return numero

    def _montar_aba_registrar(self):
        aba = ttk.Frame(self.abas, padding=24)
        self.abas.add(aba, text="  Registrar movimento  ")

        self.var_produto_mov = tk.StringVar()
        self.var_qtd = tk.StringVar(value="1")
        self.var_motivo = tk.StringVar()

        ttk.Label(aba, text="Registrar venda, entrada ou saída", style="Titulo.TLabel").grid(
            row=0, column=0, columnspan=2, sticky="w"
        )
        ttk.Label(
            aba, text="Escolha o produto, digite a quantidade e clique no botão do que aconteceu.",
            style="Dica.TLabel",
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(2, 4))

        self.menu_mov = self._menu_de_produtos(aba, 2, self.var_produto_mov,
                                               mostrar_estoque=True)
        self._campo(aba, 4, "Quantidade", self.var_qtd, 10)
        self._campo(aba, 6, "Motivo", self.var_motivo, 42,
                    dica="Obrigatório só na saída sem venda")

        # --- Os três botões principais, um para cada tipo, com cores diferentes ---
        botoes = ttk.Frame(aba)
        botoes.grid(row=8, column=0, columnspan=2, sticky="w", pady=(26, 0))
        acoes = [
            (banco.VENDA, "VENDA", "Venda.TButton", "Vendeu para um cliente"),
            (banco.ENTRADA, "ENTRADA", "Entrada.TButton", "Chegou mercadoria"),
            (banco.SAIDA_SEM_VENDA, "SAÍDA SEM VENDA", "Saida.TButton",
             "Perda, quebra, vencido, consumo"),
        ]
        for coluna, (tipo, texto, estilo_botao, dica) in enumerate(acoes):
            ttk.Button(
                botoes, text=texto, style=estilo_botao, width=16,
                # "t=tipo" guarda o tipo de cada botão (senão todos usariam o último)
                command=lambda t=tipo: self.registrar_movimento(t),
            ).grid(row=0, column=coluna, padx=(0, 16), sticky="we")
            ttk.Label(botoes, text=dica, style="Dica.TLabel").grid(
                row=1, column=coluna, pady=(6, 0)
            )

        self.msg_mov = ttk.Label(aba, style="Mensagem.TLabel")
        self.msg_mov.grid(row=9, column=0, columnspan=2, sticky="w", pady=(20, 0))

    def _montar_aba_contagem(self):
        aba = ttk.Frame(self.abas, padding=24)
        self.abas.add(aba, text="  Contagem  ")

        self.var_produto_cont = tk.StringVar()
        self.var_contado = tk.StringVar()

        ttk.Label(aba, text="Contagem da prateleira", style="Titulo.TLabel").grid(
            row=0, column=0, columnspan=2, sticky="w"
        )
        ttk.Label(
            aba,
            text=(
                "Conte as unidades que estão na prateleira/geladeira SEM olhar o estoque\n"
                "do sistema. Depois digite aqui o número que você contou."
            ),
            style="Dica.TLabel", justify="left",
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(2, 4))

        self.menu_cont = self._menu_de_produtos(aba, 2, self.var_produto_cont)
        self._campo(aba, 4, "Quantidade contada", self.var_contado, 10)

        ttk.Button(
            aba, text="REGISTRAR CONTAGEM", style="Principal.TButton",
            command=self.registrar_contagem,
        ).grid(row=6, column=0, sticky="w", pady=(26, 0))

        self.msg_cont = ttk.Label(aba, style="Mensagem.TLabel")
        self.msg_cont.grid(row=7, column=0, columnspan=2, sticky="w", pady=(20, 0))

    def _montar_aba_relatorios(self):
        aba = ttk.Frame(self.abas, padding=16)
        self.abas.add(aba, text="  Relatórios  ")

        # --- Divergências ---
        quadro1 = ttk.LabelFrame(aba, text="Divergências (faltou ou sobrou produto)",
                                 padding=10)
        quadro1.pack(fill="both", expand=True)
        self.tree_div = self._criar_tabela(
            quadro1,
            {
                "data": ("Data", 150, "center"), "produto": ("Produto", 240, "w"),
                "esperado": ("Esperado", 100, "center"), "contado": ("Contado", 100, "center"),
                "dif": ("Diferença", 110, "center"), "valor": ("Valor", 120, "e"),
                "quem": ("Quem contou", 150, "center"),
            },
            altura=5,
        )
        self.lbl_total_falta = ttk.Label(
            quadro1, font=(estilo.FONTE, 14, "bold"), foreground=estilo.VERMELHO
        )
        self.lbl_total_falta.pack(anchor="w", pady=(10, 0))

        # --- Histórico ---
        quadro2 = ttk.LabelFrame(aba, text="Histórico de movimentações (não pode ser apagado)",
                                 padding=10)
        quadro2.pack(fill="both", expand=True, pady=(14, 0))
        self.tree_hist = self._criar_tabela(
            quadro2,
            {
                "data": ("Data", 140, "center"), "produto": ("Produto", 200, "w"),
                "tipo": ("Tipo", 320, "w"), "qtd": ("Qtd", 60, "center"),
                "motivo": ("Motivo", 200, "w"), "quem": ("Quem", 130, "center"),
            },
            altura=6,
        )

    # ------------------------------------------------------------------
    # Ações dos botões
    # ------------------------------------------------------------------
    def cadastrar_produto(self):
        nome = self.var_novo_nome.get().strip()
        try:
            banco.cadastrar_produto(
                self.conn,
                nome,
                self.var_novo_preco.get(),
                self.var_usuario.get(),
                self.var_novo_inicial.get(),
            )
        except banco.ErroDeRegra as erro:
            self.mostrar_erro(self.msg_cadastro, erro)
            return
        self.var_novo_nome.set("")
        self.var_novo_preco.set("")
        self.var_novo_inicial.set("0")
        self.atualizar_tudo()
        self.mostrar_mensagem(self.msg_cadastro, f"✓  Produto \"{nome}\" cadastrado.", "ok")

    def registrar_movimento(self, tipo):
        """Chamado por um dos três botões (Venda, Entrada ou Saída sem venda)."""
        nome = self.var_produto_mov.get()
        produto_id = self.ids_por_nome.get(nome)
        quantidade = self.var_qtd.get().strip()
        motivo = self.var_motivo.get().strip()

        # Saída sem venda pede confirmação, porque não pode ser desfeita.
        # (Se faltar produto ou motivo, nem pergunta: o erro aparece logo abaixo.)
        if tipo == banco.SAIDA_SEM_VENDA and produto_id is not None and motivo:
            confirmou = messagebox.askyesno(
                "Confirmar saída sem venda",
                f"Confirma a SAÍDA SEM VENDA de {quantidade} x {nome}?\n\n"
                f"Motivo: {motivo}\n\n"
                "Depois de registrada, ela não pode ser apagada.",
                icon="warning",
            )
            if not confirmou:
                self.mostrar_mensagem(self.msg_mov, "Saída sem venda cancelada. Nada foi registrado.",
                                      "alerta")
                return

        try:
            novo_estoque = banco.registrar_movimento(
                self.conn, produto_id, tipo, quantidade,
                self.var_usuario.get(), self.var_motivo.get(),
            )
        except banco.ErroDeRegra as erro:
            self.mostrar_erro(self.msg_mov, erro)
            return
        self.var_qtd.set("1")
        self.var_motivo.set("")
        self.atualizar_tudo()

        nomes_curtos = {
            banco.VENDA: "Venda", banco.ENTRADA: "Entrada",
            banco.SAIDA_SEM_VENDA: "Saída sem venda",
        }
        resumo = f"{nomes_curtos[tipo]} registrada: {quantidade} x {nome}."
        if novo_estoque < 0:
            self.mostrar_mensagem(
                self.msg_mov, f"✗  {resumo} ATENÇÃO: estoque ficou NEGATIVO ({novo_estoque}).",
                "erro",
            )
            messagebox.showwarning(
                "Estoque negativo",
                f"Registrado, mas o sistema ficou com estoque {novo_estoque}.\n\n"
                "Isso indica que falta registrar uma entrada ou há algo errado.",
            )
        else:
            self.mostrar_mensagem(self.msg_mov, f"✓  {resumo} Estoque agora: {novo_estoque}.", "ok")

    def registrar_contagem(self):
        produto_id = self.ids_por_nome.get(self.var_produto_cont.get())
        try:
            r = banco.registrar_contagem(
                self.conn, produto_id, self.var_contado.get(), self.var_usuario.get()
            )
        except banco.ErroDeRegra as erro:
            self.mostrar_erro(self.msg_cont, erro)
            return
        self.var_contado.set("")
        self.atualizar_tudo()

        explicacao = f"O sistema esperava {r['esperado']} e você contou {r['contado']}."
        if r["diferenca"] == 0:
            self.mostrar_mensagem(self.msg_cont, f"✓  Tudo certo! {explicacao}", "ok")
        elif r["diferenca"] < 0:
            texto = f"FALTAM {abs(r['diferenca'])} unidade(s). {explicacao}"
            self.mostrar_mensagem(self.msg_cont, f"✗  {texto}", "erro")
            messagebox.showwarning(
                "Divergência",
                f"{texto}\n\nA divergência ficou registrada no relatório.",
            )
        else:
            texto = f"SOBRARAM {r['diferenca']} unidade(s). {explicacao}"
            self.mostrar_mensagem(self.msg_cont, f"⚠  {texto}", "alerta")
            messagebox.showwarning(
                "Divergência",
                f"{texto}\n\nProvavelmente falta registrar uma entrada. "
                "A divergência ficou registrada.",
            )

    # ------------------------------------------------------------------
    # Atualizar o que aparece na tela
    # ------------------------------------------------------------------
    def atualizar_tudo(self):
        produtos = banco.listar_produtos(self.conn)
        self.ids_por_nome = {p["nome"]: p["id"] for p in produtos}
        self.nomes_produtos = list(self.ids_por_nome.keys())
        # Atualiza os dois menus de produtos (respeitando o que está na busca)
        self._filtrar_menu(self.menu_mov)
        self._filtrar_menu(self.menu_cont)

        # Resumo no topo da aba Estoque
        zerados = sum(1 for p in produtos if p["estoque"] <= 0)
        self.lbl_total_produtos.configure(text=str(len(produtos)))
        self.lbl_total_zerados.configure(
            text=str(zerados),
            foreground=estilo.VERMELHO if zerados > 0 else estilo.VERDE,
        )

        # Estoque (zerado ou negativo aparece em vermelho)
        self.tree_estoque.delete(*self.tree_estoque.get_children())
        for i, p in enumerate(produtos):
            self._inserir_linha(
                self.tree_estoque, i,
                (p["nome"], banco.centavos_para_texto(p["preco"]), p["estoque"]),
                vermelho=p["estoque"] <= 0,
            )

        # Divergências (falta aparece em vermelho)
        self.tree_div.delete(*self.tree_div.get_children())
        perda_total = 0
        for i, d in enumerate(banco.divergencias(self.conn)):
            valor = d["diferenca"] * d["preco"]
            if d["diferenca"] < 0:
                perda_total += -valor
            self._inserir_linha(
                self.tree_div, i,
                (
                    banco.formatar_data(d["data_hora"]), d["nome"], d["esperado"],
                    d["contado"], f"{d['diferenca']:+d}", banco.centavos_para_texto(valor),
                    d["usuario"],
                ),
                vermelho=d["diferenca"] < 0,
            )
        self.lbl_total_falta.configure(
            text=f"Valor total do que faltou (ao preço de venda): "
                 f"{banco.centavos_para_texto(perda_total)}",
            foreground=estilo.VERMELHO if perda_total > 0 else estilo.VERDE,
        )

        # Histórico (saída sem venda aparece em vermelho)
        self.tree_hist.delete(*self.tree_hist.get_children())
        for i, m in enumerate(banco.historico(self.conn)):
            self._inserir_linha(
                self.tree_hist, i,
                (
                    banco.formatar_data(m["data_hora"]), m["nome"],
                    banco.NOMES_TIPOS.get(m["tipo"], m["tipo"]),
                    m["quantidade"], m["motivo"] or "", m["usuario"],
                ),
                vermelho=m["tipo"] == banco.SAIDA_SEM_VENDA,
            )


if __name__ == "__main__":
    App().mainloop()

"""
banco.py - Regras do sistema e banco de dados (SQLite).

Este arquivo NÃO tem tela. Ele só guarda e calcula as informações.
A tela (app.py) apenas chama as funções daqui. Separar assim facilita
testar o sistema e trocar a tela depois, sem mexer nas regras.

Ideia central contra desonestidade:
  - Toda movimentação (entrada, venda, saída sem venda) é gravada com
    QUEM fez e QUANDO.
  - Movimentações NÃO podem ser editadas nem apagadas (o próprio banco
    bloqueia isso com "triggers").
  - O estoque nunca é digitado direto: ele é CALCULADO somando as
    movimentações. Assim não dá para "esconder" uma saída.
  - A contagem física compara o que DEVERIA ter com o que TEM de verdade.
    A diferença fica registrada para sempre no relatório de divergências.
"""

import sqlite3
from datetime import datetime
from decimal import Decimal, InvalidOperation

# --- Tipos de movimentação -------------------------------------------------
ENTRADA = "ENTRADA"
VENDA = "VENDA"
SAIDA_SEM_VENDA = "SAIDA_SEM_VENDA"
AJUSTE = "AJUSTE_CONTAGEM"

# Nome bonito para mostrar na tela
NOMES_TIPOS = {
    ENTRADA: "Entrada (chegou mercadoria)",
    VENDA: "Venda",
    SAIDA_SEM_VENDA: "Saída sem venda (perda, quebra, consumo...)",
    AJUSTE: "Ajuste da contagem",
}

# Entrada soma (+1). Venda e saída sem venda subtraem (-1).
SINAL = {ENTRADA: 1, VENDA: -1, SAIDA_SEM_VENDA: -1}


class ErroDeRegra(Exception):
    """Erro com mensagem amigável, pensada para aparecer na tela."""


# --- Conexão e criação das tabelas ----------------------------------------
def conectar(caminho="estoque.db"):
    """Abre o arquivo do banco (cria se não existir) e prepara as tabelas."""
    conn = sqlite3.connect(caminho)
    conn.row_factory = sqlite3.Row  # permite ler colunas pelo nome
    conn.execute("PRAGMA foreign_keys = ON")
    _criar_tabelas(conn)
    return conn


def _criar_tabelas(conn):
    conn.executescript(
        """
        -- Preço guardado em CENTAVOS (inteiro). Evita erros de arredondamento
        -- que acontecem com números decimais (ex.: 0.1 + 0.2).
        CREATE TABLE IF NOT EXISTS produtos (
            id    INTEGER PRIMARY KEY AUTOINCREMENT,
            nome  TEXT NOT NULL UNIQUE COLLATE NOCASE,
            preco INTEGER NOT NULL DEFAULT 0,
            ativo INTEGER NOT NULL DEFAULT 1
        );

        -- 'quantidade' é o que a pessoa digitou (sempre positivo).
        -- 'delta' é o efeito no estoque (+ ou -).
        CREATE TABLE IF NOT EXISTS movimentos (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            produto_id INTEGER NOT NULL REFERENCES produtos(id),
            tipo       TEXT NOT NULL,
            quantidade INTEGER NOT NULL,
            delta      INTEGER NOT NULL,
            motivo     TEXT,
            usuario    TEXT NOT NULL,
            data_hora  TEXT NOT NULL
        );

        -- Cada contagem física: o que o sistema esperava x o que foi contado.
        CREATE TABLE IF NOT EXISTS contagens (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            produto_id INTEGER NOT NULL REFERENCES produtos(id),
            esperado   INTEGER NOT NULL,
            contado    INTEGER NOT NULL,
            diferenca  INTEGER NOT NULL,
            preco      INTEGER NOT NULL,
            usuario    TEXT NOT NULL,
            data_hora  TEXT NOT NULL
        );

        -- Trava: proíbe alterar ou apagar o histórico.
        CREATE TRIGGER IF NOT EXISTS movimentos_sem_update
        BEFORE UPDATE ON movimentos
        BEGIN SELECT RAISE(ABORT, 'Movimentações não podem ser alteradas.'); END;

        CREATE TRIGGER IF NOT EXISTS movimentos_sem_delete
        BEFORE DELETE ON movimentos
        BEGIN SELECT RAISE(ABORT, 'Movimentações não podem ser apagadas.'); END;

        CREATE TRIGGER IF NOT EXISTS contagens_sem_update
        BEFORE UPDATE ON contagens
        BEGIN SELECT RAISE(ABORT, 'Contagens não podem ser alteradas.'); END;

        CREATE TRIGGER IF NOT EXISTS contagens_sem_delete
        BEFORE DELETE ON contagens
        BEGIN SELECT RAISE(ABORT, 'Contagens não podem ser apagadas.'); END;
        """
    )
    conn.commit()


# --- Funções de apoio (pequenas e reutilizáveis) ---------------------------
def _agora():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def formatar_data(texto):
    """'2026-11-19 14:30:00' -> '19/11/2026 14:30'"""
    return datetime.strptime(texto, "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y %H:%M")


def reais_para_centavos(texto):
    """Aceita '4,50' ou '4.50' e devolve 450."""
    texto = str(texto).strip().replace("R$", "").replace(",", ".")
    if texto == "":
        return 0
    try:
        valor = Decimal(texto)
    except InvalidOperation:
        raise ErroDeRegra("Preço inválido. Use um formato como 4,50.")
    if valor < 0:
        raise ErroDeRegra("O preço não pode ser negativo.")
    return int(round(valor * 100))


def centavos_para_texto(centavos):
    """450 -> 'R$ 4,50'"""
    sinal = "-" if centavos < 0 else ""
    centavos = abs(centavos)
    return f"{sinal}R$ {centavos // 100},{centavos % 100:02d}"


def _validar_quantidade(valor, permitir_zero=False):
    try:
        numero = int(str(valor).strip())
    except (ValueError, TypeError):
        raise ErroDeRegra("Digite a quantidade com número inteiro (ex.: 6).")
    minimo = 0 if permitir_zero else 1
    if numero < minimo:
        raise ErroDeRegra(
            "A quantidade não pode ser negativa."
            if permitir_zero
            else "A quantidade precisa ser maior que zero."
        )
    return numero


def _exigir_usuario(usuario):
    usuario = (usuario or "").strip()
    if not usuario:
        raise ErroDeRegra("Informe quem está usando o sistema (campo no topo).")
    return usuario


def _buscar_produto(conn, produto_id):
    linha = conn.execute(
        "SELECT * FROM produtos WHERE id = ? AND ativo = 1", (produto_id,)
    ).fetchone()
    if linha is None:
        raise ErroDeRegra("Escolha um produto da lista.")
    return linha


def _inserir_movimento(conn, produto_id, tipo, quantidade, delta, motivo, usuario, data_hora):
    # Não faz commit aqui: quem chama decide (assim várias gravações
    # podem acontecer juntas, ou nenhuma).
    conn.execute(
        """INSERT INTO movimentos
           (produto_id, tipo, quantidade, delta, motivo, usuario, data_hora)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (produto_id, tipo, quantidade, delta, motivo, usuario, data_hora),
    )


# --- Produtos e estoque ----------------------------------------------------
def cadastrar_produto(conn, nome, preco_texto, usuario, estoque_inicial=0):
    nome = (nome or "").strip()
    if not nome:
        raise ErroDeRegra("Digite o nome do produto.")
    usuario = _exigir_usuario(usuario)
    preco = reais_para_centavos(preco_texto)
    inicial = _validar_quantidade(estoque_inicial or 0, permitir_zero=True)

    try:
        with conn:  # 'with conn' = tudo ou nada (commit no fim, rollback se der erro)
            cursor = conn.execute(
                "INSERT INTO produtos (nome, preco) VALUES (?, ?)", (nome, preco)
            )
            produto_id = cursor.lastrowid
            if inicial > 0:
                _inserir_movimento(
                    conn, produto_id, ENTRADA, inicial, inicial,
                    "Estoque inicial", usuario, _agora(),
                )
    except sqlite3.IntegrityError:
        raise ErroDeRegra("Já existe um produto com esse nome.")
    return produto_id


def estoque_atual(conn, produto_id):
    """O estoque é a SOMA de todas as movimentações do produto."""
    linha = conn.execute(
        "SELECT COALESCE(SUM(delta), 0) AS total FROM movimentos WHERE produto_id = ?",
        (produto_id,),
    ).fetchone()
    return int(linha["total"])


def listar_produtos(conn):
    return conn.execute(
        """SELECT p.id, p.nome, p.preco, COALESCE(SUM(m.delta), 0) AS estoque
           FROM produtos p
           LEFT JOIN movimentos m ON m.produto_id = p.id
           WHERE p.ativo = 1
           GROUP BY p.id
           ORDER BY p.nome"""
    ).fetchall()


# --- Movimentações ---------------------------------------------------------
def registrar_movimento(conn, produto_id, tipo, quantidade, usuario, motivo=""):
    """Registra entrada, venda ou saída sem venda. Devolve o novo estoque."""
    if tipo not in SINAL:
        raise ErroDeRegra("Tipo de movimentação inválido.")
    usuario = _exigir_usuario(usuario)
    quantidade = _validar_quantidade(quantidade)
    motivo = (motivo or "").strip()
    if tipo == SAIDA_SEM_VENDA and not motivo:
        raise ErroDeRegra("Saída sem venda exige um motivo (ex.: quebrou, vencido, consumo).")
    _buscar_produto(conn, produto_id)

    with conn:
        _inserir_movimento(
            conn, produto_id, tipo, quantidade,
            SINAL[tipo] * quantidade, motivo, usuario, _agora(),
        )
    return estoque_atual(conn, produto_id)


# --- Contagem e divergência ------------------------------------------------
def registrar_contagem(conn, produto_id, contado, usuario):
    """
    Compara o que foi CONTADO na prateleira com o que o sistema ESPERAVA.
    Se houver diferença, grava a divergência (para sempre) e cria um ajuste
    para o estoque do sistema voltar a bater com a realidade.
    """
    usuario = _exigir_usuario(usuario)
    contado = _validar_quantidade(contado, permitir_zero=True)
    produto = _buscar_produto(conn, produto_id)
    esperado = estoque_atual(conn, produto_id)
    diferenca = contado - esperado
    agora = _agora()

    with conn:
        conn.execute(
            """INSERT INTO contagens
               (produto_id, esperado, contado, diferenca, preco, usuario, data_hora)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (produto_id, esperado, contado, diferenca, produto["preco"], usuario, agora),
        )
        if diferenca != 0:
            _inserir_movimento(
                conn, produto_id, AJUSTE, abs(diferenca), diferenca,
                "Ajuste automático pela contagem", usuario, agora,
            )
    return {"esperado": esperado, "contado": contado, "diferenca": diferenca}


def divergencias(conn):
    """Só as contagens em que faltou ou sobrou produto (mais recentes primeiro)."""
    return conn.execute(
        """SELECT c.id, c.data_hora, p.nome, c.esperado, c.contado,
                  c.diferenca, c.preco, c.usuario
           FROM contagens c
           JOIN produtos p ON p.id = c.produto_id
           WHERE c.diferenca != 0
           ORDER BY c.id DESC"""
    ).fetchall()


def historico(conn, limite=300):
    """Últimas movimentações (mais recentes primeiro)."""
    return conn.execute(
        """SELECT m.id, m.data_hora, p.nome, m.tipo, m.quantidade, m.motivo, m.usuario
           FROM movimentos m
           JOIN produtos p ON p.id = m.produto_id
           ORDER BY m.id DESC
           LIMIT ?""",
        (limite,),
    ).fetchall()

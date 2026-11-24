# Controle de Estoque para Conveniência

Programa simples para controlar a saída de bebidas e produtos, feito em **Python + SQLite + Tkinter**.
Roda no Windows, sem internet e sem instalar nada além do Python.

## O problema que ele resolve

Produtos saindo sem venda registrada. O sistema não impede furto sozinho, mas torna a diferença
**visível e rastreável**:

- Toda movimentação guarda **quem** fez e **quando**.
- O histórico **não pode ser editado nem apagado** (o banco bloqueia).
- O estoque nunca é digitado: ele é **calculado** somando as movimentações.
- A **contagem física** compara o que deveria ter com o que realmente tem, e a diferença fica
  registrada para sempre no relatório de divergências.

## Como usar

1. Instale o Python 3.10 ou mais novo em <https://www.python.org/downloads/>
   (no instalador, marque **"Add Python to PATH"**).
2. Baixe/clone este projeto.
3. Abra a pasta, e no terminal rode:

   ```
   python app.py
   ```

O arquivo `estoque.db` (os dados) é criado sozinho na mesma pasta, na primeira vez.

### Rotina sugerida na loja

- Antes de tudo: digite seu nome no campo **Quem está usando** (faixa azul no topo).
- Ao vender: aba **Registrar movimento** → escolha o produto, a quantidade e clique no botão azul **VENDA**.
- Ao chegar mercadoria: botão verde **ENTRADA**.
- Quebrou, venceu, consumo próprio: botão laranja **SAÍDA SEM VENDA** (o motivo é obrigatório
  e o programa pede confirmação antes de gravar).
- Para achar um produto rápido, digite parte do nome no campo **Buscar** (não precisa de acento).
  Ao escolher o produto na aba Registrar, o estoque atual aparece ao lado.
- Mensagens em **verde** = deu certo. Em **vermelho** = algo errado (erro, falta, estoque zerado ou negativo).
- Uma vez por dia ou por semana: aba **Contagem**, contando as unidades reais.
- O dono olha a aba **Relatórios**.

## Estrutura do projeto

| Arquivo | Para que serve |
|---|---|
| `banco.py` | Banco de dados e regras (sem tela). É o coração do sistema. |
| `app.py` | Tela (Tkinter). Só chama as funções de `banco.py`. |
| `estilo.py` | Cores, fontes e aparência dos botões/tabelas (ttk, tema "clam"). Para trocar uma cor, mexa aqui. |
| `test_banco.py` | Testes automáticos das regras. |
| `.gitignore` | Evita subir o `estoque.db` (dados reais) para o GitHub. |

## Testes

```
python -m unittest -v
```

## Backup

Copie o arquivo `estoque.db` para um pendrive uma vez por semana. Ele contém **todos** os dados.

## Ideias para as próximas versões

- [ ] Senha: uma para quem registra e outra para o dono ver os relatórios
- [ ] Gerar o `.exe` com PyInstaller (atalho na área de trabalho)
- [ ] Exportar relatório de divergências para Excel/PDF
- [ ] Alerta de estoque mínimo
- [ ] Backup automático do `estoque.db`
- [ ] Desativar produto (hoje não há botão; a coluna `ativo` já existe no banco)

## Limitações conhecidas (versão 0.1)

- Não tem senha ainda: qualquer pessoa pode digitar qualquer nome em "Quem está usando".
- O nome do usuário é digitado à mão (não é um login).
- Quem tiver acesso ao computador pode apagar o arquivo `estoque.db` inteiro: por isso o backup.

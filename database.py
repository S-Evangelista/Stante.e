import sqlite3

BANCO = "livros.db"


def conectar():
    conexao = sqlite3.connect(BANCO)
    conexao.row_factory = sqlite3.Row
    return conexao


def criar_tabela():
    with conectar() as conexao:
        conexao.execute("""
            CREATE TABLE IF NOT EXISTS livros (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                autor TEXT NOT NULL,
                status TEXT NOT NULL,
                categoria TEXT NOT NULL,
                eh_colecao INTEGER NOT NULL DEFAULT 0,
                nome_colecao TEXT,
                volume TEXT,
                nota REAL,
                avaliacao TEXT
            )
        """)
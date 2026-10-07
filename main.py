import os
import random
import uuid

from flask import (
    Flask,
    abort,
    redirect,
    render_template,
    request,
    url_for
)
from werkzeug.utils import secure_filename

from database import conectar, criar_tabela

app = Flask(__name__)

CATEGORIAS = [    "Romance",
    "Suspense",
    "Fantasia",
    "Autoajuda",
    "Terror",
    "Ficção Científica"]

STATUS = ["Não iniciado", "Lendo", "Lido"]

PASTA_UPLOADS = os.path.join("static", "uploads")
EXTENSOES_PERMITIDAS = {"png", "jpg", "jpeg", "gif", "webp"}

os.makedirs(PASTA_UPLOADS, exist_ok=True)


def garantir_coluna_capa():
    """Adiciona a coluna 'capa' na tabela livros, caso ainda não exista."""
    with conectar() as conexao:
        try:
            conexao.execute("ALTER TABLE livros ADD COLUMN capa TEXT")
        except Exception:
            # A coluna já existe — não faz nada.
            pass


def extensao_permitida(nome_arquivo):
    return (
        "." in nome_arquivo
        and nome_arquivo.rsplit(".", 1)[1].lower() in EXTENSOES_PERMITIDAS
    )


def salvar_capa(arquivo):
    """Salva a imagem enviada e retorna o nome do arquivo salvo, ou None."""
    if not arquivo or arquivo.filename == "":
        return None

    if not extensao_permitida(arquivo.filename):
        return None

    extensao = secure_filename(arquivo.filename).rsplit(".", 1)[1].lower()
    nome_unico = f"{uuid.uuid4().hex}.{extensao}"
    arquivo.save(os.path.join(PASTA_UPLOADS, nome_unico))

    return nome_unico


def obter_livro(livro_id):
    with conectar() as conexao:
        return conexao.execute(
            "SELECT * FROM livros WHERE id = ?",
            (livro_id,)
        ).fetchone()


@app.route("/")
def index():
    busca = request.args.get("busca", "").strip()
    categoria = request.args.get("categoria", "")
    status = request.args.get("status", "")

    consulta = "SELECT * FROM livros WHERE 1=1"
    parametros = []

    if busca:
        consulta += " AND (nome LIKE ? OR autor LIKE ?)"
        termo = f"%{busca}%"
        parametros.extend([termo, termo])

    if categoria in CATEGORIAS:
        consulta += " AND (',' || categoria || ',') LIKE ?"
        parametros.append(f"%,{categoria},%")

    if status in STATUS:
        consulta += " AND status = ?"
        parametros.append(status)

    consulta += " ORDER BY nome COLLATE NOCASE"

    with conectar() as conexao:
        livros = conexao.execute(consulta, parametros).fetchall()

    return render_template(
        'index.html',
        livros=livros,
        busca=busca,
        categoria_selecionada=categoria,
        status_selecionado=status,
        categorias=CATEGORIAS,
        status_opcoes=STATUS
    )

@app.route("/livro/adicionar", methods=["GET", "POST"])
def adicionar():
    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        autor = request.form.get("autor", "").strip()
        categorias_selecionadas = [
            c for c in request.form.getlist("categorias") if c in CATEGORIAS
        ]
        categoria = ",".join(categorias_selecionadas)
        status = request.form.get("status", "")
        eh_colecao = request.form.get("eh_colecao") == "sim"

        nome_colecao = (
            request.form.get("nome_colecao", "").strip()
            if eh_colecao else None
        )
        volume = (
            request.form.get("volume", "").strip()
            if eh_colecao else None
        )

        nota_texto = request.form.get("nota", "").strip()
        avaliacao = request.form.get("avaliacao", "").strip()
        nota = None

        if status == "Lido" and nota_texto:
            try:
                nota = float(nota_texto)
                if nota < 1 or nota > 5:
                    nota = None
            except ValueError:
                nota = None

        if status != "Lido":
            avaliacao = None

        capa = salvar_capa(request.files.get("capa"))

        dados_validos = (
            nome
            and autor
            and categorias_selecionadas
            and status in STATUS
            and (not eh_colecao or (nome_colecao and volume))
        )

        if dados_validos:
            with conectar() as conexao:
                conexao.execute("""
                    INSERT INTO livros (
                        nome, autor, status, categoria,
                        eh_colecao, nome_colecao, volume,
                        nota, avaliacao, capa
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    nome,
                    autor,
                    status,
                    categoria,
                    int(eh_colecao),
                    nome_colecao,
                    volume,
                    nota,
                    avaliacao or None,
                    capa
                ))

            return redirect(url_for("index"))

    return render_template(
        "adicionar.html",
        categorias=CATEGORIAS,
        status_opcoes=STATUS
    )

@app.route("/livro/<int:livro_id>")
def detalhes(livro_id):
    livro = obter_livro(livro_id)

    if livro is None:
        abort(404)

    return render_template("detalhes.html", livro=livro)


@app.route("/livro/<int:livro_id>/editar", methods=["GET", "POST"])
def editar(livro_id):
    livro = obter_livro(livro_id)

    if livro is None:
        abort(404)

    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        autor = request.form.get("autor", "").strip()
        categorias_selecionadas = [
            c for c in request.form.getlist("categorias") if c in CATEGORIAS
        ]
        categoria = ",".join(categorias_selecionadas)
        status = request.form.get("status", "")
        eh_colecao = request.form.get("eh_colecao") == "sim"

        nome_colecao = (
            request.form.get("nome_colecao", "").strip()
            if eh_colecao else None
        )
        volume = (
            request.form.get("volume", "").strip()
            if eh_colecao else None
        )

        nota_texto = request.form.get("nota", "").strip()
        avaliacao = request.form.get("avaliacao", "").strip()
        nota = None

        if status == "Lido" and nota_texto:
            try:
                nota = float(nota_texto)
                if nota < 1 or nota > 5:
                    nota = None
            except ValueError:
                nota = None

        if status != "Lido":
            avaliacao = None

        nova_capa = salvar_capa(request.files.get("capa"))
        capa = nova_capa if nova_capa else livro["capa"]

        dados_validos = (
            nome
            and autor
            and categorias_selecionadas
            and status in STATUS
            and (not eh_colecao or (nome_colecao and volume))
        )

        if dados_validos:
            with conectar() as conexao:
                conexao.execute("""
                    UPDATE livros
                    SET nome = ?,
                        autor = ?,
                        categoria = ?,
                        status = ?,
                        eh_colecao = ?,
                        nome_colecao = ?,
                        volume = ?,
                        nota = ?,
                        avaliacao = ?,
                        capa = ?
                    WHERE id = ?
                """, (
                    nome,
                    autor,
                    categoria,
                    status,
                    int(eh_colecao),
                    nome_colecao,
                    volume,
                    nota,
                    avaliacao or None,
                    capa,
                    livro_id
                ))

            return redirect(url_for("detalhes", livro_id=livro_id))

        # Mantém os dados digitados caso o formulário seja inválido.
        livro = {
            "id": livro_id,
            "nome": nome,
            "autor": autor,
            "categoria": categoria,
            "status": status,
            "eh_colecao": int(eh_colecao),
            "nome_colecao": nome_colecao,
            "volume": volume,
            "nota": nota,
            "avaliacao": avaliacao,
            "capa": capa
        }

    return render_template(
        "editar.html",
        livro=livro,
        categorias=CATEGORIAS,
        status_opcoes=STATUS
    )

@app.route("/livro/<int:livro_id>/excluir", methods=["POST"])
def excluir(livro_id):
    with conectar() as conexao:
        conexao.execute(
            "DELETE FROM livros WHERE id = ?",
            (livro_id,)
        )

    return redirect(url_for("index"))


@app.route("/proxima-leitura")
def proxima_leitura():
    with conectar() as conexao:
        livros = conexao.execute(
            "SELECT * FROM livros ORDER BY id"
        ).fetchall()

    disponiveis = [
        livro for livro in livros
        if livro["status"] in ("Não iniciado", "Lendo")
    ]

    if not disponiveis:
        return render_template(
            "sugestao.html",
            livro=None,
            motivo=(
                "Não há livros disponíveis para sugerir. "
                "Cadastre um livro ou altere o status de um livro existente."
            )
        )

    # Prioriza o próximo volume de uma coleção que já tenha um volume lido.
    maiores_volumes_lidos = {}

    for livro in livros:
        if (
            livro["eh_colecao"]
            and livro["status"] == "Lido"
            and livro["nome_colecao"]
            and livro["volume"]
        ):
            try:
                numero_volume = int(livro["volume"])
            except (TypeError, ValueError):
                continue

            nome_colecao = livro["nome_colecao"].strip().casefold()
            maiores_volumes_lidos[nome_colecao] = max(
                numero_volume,
                maiores_volumes_lidos.get(nome_colecao, 0)
            )

    proximos_volumes = []

    for livro in disponiveis:
        if (
            livro["eh_colecao"]
            and livro["nome_colecao"]
            and livro["volume"]
        ):
            try:
                numero_volume = int(livro["volume"])
            except (TypeError, ValueError):
                continue

            nome_colecao = livro["nome_colecao"].strip().casefold()

            if maiores_volumes_lidos.get(nome_colecao) == numero_volume - 1:
                proximos_volumes.append(livro)

    if proximos_volumes:
        escolhido = random.choice(proximos_volumes)
        motivo = "Este livro é o próximo volume de uma coleção que você já começou."

        return render_template(
            "sugestao.html",
            livro=escolhido,
            motivo=motivo
        )

    # Calcula as médias de notas por categoria e autor.
    notas_por_categoria = {}
    notas_por_autor = {}

    for livro in livros:
        if livro["status"] == "Lido" and livro["nota"] is not None:
            notas_por_categoria.setdefault(
                livro["categoria"], []
            ).append(float(livro["nota"]))

            notas_por_autor.setdefault(
                livro["autor"], []
            ).append(float(livro["nota"]))

    medias_categorias = {
        chave: sum(valores) / len(valores)
        for chave, valores in notas_por_categoria.items()
    }

    medias_autores = {
        chave: sum(valores) / len(valores)
        for chave, valores in notas_por_autor.items()
    }

    def peso_do_livro(livro):
        media_categoria = medias_categorias.get(livro["categoria"])
        media_autor = medias_autores.get(livro["autor"])

        peso_categoria = (
            media_categoria / 5 if media_categoria is not None else 0.5
        )
        peso_autor = (
            media_autor / 5 if media_autor is not None else 0.5
        )

        return max(0.05, peso_categoria * 0.6 + peso_autor * 0.4)

    escolhido = random.choices(
        disponiveis,
        weights=[peso_do_livro(livro) for livro in disponiveis],
        k=1
    )[0]

    motivos = []

    if escolhido["categoria"] in medias_categorias:
        media = medias_categorias[escolhido["categoria"]]
        motivos.append(
            f"a categoria {escolhido['categoria']} tem média {media:.1f}/5"
        )

    if escolhido["autor"] in medias_autores:
        media = medias_autores[escolhido["autor"]]
        motivos.append(
            f"os livros de {escolhido['autor']} têm média {media:.1f}/5"
        )

    if motivos:
        motivo = "Sugestão baseada nas suas avaliações: " + " e ".join(motivos) + "."
    else:
        motivo = (
            "Ainda não há avaliações suficientes para identificar suas "
            "preferências. O livro foi escolhido entre os disponíveis."
        )

    return render_template(
        "sugestao.html",
        livro=escolhido,
        motivo=motivo
    )


criar_tabela()
garantir_coluna_capa()

@app.route("/estimativa", methods=["GET", "POST"])
def estimativa():
    resultado = None
    erro = None

    if request.method == "POST":
        tempo_texto = request.form.get("tempo_10_paginas", "").strip()
        paginas_texto = request.form.get("numero_paginas", "").strip()

        try:
            tempo_10_paginas = float(tempo_texto.replace(",", "."))
            numero_paginas = int(paginas_texto)

            if tempo_10_paginas <= 0 or numero_paginas <= 0:
                raise ValueError

            # Tempo médio por página, multiplicado pelo total de páginas do livro
            tempo_por_pagina = tempo_10_paginas / 10
            tempo_total_minutos = tempo_por_pagina * numero_paginas

            horas = int(tempo_total_minutos // 60)
            minutos = int(round(tempo_total_minutos % 60))

            if minutos == 60:
                horas += 1
                minutos = 0

            resultado = {
                "horas": horas,
                "minutos": minutos,
                "tempo_total_minutos": round(tempo_total_minutos, 1),
                "numero_paginas": numero_paginas,
                "tempo_10_paginas": tempo_10_paginas
            }
        except ValueError:
            erro = "Preencha os campos com valores numéricos válidos e maiores que zero."

    return render_template("estimativa.html", resultado=resultado, erro=erro)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8081, debug=True)
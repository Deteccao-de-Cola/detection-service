from flask import request
from flask_smorest import Blueprint
from src.schemas import ImportacaoResponseSchema
from src.services.importacao_service import importar_csvs, AREAS_VALIDAS

importacao = Blueprint("importacao", __name__, description="Importação de provas via CSV")

PERIODOS_VALIDOS = {"matutino", "vespertino"}
CAMPOS_AREA = {
    'arquivo_cod': 'COD',
    'arquivo_cn':  'CN',
    'arquivo_hum': 'HUM',
    'arquivo_mat': 'MAT',
}


@importacao.route('/importar', methods=['POST'])
@importacao.response(200, ImportacaoResponseSchema)
def importar():

    titulo  = (request.form.get('titulo') or '').strip()
    periodo = (request.form.get('periodo') or '').strip().lower()
    semestre = (request.form.get('semestre') or '').strip()
    grupo   = (request.form.get('grupo') or '').strip().upper()

    try:
        turma_ano = int(request.form.get('turma_ano', 0))
    except ValueError:
        return {"mensagem": "Campo 'turma_ano' deve ser inteiro"}, 400

    if not titulo:
        return {"mensagem": "Campo 'titulo' obrigatório"}, 400
    if periodo not in PERIODOS_VALIDOS:
        return {"mensagem": f"'periodo' inválido. Use: {', '.join(PERIODOS_VALIDOS)}"}, 400
    if not semestre:
        return {"mensagem": "Campo 'semestre' obrigatório"}, 400
    if turma_ano not in (1, 2, 3):
        return {"mensagem": "Campo 'turma_ano' deve ser 1, 2 ou 3"}, 400

    arquivos = []
    for campo, area in CAMPOS_AREA.items():
        arquivo = request.files.get(campo)
        if arquivo:
            arquivos.append({
                'conteudo':     arquivo.read(),
                'nome_arquivo': arquivo.filename or f'{campo}.csv',
                'area':         area,
            })

    if not arquivos:
        return {"mensagem": "Envie ao menos um arquivo CSV (arquivo_cod, arquivo_cn, arquivo_hum ou arquivo_mat)"}, 400

    resultado = importar_csvs(
        arquivos=arquivos,
        titulo=titulo,
        periodo=periodo,
        semestre=semestre,
        turma_ano=turma_ano,
        grupo=grupo,
    )

    return resultado

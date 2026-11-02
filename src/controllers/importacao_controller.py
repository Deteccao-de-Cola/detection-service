from flask import request
from flask_smorest import Blueprint
from src.schemas import ImportacaoResponseSchema
from src.services.importacao_service import importar_csvs, AREAS_VALIDAS, PlanilhaInvalida

importacao = Blueprint("importacao", __name__, description="Importação de provas via CSV")

PERIODOS_VALIDOS  = {"matutino", "vespertino"}
BIMESTRES_VALIDOS = {"1B", "2B"}
LETRAS_TURMA      = set("ABCDEFGHIJKLMNOPQRSTUVWX")
CAMPOS_AREA = {
    'arquivo_cod': 'COD',
    'arquivo_cn':  'CN',
    'arquivo_hum': 'HUM',
    'arquivo_mat': 'MAT',
}


@importacao.route('/importar', methods=['POST'])
@importacao.response(200, ImportacaoResponseSchema)
def importar():

    periodo  = (request.form.get('periodo') or '').strip().lower()
    bimestre = (request.form.get('bimestre') or '').strip().upper()
    turmas   = (request.form.get('turmas') or '').strip().upper()

    try:
        ano_aplicacao = int(request.form.get('anoAplicacao', 0))
        serie         = int(request.form.get('serie', 0))
    except ValueError:
        return {"mensagem": "Campos 'anoAplicacao' e 'serie' devem ser inteiros"}, 400

    if not 2000 <= ano_aplicacao <= 2100:
        return {"mensagem": "Campo 'anoAplicacao' deve estar entre 2000 e 2100"}, 400
    if serie not in (1, 2, 3):
        return {"mensagem": "Campo 'serie' deve ser 1, 2 ou 3"}, 400
    if periodo not in PERIODOS_VALIDOS:
        return {"mensagem": f"'periodo' inválido. Use: {', '.join(PERIODOS_VALIDOS)}"}, 400
    if bimestre not in BIMESTRES_VALIDOS:
        return {"mensagem": "Campo 'bimestre' deve ser 1B ou 2B"}, 400
    if not turmas or not set(turmas) <= LETRAS_TURMA or len(set(turmas)) != len(turmas):
        return {"mensagem": "Campo 'turmas' deve ter letras de A a X, sem repetir (ex.: IJKLMN)"}, 400

    arquivos = []
    for campo, area in CAMPOS_AREA.items():
        arquivo  = request.files.get(campo)
        gabarito = request.files.get(f'gabarito_{area.lower()}')
        if gabarito and not arquivo:
            return {"mensagem": f"Gabarito de {area} enviado sem o arquivo de respostas da área"}, 400
        if arquivo:
            item = {
                'conteudo':     arquivo.read(),
                'nome_arquivo': arquivo.filename or f'{campo}.csv',
                'area':         area,
            }
            if gabarito:
                item['gabarito']      = gabarito.read()
                item['nome_gabarito'] = gabarito.filename or f'gabarito_{area.lower()}.csv'
            arquivos.append(item)

    if not arquivos:
        return {"mensagem": "Envie ao menos um arquivo CSV (arquivo_cod, arquivo_cn, arquivo_hum ou arquivo_mat)"}, 400

    try:
        resultado = importar_csvs(
            arquivos=arquivos,
            ano_aplicacao=ano_aplicacao,
            serie=serie,
            periodo=periodo,
            bimestre=bimestre,
            turmas=turmas,
        )
    except PlanilhaInvalida as e:
        return {"mensagem": str(e)}, 400

    return resultado

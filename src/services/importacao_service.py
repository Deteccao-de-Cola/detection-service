import re
import io
import csv
import pandas as pd
from faker import Faker
from sqlalchemy import create_engine, text

fake = Faker('pt_BR')

MYSQL_HOST = 'db-tcc-cola'
MYSQL_USER = 'user'
MYSQL_PASSWORD = 'mysqlPass'
MYSQL_DB = 'tccdb'
MYSQL_PORT = 3306

AREAS_VALIDAS = ('COD', 'CN', 'HUM', 'MAT')
SEPARADORES_CSV = (',', ';', '\t')


class PlanilhaInvalida(ValueError):
    pass

def _engine():
    return create_engine(
        f'mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}?charset=utf8mb4',
        hide_parameters=True,
    )

def _parse_pontuacao(valor) -> int | None:
    texto = str(valor).split('/')[0].strip()
    try:
        return int(float(texto))
    except (ValueError, OverflowError):
        return None


def _parse_grupo(nome_arquivo: str) -> str:
    match = re.search(r'_\d([A-Z]+)_', nome_arquivo.upper())
    return match.group(1) if match else ''


def _parse_user_id(valor) -> int | None:
    if pd.isna(valor):
        return None
    try:
        return int(float(valor))
    except (TypeError, ValueError):
        match = re.search(r'_(\d+)@', str(valor))
        return int(match.group(1)) if match else None


def _achar_coluna(nomes: list[str], termos: list[str], padrao: int) -> int:
    for indice, nome in enumerate(nomes):
        for termo in termos:
            if nome.startswith(termo):
                return indice
    return padrao


def _detectar_separador(texto: str) -> str:

    melhor, melhor_score = ',', -1.0
    for sep in SEPARADORES_CSV:
        contagens = [len(linha) for linha in csv.reader(io.StringIO(texto), delimiter=sep) if linha]
        cabecalho = contagens[0] if contagens else 0
        if cabecalho < 2 or max(contagens) > cabecalho:
            continue
        score = contagens.count(cabecalho) / len(contagens)
        if score > melhor_score:
            melhor, melhor_score = sep, score
    return melhor


def _ler_csv(conteudo: bytes) -> pd.DataFrame:
    try:
        texto = conteudo.decode('utf-8-sig')
    except UnicodeDecodeError:
        texto = conteudo.decode('cp1252')
    return pd.read_csv(io.StringIO(texto), sep=_detectar_separador(texto))


def _processar_csv_bytes(
    conteudo: bytes,
    nome_arquivo: str,
    area: str,
    periodo: str,
    semestre: str,
    turma_ano: int,
    grupo: str,
) -> list[dict]:
    """Lê um CSV ou XLSX em memória e retorna as linhas prontas para INSERT."""
    try:
        if nome_arquivo.lower().endswith(('.xlsx', '.xlsm')):
            df = pd.read_excel(io.BytesIO(conteudo))
        else:
            df = _ler_csv(conteudo)
    except (pd.errors.ParserError, pd.errors.EmptyDataError, UnicodeDecodeError) as e:
        raise PlanilhaInvalida(f"Não foi possível ler '{nome_arquivo}': {str(e).strip()}") from e

    if str(df.iloc[0, 0]).strip().upper() == "RESPOSTA":
        df = df.iloc[1:].reset_index(drop=True)

    #para encontrar a coluna do emal
    nomes = [str(c).strip().upper().replace('-', '') for c in df.columns]

    col_data  = _achar_coluna(nomes, ['CARIMBO'], padrao=0)
    col_pont  = _achar_coluna(nomes, ['PONTUA'], padrao=1)
    col_turma = _achar_coluna(nomes, ['SÉRIE', 'TURMA'], padrao=2)

    if 'ID' in nomes:
        col_id = nomes.index('ID')
    else:
        col_id = len(nomes) - 1
        for indice, nome in enumerate(nomes):
            if 'EMAIL' in nome:
                col_id = indice
                break
    user_ids = df.iloc[:, col_id].apply(_parse_user_id).values

    datas    = df.iloc[:, col_data]
    dayfirst = bool(datas.astype(str).str.match(r'\s*\d{1,2}/\d{1,2}/\d{4}').any())

    pontuacao_map = dict(zip(user_ids, df.iloc[:, col_pont].apply(_parse_pontuacao).values))
    momento_map   = dict(zip(user_ids, pd.to_datetime(datas, errors='coerce', dayfirst=dayfirst).values))

    manter    = [i for i in range(df.shape[1]) if i not in {col_data, col_pont, col_turma, col_id}]
    respostas = df.iloc[:, manter].dropna(axis=1, how='all')
    respostas.index = user_ids

    df_melted = respostas.stack().dropna().reset_index()
    df_melted.columns = ["user_id", "questao", "resposta"]
    df_melted = df_melted[df_melted["user_id"].notna()]
    df_melted["resposta"]        = df_melted["resposta"].astype(str).str.strip().str.upper()
    df_melted["momento_entrega"] = df_melted["user_id"].apply(lambda uid: momento_map.get(uid))
    df_melted["pontuacao"]       = df_melted["user_id"].apply(lambda uid: pontuacao_map.get(uid))

    return [
        {
            "periodo":          periodo,
            "semestre":         semestre,
            "turma_ano":        turma_ano,
            "areaConhecimento": area,
            "resposta":         row["resposta"],
            "user_id":          int(row["user_id"]),
            "questao":          str(row["questao"]),
            "grupo":            grupo,
            "momento_entrega":  row["momento_entrega"].strftime("%Y-%m-%d %H:%M:%S") if pd.notna(row["momento_entrega"]) else None,
            "pontuacao":        int(row["pontuacao"]) if pd.notna(row["pontuacao"]) else None,
        }
        for _, row in df_melted.iterrows()
    ]


def importar_csvs(
    arquivos: list[dict],
    titulo: str,
    periodo: str,
    semestre: str,
    turma_ano: int,
    grupo: str = '',
) -> dict:

    engine  = _engine()
    periodo = periodo.lower().strip()
    semestre = semestre.upper().strip()

    _create_staging(engine)

    try:
        if not grupo:
            for arq in arquivos:
                if arq['area'].upper() == 'COD':
                    grupo = _parse_grupo(arq['nome_arquivo'])
                    break

        if not grupo and arquivos:
            grupo = _parse_grupo(arquivos[0]['nome_arquivo'])

        total_linhas = 0
        for arq in arquivos:
            area = arq['area'].upper()
            rows = _processar_csv_bytes(
                conteudo=arq['conteudo'],
                nome_arquivo=arq['nome_arquivo'],
                area=area,
                periodo=periodo,
                semestre=semestre,
                turma_ano=turma_ano,
                grupo=grupo,
            )
            if not rows:
                continue
            with engine.begin() as conn:
                conn.execute(text("""
                    INSERT INTO migration
                        (periodo, semestre, turma_ano, areaConhecimento, resposta,
                         user_id, questao, grupo, momento_entrega, pontuacao)
                    VALUES
                        (:periodo, :semestre, :turma_ano, :areaConhecimento, :resposta,
                         :user_id, :questao, :grupo, :momento_entrega, :pontuacao)
                """), rows)
            total_linhas += len(rows)

        if total_linhas == 0:
            return {"linhas_importadas": 0, "mensagem": "Nenhum arquivo com dados válidos"}

        _build_clusters(engine)
        _create_users(engine)
        _create_contests(engine)
        _create_aplicacoes(engine)
        _create_questions(engine)
        _create_alternatives(engine)
        _contests_questions(engine)
        _users_answers(engine, periodo, semestre, turma_ano, grupo)
        _create_realiza_prova(engine)
        _update_pontuacoes(engine)

        # Renomeia a prova para o título customizado (após o pipeline que usa o título gerado)
        titulo_gerado = f"{turma_ano} ano - {periodo} - {semestre} - {grupo}"
        _rename_contest(engine, titulo_gerado, titulo)

        return {"linhas_importadas": total_linhas, "mensagem": "Importação concluída com sucesso"}
    finally:
        _drop_staging(engine)
        engine.dispose()


def importar_csv(
    conteudo: bytes,
    nome_arquivo: str,
    periodo: str,
    semestre: str,
    turma_ano: int,
    area: str,
    grupo: str | None = None,
) -> dict:
    grupo_efetivo = grupo or _parse_grupo(nome_arquivo)
    titulo_padrao = f"{turma_ano} ano - {periodo.lower()} - {semestre.upper()} - {grupo_efetivo}"
    return importar_csvs(
        arquivos=[{'conteudo': conteudo, 'nome_arquivo': nome_arquivo, 'area': area}],
        titulo=titulo_padrao,
        periodo=periodo,
        semestre=semestre,
        turma_ano=turma_ano,
        grupo=grupo_efetivo,
    )


# ──----------------------------- helpers de pipeline ──-----------------------------

def _create_staging(engine):
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS migration"))
        conn.execute(text("""
            CREATE TABLE migration (
                id               INT AUTO_INCREMENT PRIMARY KEY,
                user_id          INT NOT NULL,
                periodo          VARCHAR(20) NOT NULL,
                semestre         VARCHAR(10) NOT NULL,
                turma_ano        INT NOT NULL,
                areaConhecimento VARCHAR(10) NOT NULL,
                resposta         TEXT NOT NULL,
                questao          TEXT NOT NULL,
                grupo            VARCHAR(20) NOT NULL DEFAULT '',
                momento_entrega  DATETIME NULL,
                pontuacao        INT NULL,
                cluster          VARCHAR(20) NULL,
                KEY idx_migration_join     (user_id, periodo, semestre, turma_ano, areaConhecimento),
                KEY idx_migration_cluster  (periodo, semestre, turma_ano, cluster),
                KEY idx_migration_questao  (questao(191)),
                KEY idx_migration_resposta (resposta(191))
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """))


def _drop_staging(engine):

    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS migration"))


def _build_clusters(engine):
    with engine.begin() as conn:
        conn.execute(text("UPDATE migration SET cluster = grupo"))


def _create_users(engine):
    with engine.connect() as conn:
        user_ids = conn.execute(text(
            "SELECT DISTINCT user_id FROM migration m "
            "WHERE NOT EXISTS (SELECT 1 FROM users u WHERE u.id = m.user_id)"
        )).fetchall()

    for (user_id,) in user_ids:
        for _ in range(5):
            try:
                with engine.begin() as conn:
                    conn.execute(text("""
                        INSERT INTO users
                            (id, name, email, password, cpf, dataNascimento,
                             createdAt, updatedAt, lastIpAddress, telefone, status)
                        VALUES
                            (:id, :name, :email, :password, :cpf, :dataNascimento,
                             NOW(), NOW(), :ip, :telefone, 1)
                    """), {
                        'id':             user_id,
                        'name':           fake.name(),
                        'email':          fake.unique.email(),
                        'password':       fake.password(),
                        'cpf':            int(fake.unique.cpf().replace('.', '').replace('-', '')),
                        'dataNascimento': fake.date_of_birth(minimum_age=14, maximum_age=20),
                        'ip':             fake.ipv4(),
                        'telefone':       int(fake.msisdn()[:11]),
                    })
                break
            except Exception:
                continue


def _create_contests(engine):
    admin_subquery = "(SELECT id FROM users WHERE email = 'admin@gmail.com')"

    with engine.connect() as conn:
        clusters = conn.execute(text("""
            SELECT DISTINCT periodo, semestre, turma_ano, cluster
            FROM migration
            WHERE cluster IS NOT NULL
            ORDER BY turma_ano, periodo, semestre, cluster
        """)).fetchall()

    rows = []
    for c in clusters:
        titulo = f"{c.turma_ano} ano - {c.periodo} - {c.semestre} - {c.cluster}"
        with engine.connect() as conn:
            existe = conn.execute(
                text("SELECT 1 FROM PROVA WHERE titulo = :titulo"),
                {"titulo": titulo}
            ).fetchone()
        if not existe:
            rows.append(f"('{titulo}', 90, 0, {admin_subquery})")

    if rows:
        with engine.begin() as conn:
            conn.execute(text(
                "INSERT INTO PROVA (titulo, tempoMaximo, salvarTempoResposta, createdBy) VALUES "
                + ", ".join(rows)
            ))


def _rename_contest(engine, titulo_gerado: str, titulo_novo: str):
    """Renomeia a PROVA criada pelo pipeline para o título customizado."""
    if titulo_gerado == titulo_novo:
        return
    with engine.begin() as conn:
        conn.execute(text(
            "UPDATE PROVA SET titulo = :novo WHERE titulo = :gerado"
        ), {"novo": titulo_novo, "gerado": titulo_gerado})


def _create_aplicacoes(engine):
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT IGNORE INTO APLICACAO_PROVA (idProva, idArea, dataHoraInicio, dataHoraFim)
            SELECT
                p.idProva,
                ac.idArea,
                MIN(m.momento_entrega),
                MAX(m.momento_entrega)
            FROM migration m
            JOIN PROVA p ON p.titulo = CONCAT(m.turma_ano, ' ano - ', m.periodo, ' - ', m.semestre, ' - ', m.cluster)
            JOIN AREA_CONHECIMENTO ac ON ac.sigla = m.areaConhecimento
            WHERE m.cluster         IS NOT NULL
              AND m.momento_entrega IS NOT NULL
            GROUP BY p.idProva, ac.idArea
        """))


def _create_questions(engine):
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT IGNORE INTO QUESTAO (nome, idArea)
            SELECT DISTINCT m.questao, ac.idArea
            FROM migration m
            JOIN AREA_CONHECIMENTO ac ON ac.sigla = m.areaConhecimento
        """))


def _create_alternatives(engine):
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT IGNORE INTO ALTERNATIVA (idQuestao, descricao)
            SELECT DISTINCT q.idQuestao, m.resposta
            FROM migration m
            JOIN AREA_CONHECIMENTO ac ON ac.sigla = m.areaConhecimento
            JOIN QUESTAO q ON q.nome  = m.questao
                          AND q.idArea = ac.idArea
        """))


def _contests_questions(engine):
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT IGNORE INTO contem (idProva, idQuestao)
            SELECT DISTINCT p.idProva, q.idQuestao
            FROM migration m
            JOIN AREA_CONHECIMENTO ac ON ac.sigla = m.areaConhecimento
            JOIN QUESTAO q ON q.nome  = m.questao
                          AND q.idArea = ac.idArea
            JOIN PROVA p   ON p.titulo = CONCAT(m.turma_ano, ' ano - ', m.periodo, ' - ', m.semestre, ' - ', m.cluster)
            WHERE m.cluster IS NOT NULL
        """))


def _users_answers(engine, periodo: str, semestre: str, turma_ano: int, cluster: str):
    titulo = f"{turma_ano} ano - {periodo} - {semestre} - {cluster}"

    with engine.connect() as conn:
        total_aplicacoes = conn.execute(text("""
            SELECT COUNT(*) FROM APLICACAO_PROVA ap
            JOIN PROVA p ON p.idProva = ap.idProva
            WHERE p.titulo = :titulo
        """), {"titulo": titulo}).scalar()

    params = {
        'titulo':     titulo,
        'periodo':    periodo,
        'semestre':   semestre,
        'ano':        turma_ano,
        'cluster':    cluster,
        'min_areas':  total_aplicacoes,
    }

    with engine.begin() as conn:
        conn.execute(text("""
            INSERT IGNORE INTO RESPOSTA (cpf, idQuestao, idAplicacao, resposta, dataHoraResposta)
            SELECT
                u.cpf,
                q.idQuestao,
                ap.idAplicacao,
                a.idAlternativa,
                NULL
            FROM migration m
            JOIN AREA_CONHECIMENTO ac ON ac.sigla = m.areaConhecimento
            JOIN users           u  ON u.id         = m.user_id
            JOIN QUESTAO         q  ON q.nome        = m.questao
                                   AND q.idArea       = ac.idArea
            JOIN PROVA           p  ON p.titulo      = :titulo
            JOIN APLICACAO_PROVA ap ON ap.idProva    = p.idProva
                                   AND ap.idArea      = ac.idArea
            JOIN ALTERNATIVA     a  ON a.idQuestao   = q.idQuestao
                                   AND a.descricao   = m.resposta
            WHERE m.periodo   = :periodo
              AND m.semestre  = :semestre
              AND m.turma_ano = :ano
              AND m.cluster   = :cluster
              AND m.user_id IN (
                  SELECT m2.user_id
                  FROM migration m2
                  WHERE m2.cluster   = :cluster
                    AND m2.semestre  = :semestre
                    AND m2.turma_ano = :ano
                    AND m2.periodo   = :periodo
                  GROUP BY m2.user_id
                  HAVING COUNT(DISTINCT m2.areaConhecimento) >= :min_areas
              )
        """), params)


def _create_realiza_prova(engine):
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT IGNORE INTO realiza_prova (cpf, idAplicacao, dataHoraInicio, dataHoraFim, finalizada)
            SELECT
                u.cpf,
                ap.idAplicacao,
                NULL,
                MAX(m.momento_entrega),
                1
            FROM migration m
            JOIN AREA_CONHECIMENTO ac ON ac.sigla = m.areaConhecimento
            JOIN users           u  ON u.id      = m.user_id
            JOIN PROVA           p  ON p.titulo   = CONCAT(m.turma_ano, ' ano - ', m.periodo, ' - ', m.semestre, ' - ', m.cluster)
            JOIN APLICACAO_PROVA ap ON ap.idProva = p.idProva
                                   AND ap.idArea  = ac.idArea
            WHERE m.cluster        IS NOT NULL
              AND m.momento_entrega IS NOT NULL
            GROUP BY u.cpf, ap.idAplicacao
        """))


def _update_pontuacoes(engine):
    with engine.begin() as conn:
        conn.execute(text("""
            UPDATE realiza_prova rp
            JOIN APLICACAO_PROVA ap ON ap.idAplicacao = rp.idAplicacao
            JOIN PROVA           p  ON p.idProva      = ap.idProva
            JOIN users           u  ON u.cpf          = rp.cpf
            JOIN (
                SELECT DISTINCT m.user_id, ac.idArea, m.turma_ano, m.periodo, m.semestre, m.cluster, m.pontuacao
                FROM migration m
                JOIN AREA_CONHECIMENTO ac ON ac.sigla = m.areaConhecimento
                WHERE m.pontuacao IS NOT NULL
            ) m ON m.user_id = u.id
              AND m.idArea   = ap.idArea
              AND CONCAT(m.turma_ano, ' ano - ', m.periodo, ' - ', m.semestre, ' - ', m.cluster) = p.titulo
            SET rp.pontuacao = m.pontuacao
        """))

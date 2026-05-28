import re
import io
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


def _engine():
    return create_engine(
        f'mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}?charset=utf8mb4'
    )

def _parse_pontuacao(valor) -> int | None:
    try:
        return int(str(valor).split('/')[0].strip())
    except (ValueError, AttributeError):
        return None


def _parse_grupo(nome_arquivo: str) -> str:
    """Extrai letras de turma do nome do arquivo: COD_1ABCD_1M.csv → 'ABCD'"""
    match = re.search(r'_\d([A-Z]+)_', nome_arquivo.upper())
    return match.group(1) if match else ''


def _processar_csv_bytes(
    conteudo: bytes,
    nome_arquivo: str,
    area: str,
    periodo: str,
    semestre: str,
    turma_ano: int,
    grupo: str,
) -> list[dict]:
    """Lê um CSV em memória e retorna as linhas prontas para INSERT."""
    df = pd.read_csv(io.BytesIO(conteudo))

    if str(df.iloc[0, 0]).strip().upper() == "RESPOSTA":
        df = df.iloc[1:].reset_index(drop=True)

    pontuacao_map = dict(zip(df.iloc[:, -1].values, df.iloc[:, 1].apply(_parse_pontuacao).values))
    momento_map   = dict(zip(df.iloc[:, -1].values, pd.to_datetime(df.iloc[:, 0], errors='coerce').values))

    respostas = df.iloc[:, 3:-1].copy()
    respostas.index = df.iloc[:, -1].values

    df_melted = respostas.stack().dropna().reset_index()
    df_melted.columns = ["user_id", "questao", "resposta"]
    df_melted = df_melted[df_melted["user_id"].astype(str).str.strip() != ""]
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

    engine.dispose()
    return {"linhas_importadas": total_linhas, "mensagem": "Importação concluída com sucesso"}


# Mantido para compatibilidade com chamadas que passam um único arquivo
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


# ── helpers de pipeline ────────────────────────────────────────────────────────

def _build_clusters(engine):
    with engine.begin() as conn:
        conn.execute(text("""
            UPDATE migration m
            JOIN migration cod
                ON  cod.user_id          = m.user_id
                AND cod.periodo          = m.periodo
                AND cod.semestre         = m.semestre
                AND cod.turma_ano        = m.turma_ano
                AND cod.areaConhecimento = 'COD'
            SET m.cluster = cod.grupo
        """))


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
    admin_subquery = "(SELECT id FROM users WHERE email = 'admin@admin.com')"

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
            INSERT IGNORE INTO APLICACAO_PROVA (idProva, tipo, dataHoraInicio, dataHoraFim)
            SELECT
                p.idProva,
                m.areaConhecimento,
                MIN(m.momento_entrega),
                MAX(m.momento_entrega)
            FROM migration m
            JOIN PROVA p ON p.titulo = CONCAT(m.turma_ano, ' ano - ', m.periodo, ' - ', m.semestre, ' - ', m.cluster)
            WHERE m.cluster         IS NOT NULL
              AND m.momento_entrega IS NOT NULL
            GROUP BY p.idProva, m.areaConhecimento
        """))


def _create_questions(engine):
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT IGNORE INTO QUESTAO (nome, areaConhecimento)
            SELECT DISTINCT m.questao, m.areaConhecimento
            FROM migration m
        """))


def _create_alternatives(engine):
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT IGNORE INTO ALTERNATIVA (idQuestao, descricao)
            SELECT DISTINCT q.idQuestao, m.resposta
            FROM migration m
            JOIN QUESTAO q ON q.nome            = m.questao
                          AND q.areaConhecimento = m.areaConhecimento
        """))


def _contests_questions(engine):
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT IGNORE INTO contem (idProva, idQuestao)
            SELECT DISTINCT p.idProva, q.idQuestao
            FROM migration m
            JOIN QUESTAO q ON q.nome            = m.questao
                          AND q.areaConhecimento = m.areaConhecimento
            JOIN PROVA p   ON p.titulo = CONCAT(m.turma_ano, ' ano - ', m.periodo, ' - ', m.semestre, ' - ', m.cluster)
            WHERE m.cluster IS NOT NULL
        """))


def _users_answers(engine, periodo: str, semestre: str, turma_ano: int, cluster: str):
    titulo = f"{turma_ano} ano - {periodo} - {semestre} - {cluster}"
    params = {
        'titulo':   titulo,
        'periodo':  periodo,
        'semestre': semestre,
        'ano':      turma_ano,
        'cluster':  cluster,
    }

    with engine.begin() as conn:
        conn.execute(text("""
            INSERT IGNORE INTO RESPONDE (cpf, idQuestao, idAplicacao, resposta, dataHoraResposta)
            SELECT
                u.cpf,
                q.idQuestao,
                ap.idAplicacao,
                a.idAlternativa,
                NULL
            FROM migration m
            JOIN users           u  ON u.id         = m.user_id
            JOIN QUESTAO         q  ON q.nome        = m.questao
                                   AND q.areaConhecimento = m.areaConhecimento
            JOIN PROVA           p  ON p.titulo      = :titulo
            JOIN APLICACAO_PROVA ap ON ap.idProva    = p.idProva
                                   AND ap.tipo       = m.areaConhecimento
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
                  HAVING COUNT(DISTINCT m2.areaConhecimento) >= 3
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
            JOIN users           u  ON u.id      = m.user_id
            JOIN PROVA           p  ON p.titulo   = CONCAT(m.turma_ano, ' ano - ', m.periodo, ' - ', m.semestre, ' - ', m.cluster)
            JOIN APLICACAO_PROVA ap ON ap.idProva = p.idProva
                                   AND ap.tipo    = m.areaConhecimento
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
                SELECT DISTINCT user_id, areaConhecimento, turma_ano, periodo, semestre, cluster, pontuacao
                FROM migration
                WHERE pontuacao IS NOT NULL
            ) m ON m.user_id         = u.id
              AND m.areaConhecimento = ap.tipo
              AND CONCAT(m.turma_ano, ' ano - ', m.periodo, ' - ', m.semestre, ' - ', m.cluster) = p.titulo
            SET rp.pontuacao = m.pontuacao
        """))

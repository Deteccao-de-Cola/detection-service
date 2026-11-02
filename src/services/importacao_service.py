import io
import csv
import pandas as pd
from faker import Faker
from sqlalchemy import create_engine, text

from src.config.database import MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB, MYSQL_PORT

fake = Faker('pt_BR')

# Steps of the migration:
#  - (importar_csvs) Receive and read files mapping the last collumn with user id in database. 
#  - (_create_staging) Insert in ´temporary´ migrations table 
#  - (_create_users) Insert users (faked ones) from migration table to users table using the id in the table to correlate both
#  - (_create_contest) Criação das provas a partir da concactenação de turmas utilizando um HAVING BY 
#  - (_create_questions) Cria as questões e as liga à prova pela tabela contem (N:M)
#  - (_create_alternatives) Insere as alternativas
#  - (_aplicar_gabarito) Insere no gabarito a partir da buscas das questoes de dentro da prova
#  - (_users_answers) Armazena as alternativas escolhidas pelos alunos nas provas a partir do where filtrando por turuma turno periodo etc. Concatenando apenas os usuários que tiverem o minimo de aplicacoes para aquela prova (3) no caso, para remover usuários faltantes em alguma das provas. 
#       - Pra essa parte eu preciso de garantir que os alunos nao estarao duplicados nas tabelas. 
#  - (_create_realiza_prova) Cria realiza prova que é responsavel por armazenar qual prova foi realizada por qual usuario bem como armazenar a pontuacao do mesmo em cada aplicacao    
#. - (_update_pontuacoes)Atualiza a pontuação dos usuarios dentro de cada prova


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


def _parse_user_id(valor) -> int | None:
    if pd.isna(valor):
        return None
    try:
        return int(float(valor))
    except (TypeError, ValueError):
        return None


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
    return pd.read_csv(io.StringIO(texto), sep=_detectar_separador(texto), dtype=str)


def _ler_planilha(conteudo: bytes, nome_arquivo: str) -> pd.DataFrame:
    """Lê um CSV ou XLSX em memória. Tudo como texto, para '40' não virar '40.0'."""
    try:
        if nome_arquivo.lower().endswith(('.xlsx', '.xlsm')):
            return pd.read_excel(io.BytesIO(conteudo), dtype=str)
        return _ler_csv(conteudo)
    except (pd.errors.ParserError, pd.errors.EmptyDataError, UnicodeDecodeError) as e:
        raise PlanilhaInvalida(f"Não foi possível ler '{nome_arquivo}': {str(e).strip()}") from e


def _normalizar_respostas(respostas: pd.Series) -> pd.Series:
    """Mesma normalização para alunos e gabarito; se divergirem, a alternativa certa não casa."""
    return respostas.astype(str).str.strip().str.upper()


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
    df = _ler_planilha(conteudo, nome_arquivo)

    if str(df.iloc[0, 0]).strip().upper() == "RESPOSTA":
        df = df.iloc[1:].reset_index(drop=True)

    #para encontrar as colunas fixas (carimbo, pontuação, turma e ID)
    nomes = [str(c).strip().upper().replace('-', '') for c in df.columns]

    col_data  = _achar_coluna(nomes, ['CARIMBO'], padrao=0)
    col_pont  = _achar_coluna(nomes, ['PONTUA'], padrao=1)
    col_turma = _achar_coluna(nomes, ['SÉRIE', 'TURMA'], padrao=2)

    # Sem fallback: o ID é a única chave do aluno, e adivinhar a coluna mistura alunos
    if 'ID' not in nomes:
        raise PlanilhaInvalida(f"'{nome_arquivo}' não tem a coluna ID, que identifica o aluno.")
    
    col_id   = nomes.index('ID')
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
    df_melted["resposta"]        = _normalizar_respostas(df_melted["resposta"])
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
    ano_aplicacao: int,
    serie: int,
    periodo: str,
    bimestre: str,
    turmas: str,
) -> dict:

    engine   = _engine()
    periodo  = periodo.lower().strip()
    bimestre = bimestre.upper().strip()
    turmas   = ''.join(sorted(turmas.upper().strip()))

    _create_staging(engine)

    try:
        total_linhas = 0
        gabaritos = {}
        for arq in arquivos:
            area = arq['area'].upper()
            # A staging mantém os nomes antigos: semestre = bimestre, turma_ano = série, grupo = turmas
            rows = _processar_csv_bytes(
                conteudo=arq['conteudo'],
                nome_arquivo=arq['nome_arquivo'],
                area=area,
                periodo=periodo,
                semestre=bimestre,
                turma_ano=serie,
                grupo=turmas,
            )
            if not rows:
                continue
            # Lido aqui para que um gabarito inválido falhe antes de qualquer gravação na prova
            if arq.get('gabarito'):
                gabaritos[area] = _receive_answer_keys(arq['gabarito'], arq['nome_gabarito'])
                
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

        _create_users(engine)

        # A prova é localizada uma única vez; daqui em diante todas as etapas usam o idProva
        id_prova = _create_contest(engine, ano_aplicacao, serie, periodo, bimestre, turmas)

        _create_aplicacoes(engine, id_prova)
        _create_questions(engine, id_prova)
        _create_alternatives(engine, id_prova)
        for area, gabarito in gabaritos.items():
            _aplicar_gabarito(engine, id_prova, area, gabarito)
        _users_answers(engine, id_prova)
        _create_realiza_prova(engine, id_prova)
        _update_pontuacoes(engine, id_prova)

        return {"linhas_importadas": total_linhas, "mensagem": "Importação concluída com sucesso"}
    finally:
        _drop_staging(engine)
        engine.dispose()

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
                KEY idx_migration_join     (user_id, periodo, semestre, turma_ano, areaConhecimento),
                KEY idx_migration_questao  (questao(191)),
                KEY idx_migration_resposta (resposta(191))
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """))


def _drop_staging(engine):

    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS migration"))


def _create_users(engine):
    with engine.connect() as conn:
        #Query utilizada para encontrar os usuarios da migracao que nao existem na tabela users
        user_ids = conn.execute(text(
            "SELECT DISTINCT user_id FROM migration "
            "WHERE user_id NOT IN (SELECT id FROM users)"
        )).fetchall()

    # Aqui para cada linha dentro da tabela de migrações em que um usuário nao existir na tabela de users é criado u usuário para o mesmo (tenta)
    # 5 vezes pro caso de ocorrer alguma colisao. 
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


def _create_contest(engine, ano_aplicacao: int, serie: int, periodo: str, bimestre: str, turmas: str) -> int:
    """Devolve o idProva da prova com exatamente esta identificação (mesmo ano, série,
    período, bimestre e conjunto de turmas), criando-a se ainda não existir.

    Turmas que se cruzam com outra prova já foram barradas no Laravel (PROVA::conflitoDeTurmas).
    """
    chave = {
        "ano_aplicacao": ano_aplicacao,
        "serie":         str(serie),  # texto: ENUM('1','2','3') trata número como posição
        "periodo":       periodo,
        "bimestre":      bimestre,
    }
    with engine.begin() as conn:
        id_prova = conn.execute(text("""
            SELECT p.idProva
            FROM PROVA p
            JOIN PROVA_TURMA t ON t.idProva = p.idProva
            WHERE p.anoAplicacao = :ano_aplicacao
              AND p.serie        = :serie
              AND p.periodo      = :periodo
              AND p.bimestre     = :bimestre
            GROUP BY p.idProva
            HAVING GROUP_CONCAT(t.letra ORDER BY t.letra SEPARATOR '') = :turmas
        """), {**chave, "turmas": turmas}).scalar()

        if id_prova is None:
            # A coluna titulo ainda é obrigatória; mesmo formato do PROVA::tituloGerado do Laravel
            id_prova = conn.execute(text("""
                INSERT INTO PROVA (titulo, anoAplicacao, serie, periodo, bimestre,
                                   tempoMaximo, salvarTempoResposta, createdBy)
                VALUES (:titulo, :ano_aplicacao, :serie, :periodo, :bimestre, 90, 0,
                        (SELECT id FROM users WHERE email = 'admin@gmail.com'))
            """), {**chave, "titulo": f"{serie} ano - {periodo} - {bimestre} - {turmas}"}).lastrowid

            conn.execute(text(
                "INSERT INTO PROVA_TURMA (idProva, letra) VALUES (:id_prova, :letra)"
            ), [{"id_prova": id_prova, "letra": letra} for letra in turmas])
    return id_prova


def _create_aplicacoes(engine, id_prova: int):
    with engine.begin() as conn:
        janelas = conn.execute(text("""
            SELECT ac.idArea, MIN(m.momento_entrega), MAX(m.momento_entrega)
            FROM migration m
            JOIN AREA_CONHECIMENTO ac ON ac.sigla = m.areaConhecimento
            WHERE m.momento_entrega IS NOT NULL
            GROUP BY ac.idArea
        """)).fetchall()

        existentes = {id_area for (id_area,) in conn.execute(text(
            "SELECT idArea FROM APLICACAO_PROVA WHERE idProva = :id_prova"
        ), {"id_prova": id_prova})}

        for id_area, inicio, fim in janelas:
            if id_area not in existentes:
                conn.execute(text("""
                    INSERT INTO APLICACAO_PROVA (idProva, idArea, dataHoraInicio, dataHoraFim)
                    VALUES (:id_prova, :id_area, :inicio, :fim)
                """), {"id_prova": id_prova, "id_area": id_area, "inicio": inicio, "fim": fim})


def _create_questions(engine, id_prova: int):
    # Prova e questão se ligam pela contem (N:M); por isso cada questão nova precisa do seu idQuestao
    with engine.begin() as conn:
        novas = conn.execute(text("""
            SELECT DISTINCT m.questao, ac.idArea
            FROM migration m
            JOIN AREA_CONHECIMENTO ac ON ac.sigla = m.areaConhecimento
            WHERE NOT EXISTS (
                SELECT 1
                FROM contem c
                JOIN QUESTAO q ON q.idQuestao = c.idQuestao
                WHERE c.idProva   = :id_prova
                  AND q.idArea    = ac.idArea
                  AND q.descricao = m.questao
            )
        """), {"id_prova": id_prova}).fetchall()

        for questao, id_area in novas:
            id_questao = conn.execute(text(
                "INSERT INTO QUESTAO (descricao, observacao, idArea) VALUES (:descricao, '', :id_area)"
            ), {"descricao": questao, "id_area": id_area}).lastrowid
            conn.execute(text(
                "INSERT INTO contem (idProva, idQuestao) VALUES (:id_prova, :id_questao)"
            ), {"id_prova": id_prova, "id_questao": id_questao})


def _create_alternatives(engine, id_prova: int):
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO ALTERNATIVA (idQuestao, descricao)
            SELECT DISTINCT q.idQuestao, m.resposta
            FROM migration m
            JOIN AREA_CONHECIMENTO ac ON ac.sigla = m.areaConhecimento
            JOIN contem  c ON c.idProva   = :id_prova
            JOIN QUESTAO q ON q.idQuestao = c.idQuestao
                          AND q.idArea    = ac.idArea
                          AND q.descricao = m.questao
            LEFT JOIN ALTERNATIVA a ON a.idQuestao = q.idQuestao
                                   AND a.descricao = m.resposta
            WHERE a.idAlternativa IS NULL
        """), {"id_prova": id_prova})


def _users_answers(engine, id_prova: int):
    with engine.begin() as conn:
        total_aplicacoes = conn.execute(text(
            "SELECT COUNT(*) FROM APLICACAO_PROVA WHERE idProva = :id_prova"
        ), {"id_prova": id_prova}).scalar()

        respostas = conn.execute(text("""
            SELECT u.cpf, q.idQuestao, ap.idAplicacao, a.idAlternativa
            FROM migration m
            JOIN AREA_CONHECIMENTO ac ON ac.sigla = m.areaConhecimento
            JOIN users           u  ON u.id         = m.user_id
            JOIN contem          c  ON c.idProva     = :id_prova
            JOIN QUESTAO         q  ON q.idQuestao   = c.idQuestao
                                   AND q.idArea       = ac.idArea
                                   AND q.descricao    = m.questao
            JOIN APLICACAO_PROVA ap ON ap.idProva    = :id_prova
                                   AND ap.idArea      = ac.idArea
            JOIN ALTERNATIVA     a  ON a.idQuestao   = q.idQuestao
                                   AND a.descricao   = m.resposta
            WHERE m.user_id IN (
                SELECT m2.user_id
                FROM migration m2
                GROUP BY m2.user_id
                HAVING COUNT(DISTINCT m2.areaConhecimento) >= :min_areas
            )
        """), {"id_prova": id_prova, "min_areas": total_aplicacoes}).fetchall()

        for cpf, id_questao, id_aplicacao, id_alternativa in respostas:
            #CONSTRAINT RESPOSTA_UQ UNIQUE (cpf, idQuestao, idAplicacao),
            #Em outras palavras o mesmo usuário na mesma questao na mesma aplicacao nao pode ter duas respostas
            conn.execute(text("""
                INSERT INTO RESPOSTA (cpf, idQuestao, idAplicacao, resposta, dataHoraResposta)
                VALUES (:cpf, :id_questao, :id_aplicacao, :id_alternativa, NULL)
                ON DUPLICATE KEY UPDATE resposta = :id_alternativa
            """), {
                "cpf":            cpf,
                "id_questao":     id_questao,
                "id_aplicacao":   id_aplicacao,
                "id_alternativa": id_alternativa,
            })


def _create_realiza_prova(engine, id_prova: int):
    # Mesma tabela derivada de _create_aplicacoes, por causa do MAX no ON DUPLICATE KEY
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO realiza_prova (cpf, idAplicacao, dataHoraInicio, dataHoraFim, finalizada)
            SELECT * FROM (
                SELECT
                    u.cpf                  AS cpf,
                    ap.idAplicacao         AS idAplicacao,
                    NULL                   AS dataHoraInicio,
                    MAX(m.momento_entrega) AS fim,
                    1                      AS finalizada
                FROM migration m
                JOIN AREA_CONHECIMENTO ac ON ac.sigla = m.areaConhecimento
                JOIN users           u  ON u.id      = m.user_id
                JOIN APLICACAO_PROVA ap ON ap.idProva = :id_prova
                                       AND ap.idArea  = ac.idArea
                WHERE m.momento_entrega IS NOT NULL
                GROUP BY u.cpf, ap.idAplicacao
            ) AS nova
            ON DUPLICATE KEY UPDATE dataHoraFim = nova.fim
        """), {"id_prova": id_prova})


def _update_pontuacoes(engine, id_prova: int):
    with engine.begin() as conn:
        conn.execute(text("""
            UPDATE realiza_prova rp
            JOIN APLICACAO_PROVA ap ON ap.idAplicacao = rp.idAplicacao
            JOIN users           u  ON u.cpf          = rp.cpf
            JOIN (
                SELECT DISTINCT m.user_id, ac.idArea, m.pontuacao
                FROM migration m
                JOIN AREA_CONHECIMENTO ac ON ac.sigla = m.areaConhecimento
                WHERE m.pontuacao IS NOT NULL
            ) m ON m.user_id = u.id
              AND m.idArea   = ap.idArea
            SET rp.pontuacao = m.pontuacao
            WHERE ap.idProva = :id_prova
        """), {"id_prova": id_prova})


def _receive_answer_keys(conteudo: bytes, nome_arquivo: str) -> list[dict]:
    """Lê o arquivo de gabarito: o cabeçalho tem as questões e a única linha tem a resposta certa de cada uma."""
    df = _ler_planilha(conteudo, nome_arquivo)

    if len(df) != 1:
        raise PlanilhaInvalida(
            f"O gabarito '{nome_arquivo}' deve ter exatamente uma linha de respostas, mas tem {len(df)}."
        )

    linha = df.iloc[0]
    # Todo gabarito tem resposta em todas as colunas; célula vazia significa cabeçalho e respostas desalinhados
    if linha.isna().any():
        raise PlanilhaInvalida(
            f"O gabarito '{nome_arquivo}' tem {len(df.columns)} colunas no cabeçalho e "
            f"{int(linha.notna().sum())} respostas. Confira se o cabeçalho tem só as colunas de questão."
        )

    respostas = _normalizar_respostas(linha)

    return [
        {"questao": str(questao), "resposta": resposta}
        for questao, resposta in respostas.items()
    ]


def _aplicar_gabarito(engine, id_prova: int, area: str, gabarito: list[dict]):
    """Marca, em cada questão da prova, a alternativa que bate com o gabarito."""
    # Comparação em vez de 1 fixo: num reimport com gabarito corrigido, a alternativa antiga é desmarcada
    with engine.begin() as conn:
        conn.execute(text("""
            UPDATE ALTERNATIVA a
            JOIN QUESTAO q            ON q.idQuestao = a.idQuestao
            JOIN contem c             ON c.idQuestao = q.idQuestao
            JOIN AREA_CONHECIMENTO ac ON ac.idArea   = q.idArea
            SET a.alternativaCorreta = (a.descricao = :resposta)
            WHERE c.idProva   = :id_prova
              AND ac.sigla    = :area
              AND q.descricao = :questao
        """), [{"id_prova": id_prova, "area": area, **item} for item in gabarito])

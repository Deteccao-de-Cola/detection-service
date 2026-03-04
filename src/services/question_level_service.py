from src.models.respostas_lake import db


class QuestionLevelService:
    @staticmethod
    def recalculate_questions_level(contest_id):
        questoes_sql = db.text("""
            SELECT q.idQuestao, q.opcaoCorreta, q.nome, q.descricao, q.dificuldade
            FROM QUESTAO q
            JOIN contem c ON q.idQuestao = c.idQuestao
            WHERE c.idProva = :contestId
        """)
        questoes_result = db.session.execute(questoes_sql, {"contestId": contest_id})
        questoes = [dict(row._mapping) for row in questoes_result.fetchall()]

        total_alunos_sql = db.text("""
            SELECT COUNT(DISTINCT cpf) as total
            FROM RESPONDE
            WHERE idProva = :contestId
        """)
        total_alunos = db.session.execute(total_alunos_sql, {"contestId": contest_id}).fetchone()[0] or 0

        for questao in questoes:
            questao_id = questao['idQuestao']

            todas = db.session.execute(db.text("""
                SELECT COUNT(*) FROM RESPONDE
                WHERE idProva = :contestId AND idQuestao = :questaoId
            """), {"contestId": contest_id, "questaoId": questao_id}).fetchone()[0] or 0

            corretas = db.session.execute(db.text("""
                SELECT COUNT(*) FROM QUESTAO q
                JOIN RESPONDE r ON q.idQuestao = r.idQuestao
                WHERE r.idQuestao = :questaoId
                  AND r.idProva = :contestId
                  AND q.opcaoCorreta = r.resposta
            """), {"contestId": contest_id, "questaoId": questao_id}).fetchone()[0] or 0

            erradas = todas - corretas
            puladas = total_alunos - todas
            percentual_acerto = (corretas / total_alunos * 100) if total_alunos > 0 else 0

            if percentual_acerto < 25:
                dificuldade = 'MUITO_DIFICIL'
            elif percentual_acerto < 50:
                dificuldade = 'DIFICIL'
            elif percentual_acerto < 75:
                dificuldade = 'MEDIA'
            else:
                dificuldade = 'FACIL'

            db.session.execute(db.text("""
                UPDATE QUESTAO SET dificuldade = :dificuldade WHERE idQuestao = :questaoId
            """), {"dificuldade": dificuldade, "questaoId": questao_id})

            questao['erradas'] = erradas
            questao['corretas'] = corretas
            questao['puladas'] = puladas
            questao['percentualAcerto'] = round(percentual_acerto, 2)
            questao['dificuldade'] = dificuldade

        db.session.commit()
        return questoes

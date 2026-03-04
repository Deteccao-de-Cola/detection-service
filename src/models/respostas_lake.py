from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class RespostasLake(db.Model):
    __tablename__ = 'respostas_lake'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    sourceId = db.Column(db.Integer, nullable=False)
    contestId = db.Column(db.Integer, nullable=True, default=0)
    respondidaEm = db.Column(db.DateTime, nullable=False)
    itemId = db.Column(db.Integer, nullable=False)
    respostaUsuario = db.Column(db.String(255), nullable=True)
    userId = db.Column(db.Integer, nullable=False)

    def __repr__(self):
        return f'<RespostasLake {self.id} - {self.tipo_acao}>'

    def to_dict(self):
        return {
            'id': self.id,
            'respondidaEm': self.respondidaEm.isoformat() if self.respondidaEm else None,
            'tipo_acao': self.tipo_acao,
            'itemId': self.itemId,
            'fonte': self.fonte,
            'respostaUsuario': self.respostaUsuario,
            'plataforma': self.plataforma,
            'userId': self.userId
        }

    @staticmethod
    def get_salvar_tempo_resposta(exam_id):
        result = db.session.execute(
            db.text("SELECT salvarTempoResposta FROM PROVA WHERE idProva = :examId"),
            {"examId": exam_id}
        ).fetchone()
        if result is None:
            return True
        return bool(result[0])

    @staticmethod
    def select_users(exam_id=None, sourceId=None):
        users = RespostasLake.query.with_entities(RespostasLake.userId)

        if exam_id is not None:
            users = users.filter(RespostasLake.contestId == exam_id)

        if sourceId is not None:
            users = users.filter(RespostasLake.sourceId == sourceId)

        users = users.distinct().order_by(RespostasLake.userId).all()
        return [u[0] for u in users]

    @staticmethod
    def select_user_questions(userId, exam_id=None, sourceId=None, orderByTimestamp=False, withTimestamp=True):
        data = {"idUser": userId}

        if exam_id is not None:
            data["examId"] = exam_id
        if sourceId is not None:
            data["sourceId"] = sourceId

        filters = " AND userId = :idUser"
        if exam_id is not None:
            filters += " AND contestId = :examId"
        if sourceId is not None:
            filters += " AND sourceId = :sourceId"

        if not withTimestamp:
            sql = f"""SELECT id, itemId, NULL as respondidaEm, userId, respostaUsuario
            FROM respostas_lake rl1
            WHERE userId = :idUser"""
            if exam_id is not None:
                sql += """ AND contestId = :examId"""
            if sourceId is not None:
                sql += """ AND sourceId = :sourceId"""
            sql += """
            AND id = (
                SELECT MAX(id)
                FROM respostas_lake rl2
                WHERE rl2.itemId = rl1.itemId
                    AND rl2.userId = :idUser"""
            if exam_id is not None:
                sql += """ AND rl2.contestId = :examId"""
            if sourceId is not None:
                sql += """ AND rl2.sourceId = :sourceId"""
            sql += """)
            ORDER BY itemId ASC;"""
        else:
            sql = """SELECT id, itemId,
            IF(YEAR(respondidaEm) = 0, NULL, respondidaEm) as respondidaEm,
            userId, respostaUsuario
            FROM respostas_lake rl1
            WHERE userId = :idUser"""
            if exam_id is not None:
                sql += """ AND contestId = :examId"""
            if sourceId is not None:
                sql += """ AND sourceId = :sourceId"""

            sql += """
            AND IF(YEAR(respondidaEm) = 0, NULL, respondidaEm) <=> (
                SELECT MAX(IF(YEAR(respondidaEm) = 0, NULL, respondidaEm))
                FROM respostas_lake rl2
                WHERE rl2.itemId = rl1.itemId
                    AND rl2.userId = :idUser"""
            if exam_id is not None:
                sql += """ AND rl2.contestId = :examId"""
            if sourceId is not None:
                sql += """ AND rl2.sourceId = :sourceId"""

            if orderByTimestamp is False:
                sql += """)
                ORDER BY itemId ASC;"""
            if orderByTimestamp is True:
                sql += """)
                ORDER BY respondidaEm ASC;"""

        # print(db.text(sql), data)
        result = db.session.execute(db.text(sql), data)
        rows = result.fetchall()

        # pylint: disable=protected-access
        return [dict(row._mapping) for row in rows]

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class RespostasLake(db.Model):
    __tablename__ = 'respostas_lake'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    source_id = db.Column(db.Integer, nullable=False)
    contest_id = db.Column(db.Integer, nullable=True, default=0)
    respondida_em = db.Column(db.DateTime, nullable=False)
    item_id = db.Column(db.Integer, nullable=False)
    resposta_usuario = db.Column(db.String(255), nullable=True)
    user_id = db.Column(db.Integer, nullable=False)

    def __repr__(self):
        return f'<RespostasLake {self.id} - {self.tipo_acao}>'

    def to_dict(self):
        return {
            'id': self.id,
            'respondida_em': self.respondida_em.isoformat() if self.respondida_em else None,
            'tipo_acao': self.tipo_acao,
            'item_id': self.item_id,
            'fonte': self.fonte,
            'resposta_usuario': self.resposta_usuario,
            'plataforma': self.plataforma,
            'user_id': self.user_id
        }

    @staticmethod
    def select_users(exam_id=None, source_id=None):
        users = RespostasLake.query.with_entities(RespostasLake.user_id)

        if exam_id is not None:
            users = users.filter(RespostasLake.contest_id == exam_id)

        if source_id is not None:
            users = users.filter(RespostasLake.source_id == source_id)

        users = users.distinct().order_by(RespostasLake.user_id).all()

        return [u[0] for u in users]

    @staticmethod
    def select_user_questions(user_id, exam_id=None, source_id=None):
        data = {"idUser": user_id}

        sql = """SELECT id, item_id, respondida_em, user_id, resposta_usuario
        FROM respostas_lake rl1
        WHERE user_id = :idUser"""

        if exam_id is not None:
            data["examId"] = exam_id
            sql += """ AND contest_id = :examId"""

        if source_id is not None:
            data["sourceId"] = source_id
            sql += """ AND source_id = :sourceId"""

        sql += """
        AND respondida_em = (
            SELECT MAX(respondida_em)
            FROM respostas_lake rl2
            WHERE rl2.item_id = rl1.item_id
                AND rl2.user_id = :idUser"""

        if exam_id is not None:
            sql += """ AND rl2.contest_id = :examId"""
        if source_id is not None:
            sql += """ AND rl2.source_id = :sourceId"""

        sql += """)
        ORDER BY item_id ASC;"""

        result = db.session.execute(db.text(sql), data)
        rows = result.fetchall()
        # pylint: disable=protected-access
        return [dict(row._mapping) for row in rows]

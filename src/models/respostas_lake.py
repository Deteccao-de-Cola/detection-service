from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from sqlalchemy import func
from sqlalchemy.orm import aliased

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
    def select_users(examId=None, sourceId=None):
        users = RespostasLake.query.with_entities(RespostasLake.user_id)
        
        if examId is not None:
            users = users.filter(RespostasLake.contest_id == examId)
        
        if examId is not None:
            users = users.filter(RespostasLake.source_id == sourceId)
        
        users = users.distinct().order_by(RespostasLake.user_id).all()
        
        return [u[0] for u in users]
    
    @staticmethod
    def select_user_questions(user_id, examId=None, sourceId=None):
        data = {"idUser": user_id}

        sql = """SELECT id, item_id, respondida_em, user_id, resposta_usuario
        FROM respostas_lake rl1
        WHERE user_id = :idUser"""
        
        if examId is not None:
            data["examId"] = examId
            sql += """ AND contest_id = :examId"""
        
        if sourceId is not None:
            data["sourceId"] = sourceId
            sql += """ AND source_id = :sourceId"""
        
        sql += """
        AND respondida_em = (
            SELECT MAX(respondida_em)
            FROM respostas_lake rl2
            WHERE rl2.item_id = rl1.item_id
                AND rl2.user_id = :idUser"""
        
        if examId is not None:
            sql += """ AND rl2.contest_id = :examId"""
        if sourceId is not None:
            sql += """ AND rl2.source_id = :sourceId"""
        
        sql += """)
        ORDER BY item_id ASC;"""

        result = db.session.execute(db.text(sql), data)
        rows = result.fetchall()

        return [dict(row._mapping) for row in rows]
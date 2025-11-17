"""
Modelos SQLAlchemy para regras e feedback do agente DIPAM COPILOT™.

Este módulo define a tabela agent_feedback_rules que armazena
regras e preferências aprendidas com feedbacks do Diretor e da equipe.
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, func
from src.dw.connection import Base


class AgentFeedbackRule(Base):
    """
    Tabela de regras de feedback do agente.
    
    Armazena regras e preferências aprendidas com feedbacks do Diretor
    e da equipe, permitindo que o agente "lembre" de decisões anteriores.
    
    Exemplo:
        Diretor diz: "Para análises de meta, exclua sempre a pasta verde"
        → Regra registrada: rule_scope='meta', condition_json={"carteira": "pasta_verde"},
          action_json={"excluir_dos_filtros": true}
    """
    __tablename__ = "agent_feedback_rules"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    owner_role = Column(String(50), nullable=False, index=True)  # 'diretor', 'supervisor', etc.
    owner_id = Column(String(100), nullable=True)  # ID opcional do usuário
    rule_scope = Column(String(50), nullable=False, index=True)  # 'meta', 'vendas', 'clientes_criticos', etc.
    condition_json = Column(Text, nullable=False)  # JSON com condição, ex.: {"carteira":"pasta_verde"}
    action_json = Column(Text, nullable=False)  # JSON com ação, ex.: {"excluir_dos_filtros":true}
    description = Column(Text, nullable=True)  # Texto humano: "Ignorar pasta verde em análises de meta"
    priority = Column(Integer, default=10, nullable=False)  # Para resolver conflitos (menor = maior prioridade)
    active = Column(Integer, default=1, nullable=False)  # 1=ativa, 0=desativada
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    def __repr__(self):
        return f"<AgentFeedbackRule(id={self.id}, owner_role='{self.owner_role}', rule_scope='{self.rule_scope}', active={self.active})>"
    
    def to_dict(self):
        """Converte para dicionário."""
        import json
        return {
            "id": self.id,
            "owner_role": self.owner_role,
            "owner_id": self.owner_id,
            "rule_scope": self.rule_scope,
            "condition_json": json.loads(self.condition_json) if self.condition_json else {},
            "action_json": json.loads(self.action_json) if self.action_json else {},
            "description": self.description,
            "priority": self.priority,
            "active": self.active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


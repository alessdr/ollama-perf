from database import db
from datetime import datetime

class TestRun(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    model_name = db.Column(db.String(100), nullable=False)
    prompt = db.Column(db.Text, nullable=False)
    response_time_ms = db.Column(db.Float, nullable=False)
    tokens_per_second = db.Column(db.Float, nullable=True)
    ttft_ms = db.Column(db.Float, nullable=True)
    prompt_tokens = db.Column(db.Integer, nullable=True)
    response_tokens = db.Column(db.Integer, nullable=True)
    response = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'model_name': self.model_name,
            'prompt': self.prompt,
            'response': self.response,
            'response_time_ms': self.response_time_ms,
            'tokens_per_second': self.tokens_per_second,
            'ttft_ms': self.ttft_ms,
            'prompt_tokens': self.prompt_tokens,
            'response_tokens': self.response_tokens,
            'created_at': self.created_at.isoformat()
        }

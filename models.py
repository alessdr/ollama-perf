from database import db
from datetime import datetime

class TestRun(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    model_name = db.Column(db.String(100), nullable=False)
    prompt = db.Column(db.Text, nullable=False)
    response_time_ms = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'model_name': self.model_name,
            'prompt': self.prompt,
            'response_time_ms': self.response_time_ms,
            'created_at': self.created_at.isoformat()
        }

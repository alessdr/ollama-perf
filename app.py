from flask import Flask, render_template, request, jsonify
from database import db
from models import TestRun
import ollama_utils
import os

app = Flask(__name__)

# Configure SQLite Database
basedir = os.path.abspath(os.path.dirname(__name__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'test_metrics.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

with app.app_context():
    db.create_all()

# --- View Routes ---

@app.route('/')
def dashboard():
    return render_template('dashboard.html')

@app.route('/models')
def models():
    return render_template('models.html')

@app.route('/test')
def test():
    return render_template('test.html')

# --- API Routes ---

@app.route('/api/models', methods=['GET'])
def api_get_models():
    all_models = ollama_utils.get_models()
    running_models = ollama_utils.get_running_models()
    
    models_data = []
    for m in all_models:
        m['status'] = "Running" if m['name'] in running_models else "Stopped"
        models_data.append(m)
    return jsonify({"models": models_data})

@app.route('/api/models/load', methods=['POST'])
def api_load_model():
    data = request.json
    model_name = data.get('model_name')
    if not model_name:
        return jsonify({"error": "Model name is required"}), 400
    
    success = ollama_utils.load_model(model_name)
    if success:
        return jsonify({"message": f"Model {model_name} loaded successfully"})
    else:
        return jsonify({"error": f"Failed to load model {model_name}"}), 500

@app.route('/api/models/unload', methods=['POST'])
def api_unload_model():
    data = request.json
    model_name = data.get('model_name')
    if not model_name:
        return jsonify({"error": "Model name is required"}), 400
    
    success = ollama_utils.unload_model(model_name)
    if success:
        return jsonify({"message": f"Model {model_name} unloaded successfully"})
    else:
        return jsonify({"error": f"Failed to unload model {model_name}"}), 500

@app.route('/api/test', methods=['POST'])
def api_run_test():
    data = request.json
    model_name = data.get('model_name')
    prompt = data.get('prompt')
    
    if not model_name or not prompt:
        return jsonify({"error": "Model name and prompt are required"}), 400
    
    result = ollama_utils.run_test(model_name, prompt)
    
    if result['success']:
        # Save to database
        test_run = TestRun(
            model_name=model_name,
            prompt=prompt,
            response_time_ms=result['total_duration_ms']
        )
        db.session.add(test_run)
        db.session.commit()
        
        return jsonify({
            "message": "Test completed successfully",
            "metrics": result,
            "saved_id": test_run.id
        })
    else:
        return jsonify({"error": result.get('error', 'Unknown error')}), 500

@app.route('/api/dashboard', methods=['GET'])
def api_dashboard_data():
    # Calculate average response time per model
    from sqlalchemy import func
    avg_times = db.session.query(
        TestRun.model_name,
        func.avg(TestRun.response_time_ms).label('avg_time'),
        func.count(TestRun.id).label('count')
    ).group_by(TestRun.model_name).all()
    
    # Get last 20 tests for history chart
    recent_tests = TestRun.query.order_by(TestRun.created_at.desc()).limit(20).all()
    
    data = {
        "averages": [{"model_name": row.model_name, "avg_time_ms": round(row.avg_time, 2), "count": row.count} for row in avg_times],
        "recent": [t.to_dict() for t in recent_tests]
    }
    return jsonify(data)

@app.route('/api/dashboard/clear', methods=['POST'])
def api_clear_dashboard():
    try:
        db.session.query(TestRun).delete()
        db.session.commit()
        return jsonify({"message": "Data cleared successfully"})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)

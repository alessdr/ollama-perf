from flask import Flask, render_template, request, jsonify, send_file
from database import db
from models import TestRun
import ollama_utils
import os
import base64
import io
from datetime import datetime
from sqlalchemy import func
from fpdf import FPDF
from fpdf.enums import XPos, YPos
import system_utils

app = Flask(__name__)

# Configure SQLite Database
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'test_metrics.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

with app.app_context():
    db.create_all()
    # Unload all models on startup to ensure a clean state
    print("Initializing system: Clearing VRAM resources...")
    ollama_utils.unload_all_models()

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

@app.route('/api/models/unload_all', methods=['POST'])
def api_unload_all_models():
    success = ollama_utils.unload_all_models()
    if success:
        return jsonify({"message": "All models unloaded successfully"})
    else:
        return jsonify({"error": "Failed to unload all models"}), 500

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
            response=result['response'],
            response_time_ms=result['total_duration_ms'],
            tokens_per_second=result['tokens_per_second'],
            ttft_ms=result['ttft_ms'],
            prompt_tokens=result['prompt_tokens'],
            response_tokens=result['response_tokens']
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
    # Calculate average response time and advanced metrics per model
    from sqlalchemy import func
    avg_metrics = db.session.query(
        TestRun.model_name,
        func.avg(TestRun.response_time_ms).label('avg_time'),
        func.avg(TestRun.tokens_per_second).label('avg_tps'),
        func.avg(TestRun.ttft_ms).label('avg_ttft'),
        func.count(TestRun.id).label('count')
    ).group_by(TestRun.model_name).all()
    
    # Get last 20 tests for history
    recent_tests = TestRun.query.order_by(TestRun.created_at.desc()).limit(20).all()
    
    data = {
        "averages": [{
            "model_name": row.model_name, 
            "avg_time_ms": round(row.avg_time, 2),
            "avg_tps": round(row.avg_tps, 2) if row.avg_tps else 0,
            "avg_ttft": round(row.avg_ttft, 2) if row.avg_ttft else 0,
            "count": row.count
        } for row in avg_metrics],
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

# --- PDF Report Generation ---

class PDFReport(FPDF):
    def header(self):
        # Signal Orange header background
        self.set_fill_color(249, 115, 22) 
        self.rect(0, 0, 210, 40, 'F')
        
        self.set_y(10)
        self.set_font('Helvetica', 'B', 22)
        self.set_text_color(255, 255, 255)
        self.cell(0, 10, 'Diagnostic Performance Report', align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        
        self.set_font('Helvetica', '', 10)
        self.set_text_color(255, 255, 255)
        self.cell(0, 10, f'Ollama Performance System v2.0 - Generated: {datetime.now().strftime("%d/%m/%Y %H:%M")}', align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(20)

    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(100, 116, 139)
        self.cell(0, 10, f'Technical Audit Document - Page {self.page_no()}', align='C', new_x=XPos.RIGHT, new_y=YPos.TOP)

@app.route('/api/report/generate', methods=['POST'])
def generate_report():
    try:
        data = request.json
        chart_latency = data.get('chart_latency')
        chart_speed = data.get('chart_speed')
        chart_ttft = data.get('chart_ttft')
        
        # Get data for the report
        averages = db.session.query(
            TestRun.model_name, 
            func.avg(TestRun.response_time_ms).label('avg_time'),
            func.avg(TestRun.tokens_per_second).label('avg_tps'),
            func.avg(TestRun.ttft_ms).label('avg_ttft')
        ).group_by(TestRun.model_name).order_by(func.avg(TestRun.response_time_ms)).all()
        
        if not averages:
            return jsonify({"error": "Nenhum dado de teste disponível para gerar o relatório."}), 400

        # Get latest context
        last_test = db.session.query(TestRun).order_by(TestRun.id.desc()).first()
        used_prompt = last_test.prompt if last_test else "N/A"

        # Get System Info
        sys_info = system_utils.get_system_info()
        sys_info_text = f"OS: {sys_info['os']['sistema']} {sys_info['os']['release']}, CPU: {sys_info['cpu']['modelo']}, RAM: {sys_info['ram']['total_gb']}GB"
        
        models_info = {m['name']: m for m in ollama_utils.get_models()}
        best_model_name = averages[0][0]
        
        summary_lines = [f"AMBIENTE: {sys_info_text}\n"]
        for row in averages:
            summary_lines.append(f"- {row.model_name}: {row.avg_time:.2f}ms, {row.avg_tps:.2f} tok/s, {row.avg_ttft:.2f}ms TTFT")
        
        analysis_text = ollama_utils.generate_analysis(best_model_name, "\n".join(summary_lines))
        
        pdf = PDFReport()
        pdf.add_page()
        
        # 1. TECHNICAL OVERVIEW (TABLE)
        pdf.set_font('Helvetica', 'B', 16)
        pdf.set_text_color(9, 9, 11)
        pdf.cell(0, 12, '1. Performance Metrics Overview', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(4)
        
        # Table Header
        pdf.set_fill_color(24, 24, 27)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font('Helvetica', 'B', 9)
        
        # Column Widths
        w = [50, 30, 35, 35, 40]
        headers = ['Model', 'Quant', 'Speed (t/s)', 'TTFT (ms)', 'Latency (avg)']
        
        for i in range(len(headers)):
            pdf.cell(w[i], 10, f' {headers[i]}', border=1, align='L' if i==0 else 'C', fill=True)
        pdf.ln()
        
        # Table Rows
        pdf.set_text_color(9, 9, 11)
        pdf.set_font('Helvetica', '', 9)
        fill = False
        for row in averages:
            m_name = row.model_name
            info = models_info.get(m_name, {})
            pdf.set_fill_color(244, 244, 245) if fill else pdf.set_fill_color(255, 255, 255)
            
            pdf.cell(w[0], 10, f' {m_name}', border=1, fill=True)
            pdf.cell(w[1], 10, f"{info.get('quantization', '-')}", border=1, align='C', fill=True)
            pdf.cell(w[2], 10, f"{row.avg_tps:.2f}", border=1, align='C', fill=True)
            pdf.cell(w[3], 10, f"{row.avg_ttft:.2f}", border=1, align='C', fill=True)
            pdf.cell(w[4], 10, f"{row.avg_time:.2f} ms", border=1, align='C', fill=True)
            pdf.ln()
            fill = not fill
            
        pdf.ln(10)

        # 2. DATA VISUALIZATION
        pdf.set_font('Helvetica', 'B', 16)
        pdf.set_text_color(24, 24, 27)
        pdf.cell(0, 12, '2. Diagnostic Visualizations', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_draw_color(249, 115, 22)
        pdf.line(pdf.get_x(), pdf.get_y(), pdf.get_x() + 40, pdf.get_y())
        pdf.ln(8)
        
        def add_chart(base64_str, title, subtitle):
            if not base64_str or not isinstance(base64_str, str) or "," not in base64_str:
                return
            try:
                # Section Title for Chart
                pdf.set_font('Helvetica', 'B', 12)
                pdf.set_text_color(249, 115, 22)
                pdf.cell(0, 8, title, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                pdf.set_font('Helvetica', 'I', 8)
                pdf.set_text_color(113, 113, 122)
                pdf.cell(0, 5, subtitle, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                pdf.ln(2)
                
                # Extract and decode image data
                encoded = base64_str.split(",", 1)[1]
                img_data = base64.b64decode(encoded)
                img_file = io.BytesIO(img_data)
                pdf.image(img_file, w=170)
                pdf.ln(12)
            except Exception as e:
                print(f"Chart Error ({title}): {e}")

        add_chart(chart_latency, "AVERAGE LATENCY", "Total response time per model (lower is better)")
        
        if chart_speed or chart_ttft:
            if pdf.get_y() > 200: pdf.add_page()
            add_chart(chart_speed, "THROUGHPUT SPEED", "Tokens generated per second (higher is better)")
            if pdf.get_y() > 200: pdf.add_page()
            add_chart(chart_ttft, "INITIAL RESPONSE (TTFT)", "Time to first token generation (lower is better)")

        # 3. AI ANALYSIS
        pdf.add_page()
        pdf.set_font('Helvetica', 'B', 16)
        pdf.set_text_color(24, 24, 27)
        pdf.cell(0, 12, '3. AI-Powered Technical Audit', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_draw_color(249, 115, 22)
        pdf.line(pdf.get_x(), pdf.get_y(), pdf.get_x() + 40, pdf.get_y())
        pdf.ln(8)
        
        pdf.set_font('Helvetica', '', 11)
        pdf.set_text_color(39, 39, 42)
        safe_analysis = analysis_text.encode('latin-1', 'replace').decode('latin-1')
        pdf.multi_cell(0, 7, safe_analysis, border=0, align='L')
        pdf.ln(15)

        # 4. HARDWARE ARCHITECTURE
        pdf.add_page()
        pdf.set_font('Helvetica', 'B', 16)
        pdf.set_text_color(24, 24, 27)
        pdf.cell(0, 12, '4. Hardware Architecture', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_draw_color(249, 115, 22)
        pdf.line(pdf.get_x(), pdf.get_y(), pdf.get_x() + 40, pdf.get_y())
        pdf.ln(8)
        
        # Grid layout for system info
        pdf.set_fill_color(244, 244, 245)
        pdf.set_draw_color(228, 228, 231)
        
        specs = [
            ("OPERATING SYSTEM", f"{sys_info['os']['sistema']} {sys_info['os']['release']}"),
            ("PROCESSOR (CPU)", sys_info['cpu']['modelo']),
            ("MEMORY (RAM)", f"{sys_info['ram']['total_gb']} GB Physical Memory"),
            ("ACCELERATOR (GPU)", ", ".join([g.get('nome', 'N/A') for g in sys_info['gpu']]) if sys_info['gpu'] else "CPU Inference Only")
        ]
        
        for label, val in specs:
            pdf.set_font('Helvetica', 'B', 8)
            pdf.set_text_color(113, 113, 122)
            pdf.cell(180, 6, label, ln=True)
            
            pdf.set_font('Helvetica', 'B', 10)
            pdf.set_text_color(24, 24, 27)
            pdf.cell(180, 10, f" {val}", border="L", fill=True, ln=True)
            pdf.ln(4)

        return send_file(
            io.BytesIO(pdf.output()),
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'signal_audit_{datetime.now().strftime("%Y%m%d_%H%M")}.pdf'
        )
        
    except Exception as e:
        print(f"Error generating PDF: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=8000)

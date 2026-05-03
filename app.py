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
        # Dark Blue header background
        self.set_fill_color(11, 17, 32) 
        self.rect(0, 0, 210, 40, 'F')
        
        self.set_y(10)
        self.set_font('Helvetica', 'B', 22)
        self.set_text_color(255, 255, 255)
        self.cell(0, 10, 'Ollama Performance Report', align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        
        self.set_font('Helvetica', '', 10)
        self.set_text_color(148, 163, 184)
        self.cell(0, 10, f'Gerado em: {datetime.now().strftime("%d/%m/%Y %H:%M:%S")}', align='C', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(20)

    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(100, 116, 139)
        self.cell(0, 10, f'Página {self.page_no()}', align='C', new_x=XPos.RIGHT, new_y=YPos.TOP)

@app.route('/api/report/generate', methods=['POST'])
def generate_report():
    try:
        data = request.json
        chart_image_base64 = data.get('chart_image')
        
        # Get data for the report
        averages = db.session.query(
            TestRun.model_name, 
            func.avg(TestRun.response_time_ms).label('avg_time'),
            func.avg(TestRun.tokens_per_second).label('avg_tps'),
            func.avg(TestRun.ttft_ms).label('avg_ttft')
        ).group_by(TestRun.model_name).order_by(func.avg(TestRun.response_time_ms)).all()
        
        if not averages:
            return jsonify({"error": "Nenhum dado de teste disponível para gerar o relatório."}), 400

        # Get the latest prompt used for context
        last_test = db.session.query(TestRun).order_by(TestRun.id.desc()).first()
        used_prompt = last_test.prompt if last_test else "Não disponível"

        # Identify best model for analysis (first in ordered list by time)
        best_model_name = averages[0][0]
        
        # Get System Info
        sys_info = system_utils.get_system_info()
        sys_info_text = f"OS: {sys_info['os']['sistema']} {sys_info['os']['release']}, CPU: {sys_info['cpu']['modelo']} ({sys_info['cpu']['nucleos_logicos']} vCores), RAM: {sys_info['ram']['total_gb']}GB"
        if sys_info['gpu']:
            sys_info_text += f", GPU: {sys_info['gpu'][0].get('nome', 'N/A')}"
        
        # Prepare data summary for AI with extra metadata
        models_info = {m['name']: m for m in ollama_utils.get_models()}
        summary_lines = [f"AMBIENTE DE TESTE: {sys_info_text}\n"]
        for row in averages:
            m_name = row.model_name
            t_avg = row.avg_time
            tps_avg = row.avg_tps
            ttft_avg = row.avg_ttft
            
            info = models_info.get(m_name, {})
            line = f"- {m_name}: Latencia {t_avg:.2f}ms, Speed {tps_avg:.2f} tok/s, TTFT {ttft_avg:.2f}ms"
            if info:
                line += f" (Size: {info.get('size_gb')}GB, Params: {info.get('parameter_size')}, Quant: {info.get('quantization')}, Best Use: {info.get('best_use')})"
            summary_lines.append(line)
        
        summary_text = "\n".join(summary_lines)
        
        # Generate AI analysis
        analysis_text = ollama_utils.generate_analysis(best_model_name, summary_text)
        
        # Create PDF
        pdf = PDFReport()
        pdf.add_page()
        
        # 1. Chart Section
        pdf.set_font('Helvetica', 'B', 16)
        pdf.set_text_color(30, 41, 59)
        pdf.cell(0, 12, '1. Comparativo de Performance', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(2)
        
        if chart_image_base64:
            try:
                header, encoded = chart_image_base64.split(",", 1)
                img_data = base64.b64decode(encoded)
                img_file = io.BytesIO(img_data)
                pdf.image(img_file, x=15, w=180)
                pdf.ln(10)
            except Exception as img_err:
                print(f"Error processing chart image: {img_err}")
                pdf.set_font('Helvetica', 'I', 10)
                pdf.cell(0, 10, '(Erro ao carregar o gráfico no PDF)', new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        # 2. Métricas Detalhadas (Tempo Médio)
        pdf.set_font('Helvetica', 'B', 16)
        pdf.set_text_color(30, 41, 59)
        pdf.cell(0, 12, '2. Métricas Detalhadas (Tempo Médio)', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(4)
        
        # Table Header
        pdf.set_fill_color(30, 41, 59)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font('Helvetica', 'B', 9)
        
        # Widths: Model (45), Quality (25), Speed (30), TTFT (30), Latency (50)
        col_widths = [45, 25, 30, 30, 50]
        
        pdf.cell(col_widths[0], 10, ' Modelo', border=1, align='L', fill=True)
        pdf.cell(col_widths[1], 10, 'Qualidade', border=1, align='C', fill=True)
        pdf.cell(col_widths[2], 10, 'Speed (tok/s)', border=1, align='C', fill=True)
        pdf.cell(col_widths[3], 10, 'TTFT (ms)', border=1, align='C', fill=True)
        pdf.cell(col_widths[4], 10, 'Latência Média ', border=1, align='R', fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        
        # Table Rows
        pdf.set_text_color(30, 41, 59)
        pdf.set_font('Helvetica', '', 8)
        fill = False
        for row in averages:
            m_name = row.model_name
            info = models_info.get(m_name, {})
            pdf.set_fill_color(248, 250, 252) if fill else pdf.set_fill_color(255, 255, 255)
            
            pdf.cell(col_widths[0], 10, f' {m_name}', border=1, align='L', fill=True)
            pdf.cell(col_widths[1], 10, f"{info.get('quantization', '-')}", border=1, align='C', fill=True)
            pdf.cell(col_widths[2], 10, f"{row.avg_tps:.2f}" if row.avg_tps else "0.00", border=1, align='C', fill=True)
            pdf.cell(col_widths[3], 10, f"{row.avg_ttft:.2f}" if row.avg_ttft else "0.00", border=1, align='C', fill=True)
            pdf.cell(col_widths[4], 10, f'{row.avg_time:.2f} ms ', border=1, align='R', fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            fill = not fill
        
        pdf.ln(10)

        # 3. Prompt Section
        pdf.set_font('Helvetica', 'B', 16)
        pdf.set_text_color(30, 41, 59)
        pdf.cell(0, 12, '3. Prompt Utilizado nos Testes', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(2)
        
        pdf.set_font('Helvetica', 'I', 11)
        pdf.set_text_color(71, 85, 105)
        safe_prompt = used_prompt.encode('latin-1', 'replace').decode('latin-1')
        pdf.multi_cell(0, 7, f'"{safe_prompt}"', border=0, align='L')
        pdf.ln(10)

        # 4. AI Analysis Section
        pdf.set_font('Helvetica', 'B', 16)
        pdf.set_text_color(30, 41, 59)
        pdf.cell(0, 12, '4. Considerações Técnicas (IA)', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(4)
        
        pdf.set_font('Helvetica', '', 11)
        pdf.set_fill_color(241, 245, 249)
        # Background box for AI analysis
        safe_text = analysis_text.encode('latin-1', 'replace').decode('latin-1')
        pdf.multi_cell(0, 7, safe_text, border=0, align='L', fill=True)
        pdf.ln(10)

        # 5. System Info Section
        pdf.set_font('Helvetica', 'B', 14)
        pdf.set_text_color(30, 41, 59)
        pdf.cell(0, 12, '5. Informações do Sistema', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(2)
        
        pdf.set_font('Helvetica', '', 10)
        pdf.set_text_color(71, 85, 105)
        
        # Grid layout for system info
        col_w = 90
        pdf.set_font('Helvetica', 'B', 10)
        pdf.cell(col_w, 7, 'Sistema Operacional:', new_x=XPos.RIGHT)
        pdf.set_font('Helvetica', '', 10)
        pdf.cell(col_w, 7, f"{sys_info['os']['sistema']} {sys_info['os']['release']} ({sys_info['os']['arquitetura']})", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        
        pdf.set_font('Helvetica', 'B', 10)
        pdf.cell(col_w, 7, 'Processador:', new_x=XPos.RIGHT)
        pdf.set_font('Helvetica', '', 10)
        pdf.cell(col_w, 7, f"{sys_info['cpu']['modelo']}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        
        pdf.set_font('Helvetica', 'B', 10)
        pdf.cell(col_w, 7, 'CPU Config:', new_x=XPos.RIGHT)
        pdf.set_font('Helvetica', '', 10)
        pdf.cell(col_w, 7, f"{sys_info['cpu']['nucleos_fisicos']} Cores / {sys_info['cpu']['nucleos_logicos']} Threads", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        
        pdf.set_font('Helvetica', 'B', 10)
        pdf.cell(col_w, 7, 'Memória RAM:', new_x=XPos.RIGHT)
        pdf.set_font('Helvetica', '', 10)
        pdf.cell(col_w, 7, f"{sys_info['ram']['total_gb']} GB", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        
        if sys_info['gpu']:
            gpu_names = ", ".join([g.get('nome') or g.get('info', 'N/A') for g in sys_info['gpu']])
            pdf.set_font('Helvetica', 'B', 10)
            pdf.cell(col_w, 7, 'Placa de Vídeo (GPU):', new_x=XPos.RIGHT)
            pdf.set_font('Helvetica', '', 10)
            pdf.cell(col_w, 7, gpu_names, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        
        pdf.set_font('Helvetica', 'B', 10)
        pdf.cell(col_w, 7, 'Hostname / IP:', new_x=XPos.RIGHT)
        pdf.set_font('Helvetica', '', 10)
        pdf.cell(col_w, 7, f"{sys_info['rede']['hostname']} ({sys_info['rede']['ip_local']})", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        
        # Output PDF
        pdf_bytes = pdf.output()
        
        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'ollama_performance_report_{datetime.now().strftime("%Y%m%d_%H%M")}.pdf'
        )
        
    except Exception as e:
        print(f"Error generating PDF: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=8000)

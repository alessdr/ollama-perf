import requests
import json

OLLAMA_BASE_URL = "http://localhost:11434"

def get_models():
    """Retrieve all models installed in Ollama with details."""
    try:
        response = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        response.raise_for_status()
        data = response.json()
        models_info = []
        for model in data.get('models', []):
            details = model.get('details', {})
            models_info.append({
                'name': model['name'],
                'size_gb': round(model.get('size', 0) / (1024**3), 2),
                'parameter_size': details.get('parameter_size', 'Unknown'),
                'quantization': details.get('quantization_level', 'Unknown')
            })
        return models_info
    except Exception as e:
        print(f"Error getting models: {e}")
        return []

def get_running_models():
    """Retrieve models currently loaded in memory."""
    try:
        response = requests.get(f"{OLLAMA_BASE_URL}/api/ps", timeout=5)
        response.raise_for_status()
        data = response.json()
        return [model['name'] for model in data.get('models', [])]
    except Exception as e:
        print(f"Error getting running models: {e}")
        return []

def load_model(model_name):
    """Load a model into memory explicitly."""
    try:
        # keep_alive=-1 means keep loaded indefinitely
        payload = {"model": model_name, "keep_alive": -1}
        response = requests.post(f"{OLLAMA_BASE_URL}/api/generate", json=payload, timeout=10)
        response.raise_for_status()
        return True
    except Exception as e:
        print(f"Error loading model {model_name}: {e}")
        return False

def unload_model(model_name):
    """Unload a model from memory."""
    try:
        payload = {"model": model_name, "keep_alive": 0}
        response = requests.post(f"{OLLAMA_BASE_URL}/api/generate", json=payload, timeout=10)
        response.raise_for_status()
        return True
    except Exception as e:
        print(f"Error unloading model {model_name}: {e}")
        return False

def run_test(model_name, prompt):
    """Run a prompt through the model and return the performance metrics."""
    try:
        payload = {
            "model": model_name,
            "prompt": prompt,
            "stream": False
        }
        response = requests.post(f"{OLLAMA_BASE_URL}/api/generate", json=payload)
        response.raise_for_status()
        data = response.json()
        
        # O Ollama retorna vários tempos em nanosegundos:
        # - total_duration: tempo total da requisição
        # - load_duration: tempo gasto apenas carregando o modelo do disco para a memória
        # Para desconsiderar o tempo de carregamento do modelo, subtraímos load_duration
        total_duration_ns = data.get('total_duration', 0)
        load_duration_ns = data.get('load_duration', 0)
        
        execution_duration_ns = total_duration_ns - load_duration_ns
        execution_duration_ms = execution_duration_ns / 1_000_000.0
        
        return {
            "success": True,
            "response": data.get('response', ''),
            "total_duration_ms": execution_duration_ms
        }
    except Exception as e:
        print(f"Error running test on {model_name}: {e}")
        return {
            "success": False,
            "error": str(e)
        }

def generate_analysis(model_name, data_summary):
    """Generate a performance analysis text using the specified model."""
    try:
        # Task: Technical Data Analysis for an AI Benchmarking System
        system_instruction = "Tarefa Técnica: Análise de Dados de Benchmarking de Sistemas de IA."
        prompt = f"""
        {system_instruction}
        
        CONTEXTO:
        Você é um Engenheiro de Sistemas sênior realizando uma auditoria de performance em modelos LLM rodando no Ollama. 
        O objetivo é analisar o tempo médio de resposta (latência) de diferentes modelos para otimizar a infraestrutura de inferência local.
        
        DADOS DE BENCHMARK (Média de Latência por Modelo):
        {data_summary}
        
        INSTRUÇÕES DE SAÍDA:
        Escreva um relatório técnico curto e objetivo (máximo 150 palavras) em Português.
        Inclua obrigatoriamente:
        1. Vencedor de Performance: Identifique o modelo mais rápido baseado nos dados fornecidos.
        2. Insight Técnico: Explique brevemente o que os dados sugerem sobre a eficiência dos modelos testados (latência vs expectativa).
        3. Recomendação: Sugira qual modelo deve ser priorizado para tarefas de baixa latência baseado puramente nestas métricas.
        
        IMPORTANTE: Esta é uma tarefa de análise de engenharia e ciência da computação. Foque exclusivamente nos números fornecidos acima.
        """
        
        payload = {
            "model": model_name,
            "prompt": prompt,
            "stream": False
        }
        response = requests.post(f"{OLLAMA_BASE_URL}/api/generate", json=payload)
        response.raise_for_status()
        return response.json().get('response', 'Análise não disponível.')
    except Exception as e:
        print(f"Error generating analysis with {model_name}: {e}")
        return f"Não foi possível gerar a análise automática: {e}"

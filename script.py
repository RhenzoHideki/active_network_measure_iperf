#!/usr/bin/env python3
import subprocess
import os
import time
import csv
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
from scipy import stats

# Configurações do cenário
SCENARIO_ID = "i1666"
TOPOLOGY_FILE = "scenario.imn"
BANDWIDTH = 100000000  # 100 Mbps

# Parâmetros da execução conforme cenário
BUFFER_SIZES = {
    "64KB": 65536,    # 64 KB (janela efetiva 128 KB)
    "208KB": 212992   # 208 KB (janela efetiva 416 KB)
}

DELAYS = {
    "10ms": 10,       # 10ms (RTT esperado 20ms) 
    "100ms": 100      # 100ms (RTT esperado 200ms)
}

REPETICOES = 8        # Número de repetições para cada configuração
CARGA = "100M"        # Carga fixa para o iperf
CONFIDENCE_LEVEL = 0.95  # Nível de confiança para intervalo (95%)

# Criar diretórios para saída
os.makedirs("./logs", exist_ok=True)
os.makedirs("./resultados", exist_ok=True)

# Arquivos de saída com timestamp
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_file = f"./logs/experimento_{timestamp}.log"
results_file = f"./resultados/resultados_{timestamp}.csv"
summary_file = f"./resultados/sumario_{timestamp}.csv"
plot_file = f"./resultados/grafico_{timestamp}.png"

# Inicializar arquivo de resultados
with open(results_file, 'w', newline='') as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(['Execucao', 'Buffer', 'Delay', 'Repeticao', 'Vazao (Mbps)'])

def log(message):
    """Registrar mensagens tanto no console quanto no arquivo de log"""
    print(message)
    with open(log_file, 'a') as f:
        f.write(f"{message}\n")

def execute_command(command):
    """Executar comando no sistema e capturar saída"""
    log(f"Executando: {command}")
    try:
        result = subprocess.run(command, shell=True, check=True, 
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                               text=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        log(f"Erro ao executar comando: {e}")
        log(f"Saída de erro: {e.stderr}")
        return None

def start_imunes():
    """Iniciar simulação IMUNES"""
    log("\n" + "="*60)
    log(f"Iniciando simulação IMUNES com ID: {SCENARIO_ID}")
    log(f"Usando arquivo de topologia: {TOPOLOGY_FILE}")
    execute_command(f"sudo imunes -b -e {SCENARIO_ID} {TOPOLOGY_FILE}")
    time.sleep(5)  # Aguardar inicialização completa
    log("Simulação iniciada com sucesso")

def stop_imunes():
    """Parar simulação IMUNES"""
    log("\n" + "="*60)
    log(f"Parando simulação IMUNES com ID: {SCENARIO_ID}")
    execute_command(f"sudo imunes -b -e {SCENARIO_ID} -c")
    log("Simulação encerrada")

def configure_links(delay_ms):
    """Configurar links com atraso especificado (em ms)"""
    log("\n" + "="*60)
    log(f"Configurando links com atraso de {delay_ms}ms (RTT esperado: {delay_ms*2}ms)")
    
    # Converter de ms para μs (como esperado pelo IMUNES)
    delay_us = delay_ms * 1000
    
    # Configurar todos os links na topologia
    links = [
        f"router1:pc1@{SCENARIO_ID}",
        f"router1:pc3@{SCENARIO_ID}",
        f"router2:pc2@{SCENARIO_ID}",
        f"router2:pc4@{SCENARIO_ID}",
        f"router2:router1@{SCENARIO_ID}"
    ]
    
    for link in links:
        execute_command(f"sudo vlink -bw {BANDWIDTH} -dly {delay_us} {link}")
    
    # Verificar configuração
    log("Verificando configuração dos links:")
    for link in links:
        execute_command(f"sudo vlink -s {link}")

def start_iperf_server():
    """Iniciar servidor iperf"""
    log("\n" + "="*60)
    log("Iniciando servidor iperf...")
    execute_command(f"sudo himage pc2@{SCENARIO_ID} iperf -s &> /dev/null &")
    time.sleep(2)  # Aguardar inicialização do servidor
    log("Servidor iperf iniciado")

def run_iperf_test(buffer_size):
    """Executar teste iperf com buffer de envio especificado"""
    log("\n" + "="*60)
    log(f"Executando teste iperf com buffer de envio: {buffer_size} bytes")
    
    # Endereço IP do servidor (pc2)
    server_ip = "10.0.3.20"  # Ajuste conforme sua topologia
    
    # Comando iperf com parâmetros especificados
    cmd = f"sudo himage pc1@{SCENARIO_ID} iperf -c {server_ip} -n {CARGA} -w {buffer_size} -i 1 -v"
    output = execute_command(cmd)
    
    # Analisar saída para extrair vazão
    if output:
        lines = output.strip().split('\n')
        for line in lines:
            if "Mbits/sec" in line and "sender" in line:
                parts = line.split()
                for i, part in enumerate(parts):
                    if "Mbits/sec" in part:
                        try:
                            vazao = float(parts[i-1])
                            log(f"Vazão medida: {vazao} Mbits/sec")
                            return vazao
                        except (ValueError, IndexError):
                            log("Erro ao analisar valor de vazão")
    
    log("Não foi possível obter vazão do teste")
    return None

def calculate_statistics(results):
    """Calcular estatísticas (média e intervalo de confiança)"""
    mean = np.mean(results)
    
    # Intervalo de confiança de 95%
    if len(results) > 1:
        sem = stats.sem(results)  # Erro padrão da média
        ci = sem * stats.t.ppf((1 + CONFIDENCE_LEVEL) / 2, len(results) - 1)
        return mean, ci
    else:
        return mean, 0

def generate_plot(summary_data):
    """Gerar gráfico de barras com intervalos de confiança"""
    log("\n" + "="*60)
    log("Gerando gráfico de resultados...")
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Configurações do gráfico
    bar_width = 0.35
    opacity = 0.8
    
    # Posições das barras no eixo x
    indices = np.arange(len(summary_data))
    
    # Extrair dados para o gráfico
    labels = [f"{data['buffer']} / {data['delay']}" for data in summary_data]
    means = [data['mean'] for data in summary_data]
    errors = [data['ci'] for data in summary_data]
    
    # Criar barras
    bars = ax.bar(indices, means, bar_width,
                  alpha=opacity, color='b',
                  yerr=errors, capsize=5,
                  label='Vazão Média (Mbps)')
    
    # Configurar eixos e legendas
    ax.set_xlabel('Configuração (Buffer / Delay)')
    ax.set_ylabel('Vazão (Mbps)')
    ax.set_title('Vazão TCP por Configuração com Intervalo de Confiança (95%)')
    ax.set_xticks(indices)
    ax.set_xticklabels(labels, rotation=45)
    ax.legend()
    
    plt.tight_layout()
    plt.savefig(plot_file)
    log(f"Gráfico salvo em: {plot_file}")

def main():
    """Função principal para execução do experimento"""
    log("="*60)
    log("EXPERIMENTO DE AVALIAÇÃO DE DESEMPENHO TCP")
    log("="*60)
    log(f"Data e hora de início: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    
    # Lista para armazenar resultados para análise
    all_results = []
    
    try:
        # Iniciar simulação IMUNES
        start_imunes()
        
        # Iniciar servidor iperf
        start_iperf_server()
        
        # Executar as quatro combinações de fatores
        execution_id = 1
        
        for buffer_name, buffer_size in BUFFER_SIZES.items():
            for delay_name, delay_ms in DELAYS.items():
                
                # Configurar links com atraso especificado
                configure_links(delay_ms)
                
                log("\n" + "="*60)
                log(f"EXECUÇÃO {execution_id}: Buffer={buffer_name}, Delay={delay_name}")
                
                # Lista para armazenar resultados desta configuração
                config_results = []
                
                # Executar repetições
                for rep in range(1, REPETICOES + 1):
                    log(f"\nRepetição {rep}/{REPETICOES}")
                    
                    # Executar teste e obter vazão
                    vazao = run_iperf_test(buffer_size)
                    
                    if vazao is not None:
                        # Registrar resultado individual
                        with open(results_file, 'a', newline='') as csvfile:
                            writer = csv.writer(csvfile)
                            writer.writerow([execution_id, buffer_name, delay_name, rep, vazao])
                        
                        config_results.append(vazao)
                    
                    time.sleep(2)  # Pequena pausa entre repetições
                
                # Calcular estatísticas para esta configuração
                if config_results:
                    mean, ci = calculate_statistics(config_results)
                    all_results.append({
                        'execution': execution_id,
                        'buffer': buffer_name,
                        'delay': delay_name,
                        'mean': mean,
                        'ci': ci,
                        'min': min(config_results),
                        'max': max(config_results)
                    })
                    
                    log(f"Configuração {execution_id} concluída. Vazão média: {mean:.2f} Mbps, IC95%: ±{ci:.2f}")
                
                execution_id += 1
        
        # Gerar resumo estatístico
        with open(summary_file, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['Execucao', 'Buffer', 'Delay', 'Media (Mbps)', 'IC95% (±)', 'Min', 'Max'])
            
            for result in all_results:
                writer.writerow([
                    result['execution'],
                    result['buffer'],
                    result['delay'],
                    f"{result['mean']:.2f}",
                    f"{result['ci']:.2f}",
                    f"{result['min']:.2f}",
                    f"{result['max']:.2f}"
                ])
        
        log(f"Resumo estatístico salvo em: {summary_file}")
        
        # Gerar gráfico
        generate_plot(all_results)
        
        # Análise de efeitos principais e interação
        log("\n" + "="*60)
        log("ANÁLISE DE EFEITOS:")
        
        # Organizar resultados para análise
        buffer_low = [r['mean'] for r in all_results if r['buffer'] == "64KB"]
        buffer_high = [r['mean'] for r in all_results if r['buffer'] == "208KB"]
        delay_low = [r['mean'] for r in all_results if r['delay'] == "10ms"]
        delay_high = [r['mean'] for r in all_results if r['delay'] == "100ms"]
        
        # Calcular efeitos principais
        buffer_effect = np.mean(buffer_high) - np.mean(buffer_low)
        delay_effect = np.mean(delay_low) - np.mean(delay_high)
        
        log(f"Efeito do Buffer (208KB vs 64KB): {buffer_effect:.2f} Mbps")
        log(f"Efeito do Delay (10ms vs 100ms): {delay_effect:.2f} Mbps")
        
        # Análise de interação (simplificada)
        buffer_low_delay_low = next((r['mean'] for r in all_results if r['buffer'] == "64KB" and r['delay'] == "10ms"), 0)
        buffer_low_delay_high = next((r['mean'] for r in all_results if r['buffer'] == "64KB" and r['delay'] == "100ms"), 0)
        buffer_high_delay_low = next((r['mean'] for r in all_results if r['buffer'] == "208KB" and r['delay'] == "10ms"), 0)
        buffer_high_delay_high = next((r['mean'] for r in all_results if r['buffer'] == "208KB" and r['delay'] == "100ms"), 0)
        
        effect_low_buffer = buffer_low_delay_low - buffer_low_delay_high
        effect_high_buffer = buffer_high_delay_low - buffer_high_delay_high
        
        log(f"Efeito do Delay com Buffer Baixo: {effect_low_buffer:.2f} Mbps")
        log(f"Efeito do Delay com Buffer Alto: {effect_high_buffer:.2f} Mbps")
        
        if abs(effect_low_buffer - effect_high_buffer) > 5:  # Limiar arbitrário
            log("CONCLUSÃO: Há evidência de interação entre os fatores.")
        else:
            log("CONCLUSÃO: Não há forte evidência de interação entre os fatores.")
        
    except Exception as e:
        log(f"Erro durante a execução do experimento: {str(e)}")
    finally:
        # Garantir que a simulação seja encerrada
        stop_imunes()
        
        log("\n" + "="*60)
        log(f"Experimento concluído em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        log(f"Log completo salvo em: {log_file}")
        log(f"Resultados individuais salvos em: {results_file}")
        log(f"Resumo estatístico salvo em: {summary_file}")
        log(f"Gráfico de resultados salvo em: {plot_file}")

if __name__ == "__main__":
    main()
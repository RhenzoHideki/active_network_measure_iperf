#!/usr/bin/env python3
import subprocess
import os
import time
import csv
from datetime import datetime

# Configurações do cenário
SCENARIO_ID = "i1666"
TOPOLOGY_FILE = "scenario.imn"
BANDWIDTH = 100000000  # 100 Mbps

# Parâmetros da execução
BUFFER_SIZES = [65536, 212992]  # 64 KB, 208 KB
DELAYS = [5000, 50000]  # 5ms (10ms RTT), 50ms (100ms RTT)
REPETICOES = 5  # Número de repetições para cada configuração
FLUXES = 1  # Número de fluxos paralelos

# Criar diretório para logs e resultados
os.makedirs("./logs", exist_ok=True)
os.makedirs("./resultados", exist_ok=True)

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_filename = f"./logs/experimento_{timestamp}.log"
results_filename = f"./resultados/resultados_{timestamp}.csv"

# Configurar arquivo de resultados
with open(results_filename, 'w', newline='') as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(['Execucao', 'Buffer (KB)', 'RTT (ms)', 'Vazao (Mbps)', 'Repeticao'])

def log_message(message):
    """Registrar mensagens no log e exibir na tela"""
    print(message)
    with open(log_filename, 'a') as logfile:
        logfile.write(f"{message}\n")

def execute_command(command):
    """Executar comando e registrar saída"""
    log_message(f"Executando: {command}")
    try:
        result = subprocess.run(command, shell=True, check=True, 
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                              text=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        log_message(f"Erro ao executar comando: {e}")
        log_message(f"Saída de erro: {e.stderr}")
        return None

def start_imunes():
    """Iniciar simulação IMUNES"""
    log_message("\n" + "="*60)
    log_message(f"Iniciando simulação IMUNES com ID: {SCENARIO_ID}")
    log_message(f"Usando arquivo de topologia: {TOPOLOGY_FILE}")
    execute_command(f"sudo imunes -b -e {SCENARIO_ID} {TOPOLOGY_FILE}")
    time.sleep(5)  # Aguardar inicialização completa
    log_message("Simulação iniciada com sucesso")

def stop_imunes():
    """Parar simulação IMUNES"""
    log_message("\n" + "="*60)
    log_message(f"Parando simulação IMUNES com ID: {SCENARIO_ID}")
    execute_command(f"sudo imunes -b -e {SCENARIO_ID} -c")
    log_message("Simulação encerrada")

def configure_links(delay):
    """Configurar links com largura de banda e atraso específicos"""
    log_message("\n" + "="*60)
    log_message(f"Configurando links com atraso de {delay}μs (RTT: {delay*2/1000}ms)")
    
    # Configurar links
    links = [
        f"router1:pc1@{SCENARIO_ID}",
        f"router1:pc3@{SCENARIO_ID}",
        f"router2:pc2@{SCENARIO_ID}",
        f"router2:pc4@{SCENARIO_ID}",
        f"router2:router1@{SCENARIO_ID}"
    ]
    
    for link in links:
        execute_command(f"sudo vlink -bw {BANDWIDTH} -dly {delay} {link}")
    
    # Verificar status (opcional)
    log_message("Status dos links:")
    for link in links:
        status = execute_command(f"sudo vlink -s {link}")
        log_message(f"Link {link}: {status.strip() if status else 'Status não disponível'}")

def start_iperf_servers():
    """Iniciar servidores iperf"""
    log_message("\n" + "="*60)
    log_message("Iniciando servidores iperf...")
    execute_command(f"sudo himage pc2@{SCENARIO_ID} iperf -s &> /dev/null &")
    execute_command(f"sudo himage pc4@{SCENARIO_ID} iperf -s &> /dev/null &")
    log_message("Servidores iperf iniciados")

def start_background_traffic():
    """Iniciar tráfego UDP de fundo"""
    log_message("\n" + "="*60)
    log_message("Iniciando tráfego UDP de fundo...")
    execute_command(f"sudo himage pc1@{SCENARIO_ID} iperf -c 10.0.3.20 -u -t 100000 -b 10M &> /dev/null &")
    log_message("Tráfego de fundo iniciado")

def run_iperf_test(buffer_size, repeticao, execucao_num):
    """Executar teste iperf e retornar resultados"""
    log_message("\n" + "="*60)
    log_message(f"Executando teste TCP entre PC3 e PC4 (Buffer: {buffer_size/1024}KB, Repetição: {repeticao+1})")
    
    # Comando iperf com buffer de envio específico
    cmd = f"sudo himage pc3@{SCENARIO_ID} iperf -c 10.0.4.20 -n 100M -P {FLUXES} -i 1 -w {buffer_size}"
    output = execute_command(cmd)
    
    # Analisar saída para obter vazão
    if output:
        lines = output.strip().split('\n')
        last_line = lines[-1]
        if "Mbits/sec" in last_line:
            # Extrair valor de vazão
            parts = last_line.split()
            for i, part in enumerate(parts):
                if "Mbits/sec" in parts[i]:
                    try:
                        vazao = float(parts[i-1])
                        log_message(f"Vazão medida: {vazao} Mbits/sec")
                        return vazao
                    except (ValueError, IndexError):
                        log_message("Erro ao analisar a vazão")
    
    log_message("Não foi possível obter a vazão")
    return None

def main():
    """Função principal para execução dos experimentos"""
    log_message("="*60)
    log_message("EXPERIMENTO DE AVALIAÇÃO DE DESEMPENHO TCP COM IMUNES")
    log_message("="*60)
    
    try:
        # Iniciar simulação
        start_imunes()
        
        # Iniciar servidores iperf
        start_iperf_servers()
        
        # Iniciar tráfego de fundo
        start_background_traffic()
        
        execucao_num = 1
        
        # Para cada combinação de buffer e atraso
        for buffer_size in BUFFER_SIZES:
            for delay in DELAYS:
                # Configurar links com o atraso apropriado
                configure_links(delay)
                
                buffer_kb = buffer_size / 1024
                rtt_ms = delay * 2 / 1000
                
                log_message(f"\n{'='*60}")
                log_message(f"EXECUÇÃO {execucao_num}: Buffer={buffer_kb}KB, RTT={rtt_ms}ms")
                
                # Executar repetições
                for rep in range(REPETICOES):
                    vazao = run_iperf_test(buffer_size, rep, execucao_num)
                    
                    # Registrar resultados
                    if vazao is not None:
                        with open(results_filename, 'a', newline='') as csvfile:
                            writer = csv.writer(csvfile)
                            writer.writerow([execucao_num, buffer_kb, rtt_ms, vazao, rep+1])
                
                execucao_num += 1
                
    except Exception as e:
        log_message(f"Erro durante a execução do experimento: {e}")
    finally:
        # Garantir que a simulação seja encerrada mesmo em caso de erro
        stop_imunes()
        log_message("Experimento concluído.")
        log_message(f"Resultados salvos em {results_filename}")

if __name__ == "__main__":
    main()
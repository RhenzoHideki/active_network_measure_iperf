import subprocess
import time
import os
import re

# Configurações
topologia = "cenario1.imn"
buffer_sizes = ["64K", "208K"]
delays = [10, 100]  # em ms
repeticoes = 8

pc_cliente = "pc2"
pc_servidor = "pc4"
ip_servidor = "10.0.4.20"
enlace = "router2:pc2"

saida_dir = "resultados_iperf"
os.makedirs(saida_dir, exist_ok=True)

# ========== Funções Auxiliares ==========

def iniciar_imunes(topologia):
    print(f"Iniciando IMUNES com topologia {topologia}...")
    resultado = subprocess.run(["sudo", "imunes", "-b", topologia], capture_output=True, text=True)
    if resultado.returncode != 0:
        raise RuntimeError(f"Erro ao iniciar IMUNES: {resultado.stderr}")
    
    match = re.search(r"Experiment ID\s*=\s*(\S+)", resultado.stdout)
    if not match:
        raise RuntimeError("Não foi possível extrair o ID do cenário (eid)")
    
    cenario_id = match.group(1)
    print(f"Cenário iniciado com ID: {cenario_id}")
    time.sleep(2)
    return cenario_id

def configurar_delay(delay, enlace, cenario_id):
    microssegundos = delay * 1000
    print(f"Configurando delay de {delay}ms no enlace {enlace}...")
    subprocess.run(["sudo", "vlink", "-dly", str(microssegundos), f"{enlace}@{cenario_id}"])

def iniciar_servidor_iperf(pc_servidor, cenario_id):
    return subprocess.Popen(
        ["sudo", "himage", f"{pc_servidor}@{cenario_id}", "iperf", "-s"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

def parar_servidor_iperf(pc_servidor, cenario_id, processo):
    processo.terminate()
    subprocess.run(["sudo", "himage", f"{pc_servidor}@{cenario_id}", "pkill", "-f", "iperf"])

def executar_teste(buffer, delay, repeticao, cenario_id):
    nome_arquivo = f"iperf_buffer{buffer}_delay{delay}_rep{repeticao+1}.txt"
    caminho_saida = os.path.join(saida_dir, nome_arquivo)

    servidor = iniciar_servidor_iperf(pc_servidor, cenario_id)
    time.sleep(1)

    print(f"Executando cliente iperf: buffer={buffer}, delay={delay}ms, repetição {repeticao+1}")
    with open(caminho_saida, "w") as f:
        subprocess.run([
            "sudo", "himage", f"{pc_cliente}@{cenario_id}",
            "iperf", "-c", ip_servidor, "-n", "100M", "-w", buffer, "-y", "C"
        ], stdout=f, stderr=subprocess.DEVNULL)

    parar_servidor_iperf(pc_servidor, cenario_id, servidor)
    time.sleep(1)

def finalizar_imunes(cenario_id):
    print("Finalizando o cenário IMUNES...")
    subprocess.run(["sudo", "imunes", "-e", cenario_id])
    print("Cenário finalizado.")

# ========== Funções para Análise ==========

def parse_iperf_output(file_path):
    try:
        with open(file_path, 'r') as f:
            lines = f.readlines()
        for line in reversed(lines):
            if line.strip() and not line.startswith("#"):
                parts = line.strip().split(',')
                if len(parts) > 8:
                    return float(parts[8])
    except Exception as e:
        print(f"Erro ao processar {file_path}: {e}")
    return None

def calcular_intervalo_confianca(dados):
    media = np.mean(dados)
    n = len(dados)
    if n < 2:
        return (media, media)
    sem = stats.sem(dados)
    intervalo = stats.t.interval(0.95, n - 1, loc=media, scale=sem)
    return intervalo

# ========== Execução Principal ==========

cenario_id = None
try:
    cenario_id = iniciar_imunes(topologia)

    for buffer in buffer_sizes:
        for delay in delays:
            configurar_delay(delay, enlace, cenario_id)
            for i in range(repeticoes):
                executar_teste(buffer, delay, i, cenario_id)

except Exception as e:
    print(f"Erro durante execução: {e}")

finally:
    if cenario_id:
        finalizar_imunes(cenario_id)

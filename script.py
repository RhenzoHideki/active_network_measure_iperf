import subprocess
import time
import os
import sys

# Definições do cenário e experimentos
topologia = "cenario1.imn"
buffer_sizes = ["64K", "208K"]
delays = [10, 100]
repeticoes = 8

# Configuração das máquinas e parâmetros da rede
pc_cliente = "pc2"
pc_servidor = "pc4"
ip_servidor = "10.0.4.20"  # IP do pc4
enlace = "router1:router2"  # Link entre os roteadores

# Cria diretório para resultados
saida_dir = "resultados_iperf"
os.makedirs(saida_dir, exist_ok=True)

# Inicia o IMUNES com o cenário especificado
print(f"Iniciando IMUNES com topologia {topologia}...")
resultado = subprocess.run(["sudo", "imunes", "-b", topologia], capture_output=True, text=True)

# Extrair ID do cenário da saída
cenario_id = resultado.stdout.strip().split()[-1]
print(f"Cenário iniciado com ID: {cenario_id}")

print("Aguardando 2 segundos para o cenário carregar completamente...")
time.sleep(2)

try:
    # Início das execuções
    for buffer in buffer_sizes:
        for delay in delays:
            print(f"\n=== Testando Buffer: {buffer}, Delay: {delay}ms ===")
            
            # Ajusta o delay no link entre os roteadores
            print(f"Configurando delay de {delay}ms no enlace {enlace}...")
            subprocess.run(["sudo", "vlink", "-dly", str(delay*1000), f"{enlace}@{cenario_id}"])
            time.sleep(1)
            
            for i in range(repeticoes):
                print(f"\nExecução {i+1}/{repeticoes}")
                
                # Inicia o servidor iperf em pc4
                print(f"Iniciando servidor iperf em {pc_servidor}...")
                servidor = subprocess.Popen(
                    ["sudo", "himage", f"{pc_servidor}@{cenario_id}", "iperf", "-s"], 
                    stdout=subprocess.DEVNULL, 
                    stderr=subprocess.DEVNULL
                )
                time.sleep(2)
                
                # Nome do arquivo de saída
                nome_arquivo = f"iperf_buffer{buffer}_delay{delay}_rep{i+1}.txt"
                caminho_saida = os.path.join(saida_dir, nome_arquivo)
                
                # Executa o cliente iperf em pc2 e salva resultado
                print(f"Executando cliente iperf em {pc_cliente} e salvando resultado em {nome_arquivo}...\n")
                with open(caminho_saida, "w") as f:
                    subprocess.run([
                        "sudo", "himage", f"{pc_cliente}@{cenario_id}",
                        "iperf", "-c", ip_servidor, "-n", "100M", "-w", buffer, "-i", "1"
                    ], stdout=f)
                
                # Finaliza servidor iperf
                print("Finalizando servidor iperfs...\n")
                servidor.terminate()
                subprocess.run(
                    ["sudo", "himage", f"{pc_servidor}@{cenario_id}", "pkill", "-f", "iperf"],
                    stdout=subprocess.DEVNULL, 
                    stderr=subprocess.DEVNULL
                )
                time.sleep(1)

except Exception as e:
    print(f"Erro durante a execução: {e}\n")

finally:
    # Finaliza o IMUNES
    print("\nFinalizando cenário no IMUNES...")
    subprocess.run(["sudo", "imunes", "-e", cenario_id])
    print("Teste concluído.")
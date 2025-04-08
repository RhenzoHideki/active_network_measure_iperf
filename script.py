#!/usr/bin/env python3
import subprocess
import time
import os

# Parâmetros do cenário
SCENARIO_ID = "i1666"
TOPOLOGY_FILE = "scenario.imn"
BANDWIDTH = "100000000"  # 100 Mbps

# Configurações dos fatores:
# Buffers: argumento para o iperf e rótulo descritivo
buffers = [
    ("64K", "64KB"),   # Nível baixo: 64K -> janela efetiva ~128KB
    ("208K", "208KB")  # Nível alto: 208K -> janela efetiva ~416KB
]
# Atrasos (em microssegundos) e rótulo descritivo.
# 10 ms = 10,000 µs e 100 ms = 100,000 µs.
delays = [
    (10000, "10ms"),    # Nível baixo: RTT de ~20ms
    (100000, "100ms")   # Nível alto: RTT de ~200ms
]

# Número de repetições para cada combinação
repeticoes = 8

# Criação do diretório de logs (se não existir)
os.makedirs("./log", exist_ok=True)

# Loop para as combinações experimentais
for buf_arg, buf_desc in buffers:
    for delay_val, delay_desc in delays:
        exp_id = f"Exp_buf{buf_desc}_delay{delay_desc}"
        print(f"Executando {exp_id} ...")
        for rep in range(1, repeticoes + 1):
            print(f"  Replicação {rep}:")

            # Aplicar a configuração de atraso usando vlink
            # Ajusta o link do router2 para o nó pc4 no cenário
            cmd_vlink = f"sudo vlink -bw {BANDWIDTH} -dly {delay_val} router2:pc4@{SCENARIO_ID}"
            print(f"    Configurando link: {cmd_vlink}")
            subprocess.run(cmd_vlink, shell=True)
            time.sleep(1)  # Aguarda a estabilização da configuração

            # Executar o teste iperf no modo TCP
            # O teste é executado do nó pc3 para o ip do servidor (neste exemplo, 10.0.4.20)
            cmd_iperf = (
                f"sudo himage pc3@{SCENARIO_ID} iperf -c 10.0.4.20 "
                f"-n 100M -P 1 -i 1 -w {buf_arg}"
            )
            print(f"    Executando teste: {cmd_iperf}")
            # Nome do arquivo de saída
            log_file = f"log/{exp_id}_rep{rep}.txt"
            with open(log_file, "w") as f:
                subprocess.run(cmd_iperf, shell=True, stdout=f, stderr=subprocess.STDOUT)
            time.sleep(2)  # Pausa entre as repetições

print("Todos os testes foram concluídos.")

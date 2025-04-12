import os
import csv

saida_dir = "resultados_iperf"

def parse_iperf_output(file_path):
    with open(file_path, 'r') as f:
        lines = f.readlines()

    for line in reversed(lines):
        if "," in line:
            try:
                throughput = float(line.strip().split(",")[8])
                return throughput
            except:
                continue
    return None

def salvar_resultados_csv(diretorio, arquivo_saida="resultados_consolidados.csv"):
    resultados = []
    for arquivo in os.listdir(diretorio):
        if arquivo.endswith(".txt"):
            partes = arquivo.replace(".txt", "").split("_")
            buffer = partes[1].replace("buffer", "")
            delay = partes[2].replace("delay", "")
            repeticao = partes[3].replace("rep", "")
            caminho = os.path.join(diretorio, arquivo)
            vazao = parse_iperf_output(caminho)
            if vazao:
                resultados.append([buffer, delay, repeticao, vazao])

    with open(arquivo_saida, "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["buffer", "delay", "repeticao", "throughput_mbps"])
        writer.writerows(resultados)

# Chamada principal
salvar_resultados_csv(saida_dir)

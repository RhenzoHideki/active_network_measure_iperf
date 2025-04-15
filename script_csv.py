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
            # Ex: "208K" ou "64K"
            buffer_val = partes[1].replace("buffer", "")
            # Ex: "10" ou "100"
            delay_val = partes[2].replace("delay", "")
            repeticao = partes[3].replace("rep", "")
            caminho = os.path.join(diretorio, arquivo)
            vazao = parse_iperf_output(caminho)
            if vazao:
                resultados.append([buffer_val, delay_val, repeticao, vazao])
    
    # Função de ordenação que converte os valores para números
    def chave_ordenacao(item):
        # Remove o "K" e converte o buffer para inteiro
        buffer_numeric = int(item[0].replace("K", ""))
        delay_numeric = int(item[1])
        repet_numeric = int(item[2])
        return (buffer_numeric, delay_numeric, repet_numeric)

    resultados.sort(key=chave_ordenacao)

    with open(arquivo_saida, "w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["buffer", "delay", "repeticao", "throughput_mbps"])
        writer.writerows(resultados)

# Chamada principal
salvar_resultados_csv(saida_dir)

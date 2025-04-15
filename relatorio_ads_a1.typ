
  #import "@preview/klaro-ifsc-sj:0.1.0": report


    #show: doc => report(
      title: "Medição Ativa em Redes com o Iperf",
      subtitle: "Avaliação de desempenho de sistemas (ASD029009)",
      // Se apenas um autor colocar , no final para indicar que é um array
      authors:("Matheus Pires Salazar,Rhenzo Hideki Silva Kajikawa",),
      date: "8 de abril de 2025",
      doc,
    )


  = Introdução

  A medição ativa em redes é uma técnica fundamental para a avaliação do desempenho dos sistemas de comunicação. Este relatório apresenta a análise de desempenho de uma conexão TCP utilizando a ferramenta `iperf`, onde foram mensuradas as vazões sob diferentes configurações. A principal finalidade é entender como o tamanho do buffer de envio e os atrasos na rede (RTT) influenciam a vazão efetiva obtida na transferência de dados.


  = Descrição do Cenário
  Cenário escolhido foi o cenário 1, neste cenário será avaliada a vazão média de uma conexão TCP utilizando medições ativas com `iperf`, a fim de determinar os efeitos dos seguintes fatores:



  #table(
    columns: (auto,auto,auto,auto),
    inset: 10pt,
  [ Execução ],[ Buffer de Envio (-w) ],[ Atraso de Rede (RTT) ],[ Vazão Esperada (teórica) ],
  [    1     ],[       64 KB          ],[   10 ms (20 ms RTT)  ],[         Moderada         ],
  [    2     ],[       64 KB          ],[  100 ms (200 ms RTT) ],[         Baixa            ],
  [    3     ],[      208 KB          ],[   10 ms (20 ms RTT)  ],[         Alta             ],
  [    4     ],[      208 KB          ],[  100 ms (200 ms RTT) ],[         Moderada         ])
  Serão realizadas medições para as quatro combinações destes níveis, utilizando uma transferência fixa de 100M. Cada combinação será replicada 8 vezes para obter a média da vazão (em Mbps) e calcular o intervalo de confiança de 95%, permitindo a análise dos efeitos individuais e da interação entre os fatores.


  #pagebreak()
  = Desenvolvimento
  
  == Script
  A medição foi automatizada por meio de um script Python que inicia o cenário no emulador de rede (IMUNES), configura os parâmetros desejados (delay e buffer) e executa o `iperf` nas configurações especificadas. O script coleta os resultados em arquivos de saída (`.txt`) e os consolida em um arquivo CSV, que contém as colunas: *buffer, delay, repetição* e *throughput_mbps*. Posteriormente, um outro script processa esse CSV para calcular as médias e os intervalos de confiança e gerar um gráfico de barras.
  ```py
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
enlace = "router1:pc2"

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

  ```
== Análise do Código
=== Configurações Iniciais
Variáveis de Configuração:
São definidas as configurações essenciais para o experimento:

topologia: Arquivo que contém a definição do cenário de rede (cenario1.imn).

buffer_sizes e delays: Listas definem os valores de buffer (64K e 208K) e os valores de delay (10 ms e 100 ms) que serão testados.

repeticoes: Número de vezes que cada combinação será executada (8 repetições).

Nomes dos nós e IP: São configurados os nós cliente (pc2) e servidor (pc4), além do IP do servidor e do enlace utilizado para configuração do delay.

Diretório de Saída: Cria-se o diretório resultados_iperf para armazenar os arquivos com os resultados dos testes.

=== Funções Auxiliares
iniciar_imunes(topologia):

Executa o comando para iniciar o IMUNES com a topologia definida.

Utiliza o subprocess.run para chamar o programa com privilégios de superusuário.

Extrai o ID do cenário (eid) da saída do comando usando uma expressão regular.

Aguarda 2 segundos para que o cenário seja estabilizado antes de seguir com os testes.

configurar_delay(delay, enlace, cenario_id):

Converte o valor do delay de milissegundos para microssegundos, que é a unidade esperada pelo comando.

Aplica o delay configurado ao enlace especificado, utilizando o comando vlink.

iniciar_servidor_iperf(pc_servidor, cenario_id):

Inicia o servidor iperf no nó servidor, usando subprocess.Popen para rodar o processo em segundo plano.

Redireciona a saída e os erros para DEVNULL para evitar poluição no terminal.

parar_servidor_iperf(pc_servidor, cenario_id, processo):

Termina o processo do servidor iperf iniciado anteriormente.

Utiliza o comando pkill para assegurar que quaisquer instâncias residuais do iperf sejam finalizadas no nó servidor.

executar_teste(buffer, delay, repeticao, cenario_id):

Define o nome e o caminho do arquivo de saída com base no buffer, delay e número da repetição.

Inicia o servidor iperf e aguarda 1 segundo para que este se estabilize.

Executa o cliente iperf no nó cliente, realizando uma transferência de 100M com os parâmetros especificados, e grava a saída no arquivo definido.

Finaliza o servidor iperf após a realização do teste e aguarda mais 1 segundo antes de continuar.

finalizar_imunes(cenario_id):

Finaliza o cenário IMUNES chamando o comando apropriado para encerrar o ambiente simulado, liberando os recursos utilizados.

=== Funções para Análise dos Resultados
parse_iperf_output(file_path):

Lê o conteúdo do arquivo de saída gerado pelo iperf.

Percorre as linhas em ordem reversa para encontrar a linha relevante (não comentada).

Divide a linha em partes usando a vírgula como separador e retorna o valor de vazão presente na 9ª posição (índice 8).

Caso ocorra algum erro, exibe uma mensagem e retorna None.

calcular_intervalo_confianca(dados):

Calcula a média dos dados de vazão e o erro padrão (SEM) utilizando a biblioteca numpy e scipy.stats.

Se houver pelo menos 2 amostras, utiliza a distribuição t-student para calcular o intervalo de confiança de 95%.

Retorna uma tupla com os limites inferior e superior do intervalo; se não houver dados suficientes, retorna a média para ambos os limites.

=== Execução Principal
O bloco principal do script gerencia o fluxo de execução:

Inicializa o cenário chamando a função iniciar_imunes().

Para cada combinação de tamanho de buffer e delay, configura o atraso e executa os testes conforme o número de repetições definido.

Em caso de erro, o script captura e exibe a mensagem correspondente.

No final, se o cenário foi iniciado, ele é finalizado de forma apropriada, garantindo que todos os recursos sejam liberados.

  == Tabela de resultados
  #let resultados = csv("resultados_consolidados.csv")

  #align(
    table(
      columns: 4,
      ..resultados.flatten()
    ),
    center
  )

  Observa-se que os testes com buffer de 208K e atraso de 10 ms resultaram em vazões aproximadamente entre 92 e 93 Mbps, enquanto as configurações com atraso de 100 ms apresentaram vazões inferiores, próximas a 34–49 Mbps. Os dados consolidados foram posteriormente utilizados para gerar os gráficos.

  == Gráfico de Barras ( vazões e intevalos dde confiança )
O gráfico a seguir ilustra a média das vazões obtidas para cada combinação de buffer e atraso, com barras de erro representando o intervalo de confiança de 95%. Os grupos no eixo X são organizados pelo tamanho do buffer e, dentro de cada grupo, os diferentes atrasos são diferenciados por cores.

  #figure(
  image("./grafico_vazao.png",width:100%),
  caption: [
    Grafico gerado pelos resultados.

   Fonte: Elaborada pelo autor
  ],
  supplement: "Figura"
  );
O eixo Y foi limitado a 120 Mbps para garantir que os rótulos não ultrapassem os limites do gráfico e manter a leitura clara.

#pagebreak()
  == Resultados
  A análise dos resultados mostra que:

• **Conexões com buffer de 208K e atraso de 10 ms** atingem a maior vazão média, conforme esperado, validando a hipótese de que um buffer maior aliado a baixa latência favorece a performance do TCP.  

• **Testes com atraso de 100 ms** demonstraram uma queda significativa na vazão, independentemente do tamanho do buffer, evidenciando o impacto negativo da alta latência na transferência de dados.  
  = Conclusão


O estudo demonstrou que a combinação de um buffer de envio maior com baixa latência resulta em melhor desempenho na transferência TCP, enquanto condições de alta latência reduzem significativamente a vazão. Estes resultados evidenciam a importância da otimização dos parâmetros de rede para aplicações que demandam alta performance. Além disso, a metodologia aplicada – utilizando medições ativas com `iperf` e análise estatística dos resultados – se mostrou eficiente para a avaliação do desempenho dos sistemas de comunicação.

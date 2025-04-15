import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import scipy.stats as stats

# Carregar os dados do CSV
df = pd.read_csv('resultados_consolidados.csv')

# Converter throughput para Mbps (dividir por 1000000)
df['throughput_mbps'] = df['throughput_mbps'] / 1000000

# Agrupar por buffer e delay, e calcular média e desvio padrão
group = df.groupby(['buffer', 'delay'])
means = group['throughput_mbps'].mean().reset_index()
std_devs = group['throughput_mbps'].std().reset_index()

# Calcular o tamanho de cada grupo (número de amostras)
sample_counts = group.size().reset_index(name='count')

# Mesclar os dados
data = pd.merge(means, std_devs, on=['buffer', 'delay'], suffixes=('_mean', '_std'))
data = pd.merge(data, sample_counts, on=['buffer', 'delay'])

# Calcular margem de erro para IC de 95%
data['margin_of_error'] = stats.t.ppf(0.975, data['count']-1) * data['throughput_mbps_std'] / np.sqrt(data['count'])
data['ci_lower'] = data['throughput_mbps_mean'] - data['margin_of_error']
data['ci_upper'] = data['throughput_mbps_mean'] + data['margin_of_error']

# Criar rótulos para o eixo X combinando buffer e delay
data['label'] = data['buffer'] + '\n' + data['delay'].astype(str) + 'ms'

# Ordenar dados para o gráfico (ordem decrescente de velocidade para melhor visualização)
# Primeiro ordenar todos por buffer
buffer_order = ['208K', '64K']
data['sort_buffer'] = pd.Categorical(data['buffer'], categories=buffer_order, ordered=True)

# Depois ordenar por delay dentro de cada buffer
data = data.sort_values(by=['sort_buffer', 'delay'])

# Definir cores para as barras
colors = ['#4a86e8', '#ff9900', '#6aa84f', '#cc4125']

# Criar o gráfico
plt.figure(figsize=(12, 8))

# Posições das barras no eixo X
x_pos = np.arange(len(data))

# Criar barras
bars = plt.bar(x_pos, data['throughput_mbps_mean'], color=colors)

# Adicionar barras de erro para o intervalo de confiança
yerr = data['margin_of_error']
plt.errorbar(x_pos, data['throughput_mbps_mean'], yerr=yerr, fmt='none', color='black', capsize=5)

# Configurar rótulos e título
plt.ylabel('Vazão Média (Mbps)', fontsize=12)
plt.title('Desempenho do TCP com Diferentes Combinações de Buffer e Atraso\nIntervalos de Confiança de 95%', fontsize=14)
plt.xticks(x_pos, data['label'], fontsize=10)
plt.grid(axis='y', linestyle='--', alpha=0.7)

# Definir limites do eixo Y começando do zero
plt.ylim(0, max(data['throughput_mbps_mean'] + data['margin_of_error']) * 1.1)

# Adicionar valores e intervalo de confiança acima das barras
for i, bar in enumerate(bars):
    mean_value = data.iloc[i]['throughput_mbps_mean']
    ci_lower = data.iloc[i]['ci_lower']
    ci_upper = data.iloc[i]['ci_upper']
    plt.text(bar.get_x() + bar.get_width()/2, mean_value + 2,
             f"{mean_value:.2f} Mbps\nCI: [{ci_lower:.2f}, {ci_upper:.2f}]",
             ha='center', va='bottom', fontsize=9)

# Ajustar o layout para evitar sobreposição
plt.tight_layout()

# Salvar o gráfico
plt.savefig('grafico_vazao.png', dpi=300)

# Mostrar o gráfico
plt.show()
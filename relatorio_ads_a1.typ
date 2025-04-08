
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
== Tabela de resultados
== Gráfico de Barras ( vazões e intevalos dde confiança)
== Resultados
= Conclusão



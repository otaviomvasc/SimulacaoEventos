import simpy
import random
import numpy as np
import scipy
import matplotlib
import matplotlib.pyplot as plt
from random import expovariate, seed, normalvariate
from scipy import stats

from Modelos_Artigo import Entidades, Entidade_individual, Recursos, CorridaSimulacao, Simulacao


if __name__ == '__main__':
    """
    Passos:
        1 - Modelar fluxos de processo chegada, check-in, decisão 2-way-by-chance, check-in US/IM
        2 - Modelar direcionamento exames
        3 - Modelar saidas para outros exames e filas
        4 - Validar estatísticas
        5 - Pensar em como fazer loop de dias 
            Como o sistema "zera" a cada dia e as entidades são diferentes em cada dia (premissa do artigo), posso tentar
            criar loop de dias chamando uma nova simulação. Criar camada no final para salvar as estatísticas da mesma forma
            que as corridas de simulação
        6 - Criar corridas de simulação
        7 - Verificar os cálculos dos indicadores do artigo e bater resultados
    ---------------------------------------------------------------------------------------------------------------
    DÚVIDAS:
    ---------------------------------------------------------------------------------------------------------------
    1 - VALOR DOS TEMPOS DE CHEGADA E PROCESSO (TENTEI DEIXAR EM MINUTOS, PORÉM NÃO SEI SE ESTÁ CERTO)
    2 - VALIDAR ESTATISTICAS
    3 - NÃO CONSEGUI AINDA VALIDAR O MODELO COM OS RESULTADO DO ARTIGO. TENTAR FAZER ISSO APÓS O RESUMO!
    4 - ENTENDER COMO TRABALHAR COM MODELOS QUE SÃO INTERROMPIDOS NO SIMPY. VI QUE NA DOC TEM UM MÉTODO PARA EXECUTAR, 
    MAS NÃO SEI SE DEVO USA-LO OU POSSO APENAS CONSIDERAR UMA NOVA SIMULAÇÃO A CADA DIA.
    
    -----------------------------------------------------------------------------------------------------------
    Pendencias:
    -----------------------------------------------------------------------------------------------------------
    1 - Mudança de pacientes de SI para SU (Também não ficou claro no modelo conceitual o valor dessa probabilidade)
    
    2 - Validação das estatísticas e unidades dos dados de entrada

    """

    def define_time_slot(hora_chegada):
        """
        A ideia é encapsular essas infos para caso seja necessária alguma alteração, mudar
        num so lúgar.
        Como Calculei os sheets:
        inicio = 0
        07:00 - inicio
        09:00 -  Inicio + 1.5 horas
        11:00 - Inicio + 3.5 horas
        13:00 - Inicio + 6 horas
        15:00 - Inicio + 8 horas
        17:00 - Inicio + 10 horas
        19:00 - Inicio + 12 horas
        20:30 - Inicio + 13.5 horas
        """

        coef = 3600 #TODO: Verificar unidade de tempo da simulação
        time_slot_1 = [0, 1.5 * coef, "time_slot_1"]
        time_slot_2 = [1.5 * coef, 3.5 * coef, "time_slot_2"]
        time_slot_3 = [3.5 * coef, 6 * coef, "time_slot_3"]
        time_slot_4 = [6 * coef, 8 * coef, "time_slot_4"]
        time_slot_5 = [8 * coef, 10 * coef, "time_slot_5"]
        time_slot_6 = [10 * coef, 12 * coef, "time_slot_6"]
        time_slot_7 = [12 * coef, 13.5 * coef, "time_slot_7"]

        slots = [time_slot_1, time_slot_2, time_slot_3, time_slot_4, time_slot_5, time_slot_6, time_slot_7]
        return next(slot[2] for slot in slots if hora_chegada >= slot[0] and hora_chegada <= slot[1]) #iterator para minimizar tempo de busca!

    #define_time_slot(hora_chegada=10000)

    def calcula_probabilidade_IS(aleatorio):
        """
        Tive dúvidas na hora de entender qual a probabilidade de cada cliente ir para cada tipo de exame na
        parte de Imagem. Então considerei os dados de entrada, porém é necessário confirmar esse ponto de dúvida:

        17885 - Raio-x  probabilidade: (0.39)
        9627 - MRI probabilidade: (0.21)
        11119 - CAT probabilidade: (0.24)
        6102 - Mammography: (0.16)
        Total: 44733

        Então usei o conceito de distribuição acumulada de probabilidade para conseguir gerar a decisão a partir
        de um pseudoaleatório:

        0 - 0.39: Raio-x
        0.39 - 0.6: MRI
        0.6 - 0.84: CAT
        0.84 - 1: Mammography
        """

        op1 = [0, .39, "Raio-x"]
        op2 = [.39, .6, "MRI"]
        op3 = [.6, .84, "CAT"]
        op4 = [.84, 1.0, "Mammography"]

        processos = [op1, op2, op3, op4]

        return next(pr[2] for pr in processos if aleatorio >= pr[0] and aleatorio <= pr[1])

    def distribuicoes(processo, slot="None"):
        coef_processos = 60 #Conversão para minutos!!
        coef_chegadas = 60
        coef_checkin = 60
        dados = {"chegada" :
                           {"time_slot_1": expovariate(1/(1.7 * coef_chegadas)),
                            "time_slot_2": expovariate(1/(1.05 * coef_chegadas)),
                            "time_slot_3": expovariate(1/(1.26 * coef_chegadas)),
                            "time_slot_4": expovariate(1/(1.45 * coef_chegadas)),
                            "time_slot_5": expovariate(1/(1.16 * coef_chegadas)),
                            "time_slot_6": expovariate(1/(1.54 * coef_chegadas)),
                            "time_slot_7": expovariate(1/(4.46 * coef_chegadas))},

                 "decisao_fluxo":
                      {"time_slot_1": .8119,
                       "time_slot_2": .7779,
                       "time_slot_3": .7786,
                       "time_slot_4": .8357,
                       "time_slot_5": .7701,
                       "time_slot_6": .7796,
                       "time_slot_7": .9271},

                 #"check_in_ultrassom": {"None": np.random.lognormal(mean = 7.53, sigma = 3.65)}, #TODO: Validar como o artigo indica que o devio é 3.65 e não da negativo!!!
                 #"check_in_imagem": {"None": np.random.lognormal(mean = 7.53, sigma = 3.65)}, #TODO: Validar como o artigo indica que o devio é 3.65 e não da negativo!!
                 "check_in_ultrassom": {"None": random.normalvariate(15, 2.5) * coef_checkin},
                 "check_in_imagem": {"None": random.normalvariate(15, 2.5) * coef_checkin},
                 "Raio-x": {"None": 10 * coef_processos},
                 "MRI": {"None": 40 * coef_processos},
                 "CAT": {"None": 20 * coef_processos},
                 "Mammography": {"None": 15 * coef_processos},
                 "Ultrasound": {"None": 15 * coef_processos}
                 }

        return dados[processo][slot] #TODO: lembrar como fazer get de 2 níveis!!

    def calcula_distribuicoes_probabilidade():
        """
        Tive dúvidas na hora de entender qual a probabilidade de cada cliente ir para cada tipo de exame na
        parte de Imagem. Então considerei os dados de entrada, porém é necessário confirmar esse ponto de dúvida:

        17885 - Raio-x  probabilidade: (0.39)
        9627 - MRI probabilidade: (0.21)
        11119 - CAT probabilidade: (0.24)
        6102 - Mammography: (0.16)
        Total: 44733

        Então usei o conceito de distribuição acumulada de probabilidade para conseguir gerar a decisão a partir
        de um pseudoaleatório:

        0 - 0.39: Raio-x
        0.39 - 0.6: MRI
        0.6 - 0.84: CAT
        0.84 - 1: Mammography
        """

        def calcula(dados):
            inicio = 0
            list_aux = []
            for dado in dados:
                list_aux.append([inicio, inicio + dado[1], dado[0]])
                inicio = inicio + dado[1]
            return list_aux

        dados_raio_X = [["MRI", 0.075],
                 ["CAT", 0.038],
                 ["Mammography", 0.028],
                 ["Ultrasound", 0.172],
                 ["Exit", 0.719]]


        dados_mri = [["Raio-x", 0.142],
                 ["CAT", 0.035],
                 ["Mammography", 0.006],
                 ["Ultrasound", 0.035],
                 ["Exit", 0.808]]


        dados_cat = [["Raio-x", 0.061],
                 ["MRI", 0.030],
                 ["Mammography",0.015],
                 ["Ultrasound", 0.091],
                 ["Exit", 0.833]]


        dados_mamo = [["Raio-x", 0.082],
                 ["MRI", 0.009],
                 ["CAT", 0.028],
                ["Ultrasound", 0.972],
                ["Exit", 0.028]]


        dados_ultrasom = [["Raio-x", 0.130],
                 ["MRI", 0.014],
                 ["CAT", 0.042],
                 ["Mammography", 0.250],
                 ["Exit", 0.608]]


        dados_check_in_imagem = [["Raio-x", 0.39],
                 ["MRI", 0.21],
                 ["CAT",0.24],
                 ["Mammography",0.16]]


        dict_distribuicoes = {"check_in_ultrassom":0,
                              "check_in_imagem": calcula(dados_check_in_imagem),
                              "Raio-x": calcula(dados_raio_X),
                              "MRI": calcula(dados_mri),
                              "CAT":calcula(dados_cat),
                              "Mammography":calcula(dados_mamo),
                              "Ultrasound":calcula(dados_ultrasom)
                              }

        return dict_distribuicoes


    distribuicoes_probabilidade = calcula_distribuicoes_probabilidade()
    seed(1)
    recursos = {"check_in_ultrassom": 5,
                "check_in_imagem" : 5,
                "Raio-x": 4,
                "MRI": 6,
                "CAT": 3,
                "Mammography": 2,
                "Ultrasound": 8,
                "tecnico_Mammography": 1,
                "tecnico_Raio-x": 3,
                "assistente_Raio-x": 3,
                "tecnico_MRI": 4,
                "assistente_MRI": 4,
                "tecnico_CAT": 2,
                "assistente_CAT": 2,
                "medico_ultrasound": 6,
                "assistente_ultrasound": 6
                }

    #TODO: dessa forma só da pra pedir 1 por request. pensar em formas genéricas para quando for necessário mais de 1 recurso
    necessidade_recursos = {"Mammography": ["Mammography", "tecnico_Mammography"],
                            "Raio-x": ["Raio-x", "tecnico_Raio-x", "assistente_Raio-x"],
                            "MRI":["MRI", "tecnico_MRI", "assistente_MRI"],
                            "CAT": ["CAT", "tecnico_CAT", "assistente_CAT"],
                            "Ultrasound": ["Ultrasound", "medico_ultrasound", "assistente_ultrasound"]}
    dias = 30
    tempo = 13 * 3600 #Tempo em segundos!

    simulacao = Simulacao(distribuicoes=distribuicoes,
                          imprime=False,
                          recursos=recursos,
                          dist_prob=distribuicoes_probabilidade,
                          tempo = tempo,
                          necessidade_recursos = necessidade_recursos)

    # simulacao.comeca_simulacao()
    # simulacao.finaliza_todas_estatisticas()
    #simulacao.env.run(until=tempo)
    #b=0
    replicacoes = 5 # corridas * quantidade de dias. Essa é a maneira certa?
    warmup = tempo * 0.1 #Pensei em criar essa forma como porcentagem por tempo, mas o artigo simula de forma continua e indica o warmup como 13 semanas
    CorridaSimulacao = CorridaSimulacao(
        replicacoes= replicacoes,
        simulacao=simulacao,
        duracao_simulacao=tempo,
        periodo_warmup=warmup
    )

    CorridaSimulacao.roda_simulacao()
    CorridaSimulacao.fecha_estatisticas_experimento()
    b=0
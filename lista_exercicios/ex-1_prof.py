# -*- coding: utf-8 -*-
#!/usr/bin/python3

# Disciplina: EPD045: Simulacao por Eventos Discretos
# Prof: Joao Flavio F. Almeida <joao.flavio@dep.ufmg>
# Problemas de Simulação - Resolução em Simpy (python)

# ##################################################################
# Implementação computacional dos 10 exemplos das aulas
# ##################################################################

# ##################################################################
# Uma empresa opera três máquinas, em um determinado setor de sua 
# planta industrial. As máquinas trabalham em operação contínua, 
# interrompendo seu funcionamento apenas para manutenção corretiva. 
# O tempo entre falhas é descrito por uma distribuição exponencial 
# com média de 3 dias. A manutenção é feita por uma única equipe e 
# sua duração segue uma distribuição exponencial com média de 1 dia. 
# Deseja-se simular este problema para avaliar o tempo que as 
# máquinas ficam paradas aguardando por manutenção e para estimar 
# a ocupação média da equipe de manutenção. 
# Para tanto, construir o modelo conceitual do sistema usando 
# diagramas de ciclo de atividades.
# ##################################################################

# simulacao: https://simpy.readthedocs.io/en/latest/index.html
import simpy              
# numero aleatorio: https://docs.python.org/3/library/random.html
import random             
# biblioteca numérica do python: https://numpy.org/doc/stable/
import numpy as np        
# biblioteca numérica do python: https://scipy.org/
import scipy
# Impressao de graficos para periodo de Warm-up
import matplotlib
import matplotlib.pyplot as plt

from random import expovariate, seed
from scipy import stats

from Modelos import Estatistica_v1, Entidades,Entidade_individual, Recursos, Recurso_Individual
# Fixando a semente do gerador de numero aleatorio 
# (p/controle de cenários)
seed(1)  

NS = []
NA = []
NF = []
TS = []
TA = []
TF = []
USO= []

NS_bar = []
NF_bar = [] 
NA_bar = [] 
TS_bar = [] 
TF_bar = [] 
TA_bar = []
USO_bar= []

T = []  # Tempo dos Eventos Discretos

conta_chegada = 0
conta_saida = 0 

tempo_utilizacao_Recurso = 0

momento_chegada = {}
momento_saida = {}
tempo_sistema = {}
momento_entrada_fila = {}  
momento_saida_fila = {}
tempo_fila = {}
inicia_atendimento = {}
finaliza_atendimento = {}
duracao_atendimento = {}
utilizacao = {}

CAP_EQUIPE = 1

###################################################################
# Configura a rodada de simulacao definindo o 
# numero de replicações e duração da simulação
###################################################################
# # Teste
n_replicacoes = 1
duracao_da_simulacao = 1000
tempo_aquecimento = 0
imprime_detalhes = True
###################################################################
# Simulação oficial
# n_replicacoes = 5
# duracao_da_simulacao =   24*365
# tempo_aquecimento = 2000
# imprime_detalhes = False
###################################################################

# Unidade básica para todos os tempos: horas
def distribuicoes(tipo):
    taxa_chegadas=1         # por hora
    taxa_operacao=1/(3*24)  # por hora
    taxa_manutencao=1/24    # por hora
    return {
        'chegada': expovariate(taxa_chegadas),
        'operacao': expovariate(taxa_operacao),
        'manutencao': expovariate(taxa_manutencao)
    }.get(tipo,0.0)


def gera_maquinas(env, entidade, est, entidades):
    global conta_chegada    
    yield env.timeout(0)
    for i in range(1,4):
        conta_chegada+=1
        nome = entidade + " " + str(conta_chegada)
        momento_chegada[nome] = env.now
        est.momento_chegada[nome] = env.now
        entidade_indvidual = Entidade_individual(nome=nome)
        #entidades.entidades.append(entidade_indvidual)
        #est.coleta_estatistica(nome=nome, processo='chegada', tipo='recurso', valor=env.now)
        if imprime_detalhes:
            #print("{0:.2f}: {1:s} Inicia a operação".format(env.now, nome))
            print(f"{env.now}: {entidade_indvidual.nome} Inicia a operação")
        env.process(operacao(env, entidade_indvidual, est))


def operacao(env, entidade, est):
    # Delay    
    yield env.timeout(distribuicoes('operacao')) 
    if imprime_detalhes:
        #print("{0:.2f}: {1:s} quebrou! Vai para manutenção".format(env.now, nome))
         print(f"{env.now}: {entidade.nome} quebrou! Vai para manutenção")
    env.process(manutencao(env, entidade, equipes, est))


def manutencao(env, entidade, equipes, est):
    momento_entrada_fila[entidade.nome] = env.now
    est.momento_entrada_fila[entidade.nome] = env.now
    entidade.entra_fila = env.now
    #est.coleta_estatistica(nome=nome, processo="manutencao", tipo="fila", valor=env.now)
    # Requer uso de um slot do Recurso
    request=equipes.request()
    # Seize, Delay, Release
    yield request   
    momento_saida_fila[entidade.nome] = env.now
    est.momento_saida_fila[entidade.nome]=env.now
    entidade.sai_fila = env.now
    #est.coleta_estatistica(nome=nome, processo="manutencao", tipo="fila", valor=env.now, completa=True)
    tempo_fila[entidade.nome] = momento_saida_fila[entidade.nome] - momento_entrada_fila[entidade.nome]
    est.tempo_fila[entidade.nome] = est.momento_saida_fila[entidade.nome] - est.momento_entrada_fila[entidade.nome]
    if imprime_detalhes:
        print("{0:.2f}: Equipe inicia o atendimento da {1:s}. Número de entidades em atendimento: {2:d}".format(env.now, entidade.nome, equipes.count))

    inicia_atendimento[entidade.nome] = env.now
    est.inicia_atendimento[entidade.nome] = env.now
    entidade.entra_processo = env.now
    est.coleta_estatistica(nome=entidade.nome, processo="manutencao", tipo="processo", valor=env.now)
    inicia_utilizacao_Recurso = env.now
    est.inicia_utilizacao_Recurso = env.now

    yield env.timeout(distribuicoes('manutencao'))    
    if imprime_detalhes:
        print("{0:.2f}: Equipe termina o atendimento da {1:s}. Número de entidades em fila: {2:d}".format(env.now, entidade.nome, len(equipes.queue)))
    finaliza_atendimento[entidade.nome] = env.now
    est.finaliza_atendimento[entidade.nome] = env.now
    entidade.sai_processo = env.now
    #est.coleta_estatistica(nome=nome, processo="manutencao", tipo="processo", valor=env.now, completa=True)
    duracao_atendimento[entidade.nome] = finaliza_atendimento[entidade.nome] - inicia_atendimento[entidade.nome]
    est.duracao_atendimento[entidade.nome] = est.finaliza_atendimento[entidade.nome] - est.inicia_atendimento[entidade.nome]
    entidade.fecha_ciclo(processo="manutencao")
    yield equipes.release(request)
    global tempo_utilizacao_Recurso
    tempo_utilizacao_Recurso += env.now - inicia_utilizacao_Recurso
    utilizacao['Equipe'] = tempo_utilizacao_Recurso/(CAP_EQUIPE*env.now)
    est.utilizacao['Equipe'] = tempo_utilizacao_Recurso/(CAP_EQUIPE*env.now)

    #est.coleta_estatistica(nome='Equipe1', processo="manutencao", tipo="utilizacao", valor=tempo_utilizacao_Recurso/(CAP_EQUIPE*env.now))

    coleta_dados_indicadores(env, entidade.nome, equipes)
    #est.coleta_dados_indicadores(env=env, tempo_aquecimento=10)
    env.process(operacao (env, entidade, est))


def coleta_dados_indicadores(env, nome, equipes):    
    global conta_saida
    conta_saida = 0

    # Coleta dados para estatísticas        
    numero_sistema = conta_chegada - conta_saida 

    if env.now > tempo_aquecimento:
        NS.append(numero_sistema)
        NA.append(equipes.count)
        NF.append(len(equipes.queue))
    

    momento_saida[nome] = env.now            
    tempo_sistema[nome] = momento_saida[nome] - momento_chegada[nome]
    # print(f'momento_chegada[{nome}]: ', momento_chegada[nome])
    # print(f'momento_saida[{nome}]: ', momento_saida[nome])
    # print(f'tempo_sistema[{nome}]: ', tempo_sistema[nome])
    if env.now > tempo_aquecimento:
        TS.append(tempo_sistema[nome])
        TA.append(duracao_atendimento[nome])
        TF.append(tempo_fila[nome])
        
    # Coleta dados para estatísticas        
    numero_sistema = conta_chegada - conta_saida

    if env.now > tempo_aquecimento:
        NS.append(numero_sistema)
        NA.append(equipes.count)
        NF.append(len(equipes.queue))


    momento_saida[nome] = env.now            
    tempo_sistema[nome] = momento_saida[nome] - momento_chegada[nome]
    # print(f'momento_chegada[{nome}]: ', momento_chegada[nome])
    # print(f'momento_saida[{nome}]: ', momento_saida[nome])
    # print(f'tempo_sistema[{nome}]: ', tempo_sistema[nome])
    if env.now > tempo_aquecimento:
        TS.append(tempo_sistema[nome])
        TA.append(duracao_atendimento[nome])
        TF.append(tempo_fila[nome])
        USO.append(utilizacao['Equipe'])
        T.append(env.now)


def computa_estatisticas(replicacao):  
    print()
    comprimento_linha = 100
    print("="*comprimento_linha)   
    print("Indicadores de Desempenho da Replicacao {0:d}".format(replicacao), end="\n")
    print("="*comprimento_linha)   
    # print('NS: ', NS)
    # print('NF: ', NF)
    # print('NA: ', NA)
    # print('TS: ', TS)
    # print('TF: ', TF)
    # print('TA: ', TA)
    NS_i = np.mean(NS)
    NF_i = np.mean(NF)
    NA_i = np.mean(NA)
    TS_i = np.mean(TS)
    TF_i = np.mean(TF)
    TA_i = np.mean(TA)
    USO_i= np.mean(USO)    
    print('Chegadas: {0:d} máquinas'.format(conta_chegada))
    print('Saidas:   {0:d} máquinas'.format(conta_saida))
    print('WIP:      {0:d} máquinas'.format(conta_chegada-conta_saida))
    print('NS: {0:.2f} máquinas'.format(NS_i))
    print('NF: {0:.2f} máquinas'.format(NF_i))
    print('NA: {0:.2f} máquinas'.format(NA_i))
    print('TS: {0:.2f} horas'.format(TS_i))
    print('TF: {0:.2f} horas'.format(TF_i))
    print('TA: {0:.2f} horas'.format(TA_i))
    print('USO:{0:.2f}%'.format(USO_i*100))    
    print("="*comprimento_linha, end="\n")   
    NS_bar.append(NS_i)
    NF_bar.append(NF_i)
    NA_bar.append(NA_i)
    TS_bar.append(TS_i)
    TF_bar.append(TF_i)
    TA_bar.append(TA_i)
    USO_bar.append(USO_i)


def calc_ic(lista):
    confidence = 0.95
    n = len(lista)
    # mean_se: Erro Padrão da Média
    mean_se = stats.sem(lista)
    h = mean_se * stats.t.ppf((1 + confidence) / 2., n-1)
    # Intervalo de confiança: mean, +_h
    return h


def publica_estatisticas():  
    print()
    comprimento_linha = 100
    print("="*comprimento_linha)   
    print("Indicadores de Desempenho do Sistema", end="\n")
    print("="*comprimento_linha)   
    
    print('NS: {0:.2f} \u00B1 {1:.2f} máquinas (IC 95%)'.format(np.mean(NS_bar), calc_ic(NS)))
    print('NF: {0:.2f} \u00B1 {1:.2f} máquinas (IC 95%)'.format(np.mean(NF_bar), calc_ic(NF)))
    print('NA: {0:.2f} \u00B1 {1:.2f} máquinas (IC 95%)'.format(np.mean(NA_bar), calc_ic(NA)))
    print('TS: {0:.2f} \u00B1 {1:.2f} horas (IC 95%)'.format(np.mean(TS_bar), calc_ic(TS)))
    print('TF: {0:.2f} \u00B1 {1:.2f} horas (IC 95%)'.format(np.mean(TF_bar), calc_ic(TF)))
    print('TA: {0:.2f} \u00B1 {1:.2f} horas (IC 95%)'.format(np.mean(TA_bar), calc_ic(TA)))
    print('USO:{0:.2f}% \u00B1 {1:.2f}%  (IC 95%)'.format(np.mean(USO_bar)*100, calc_ic(USO)*100))
    print("="*comprimento_linha, end="\n") 

    ###################################################################
    # Gera gráfico de Warm-up
    ###################################################################
    if n_replicacoes == 1:
        matplotlib.rcParams['figure.figsize'] = (8.0, 6.0)
        matplotlib.style.use('ggplot')
        # cria os dados
        xi = T     
        y = USO        
        # usa a função plot
        plt.title('Indicador de Desempenho: \n\n' + "Utilização média da equipe de manutenção")
        plt.plot(xi, y, marker='o', linestyle='-', color='r', label='Dados')
        plt.ylim(0.0,1.0)
        plt.xlim(0.0,duracao_da_simulacao)
        plt.xlabel('Tempo (horas)')
        plt.ylabel('Valor') 
        plt.show()
    ###################################################################
  

###################################################################

for i in range (1,n_replicacoes+1):
    # Re-inicializacao das estatísticas entre replicações
    conta_chegada = 0    
    conta_saida = 0
    tempo_utilizacao_Recurso = 0

    estatisticas = Estatistica_v1()
    entidades = Entidades()
    recursos = Recursos()
    env = simpy.Environment()
    equipes = simpy.Resource(env, capacity=CAP_EQUIPE)
    equipe_est = Recurso_Individual(rec_simpy=equipes, capacidade=CAP_EQUIPE)
    recursos.recursos.append(equipe_est)
    env.process(gera_maquinas(env=env, entidade="maquina",est=estatisticas,entidades=entidades))
    env.run(duracao_da_simulacao)
    computa_estatisticas(i)    

publica_estatisticas()
###################################################################
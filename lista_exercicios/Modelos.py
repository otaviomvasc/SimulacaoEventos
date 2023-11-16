import simpy
import random
import numpy as np
from scipy import stats
import matplotlib
import matplotlib.pyplot as plt
import pandas as pd
from copy import deepcopy

""" 
Temos 3 tipos de estatisticas:
Da Simulação (NS)
Dos recursos (NA - Individuos em fila e NF)

Então a tentativa é fazer a captura para cada entidade/recurso e depois juntar tudo no final.
Também passei a estatística para uma classe para ficar mais fácil de usar em outros codigos.
"""
#TODO: Passar essas classes para abstratas e deixar como fixo!!!
class Simulacao():
    def __init__(self, distribuicoes, qntd_chegadas, imprime, recursos):
        self.env = simpy.Environment()
        self.distribuicoes = distribuicoes
        self.entidades = Entidades()
        self.recursos_est = Recursos(env = self.env, recursos=recursos) #Foi necessário criar 2x de recursos. Pensar algo melhor!
        self.recursos = self.recursos_est.recursos
        self.estatisticas_sistema = EstatisticasSistema()
        self.estatisticas = Estatistica_v1()
        self.imprime_detalhes = imprime
        self.qntd_chegadas = qntd_chegadas

    def comeca_simulacao(self):
        self.env.process(self.gera_maquinas())

    def finaliza_todas_estatisticas(self):
        self.entidades.fecha_estatisticas()
        self.recursos_est.fecha_estatisticas()
        self.estatisticas_sistema.fecha_estatisticas()

    def gera_maquinas(self):
        yield self.env.timeout(0)
        for i in range(1, self.qntd_chegadas):
            self.estatisticas_sistema.computa_chegadas(momento=self.env.now)
            nome = 'entidade' + " " + str(self.estatisticas_sistema.chegadas)
            entidade_indvidual = Entidade_individual(nome=nome)
            entidade_indvidual.entrada_sistema = self.env.now
            self.entidades.lista_entidades.append(entidade_indvidual)
            if self.imprime_detalhes:
                # print("{0:.2f}: {1:s} Inicia a operação".format(env.now, nome))
                print(f"{self.env.now}: {entidade_indvidual.nome} Inicia a operação")
            self.env.process(self.operacao(entidade_indvidual))

    def operacao(self, entidade_individual):
        yield self.env.timeout(self.distribuicoes('operacao'))
        if self.imprime_detalhes:
            print(f"{self.env.now}: {entidade_individual.nome} quebrou! Vai para manutenção")
        self.env.process(self.manutencao(entidade_individual))

    def manutencao(self, entidade_individual):

        entidade_individual.entra_fila = self.env.now #Estatisticas modo 2
        request = self.recursos['equipes'].request() #TODO: Pensar melhor o funcionamento dos recursos
        yield request
        entidade_individual.sai_fila = self.env.now #Estatisticas modo 2
        if self.imprime_detalhes:
            print("{0:.2f}: Equipe inicia o atendimento da {1:s}. Número de entidades em atendimento: {2:d}".format(
                self.env.now, entidade_individual.nome, self.recursos['equipes'].count))

        entidade_individual.entra_processo = self.env.now #Estatisticas modo 2
        self.recursos['equipes'].inicia_utilizacao_recurso = self.env.now

        yield self.env.timeout(self.distribuicoes('manutencao'))
        if self.imprime_detalhes:
            print(f"{self.env.now,}: Equipe termina o atendimento da {entidade_individual.nome}. Número de entidades em fila: {len(self.recursos['equipes'].queue)}")

        entidade_individual.sai_processo = self.env.now #Estatisticas modo 2
        entidade_individual.fecha_ciclo(processo="manutencao") #Estatisticas modo 2
        yield self.recursos['equipes'].release(request)
        self.recursos['equipes'].finaliza_utilizacao_recurso = self.env.now
        #TODO: Descobrir como criar self sem alterar simpy!!!!
        self.recursos_est.fecha_ciclo(nome_recurso='equipes', momento=self.env.now)
        self.env.process(self.operacao(entidade_individual=entidade_individual))

class EstatisticasSistema():
    def __init__(self):
        self.chegadas = 0
        self.saidas = 0
        self.WIP = 0
        self.df_estatisticas_simulacao = pd.DataFrame()
        self.entidades_sistema = list()

    def fecha_estatisticas(self):
        print(f'Chegadas: {self.chegadas}')
        print(f'Saídas: {self.saidas}')
        print(f'WIP: {self.WIP} ')
        entidades_sistema = np.mean([v for reg in self.entidades_sistema for v in reg.values()]) #TODO: Verificar como esse cálculo ta sendo feito!!
        dict_aux = {"Chegadas": self.chegadas,
                    "Saidas": self.saidas,
                    "WIP": self.WIP,
                    "Media_Sistema": entidades_sistema}

        self.df_estatisticas_simulacao = pd.DataFrame([dict_aux])

    def computa_chegadas(self, momento):
        #TODO: Adaptar para computar chegadas de mais de um indivíduo!!!!
        self.chegadas += 1
        self.WIP += 1
        self.entidades_sistema.append({"discretizacao": momento,
                                       "WIP": self.WIP})

    def computa_saidas(self, momento):
        self.saidas += 1
        self.WIP -= 1
        self.entidades_sistema.append({"discretizacao": momento,
                                       "WIP": self.WIP})

class Estatistica_v1:
    def __init__(self):
        self.dados_list = list()
        self.dados_dict = dict()
        self.NS = list()
        self.NA = list()
        self.NF = list()
        self.TS = list()
        self.TA = list()
        self.TF = list()
        self.USO = list()

        self.NS_bar = list()
        self.NF_bar = list()
        self.NA_bar = list()
        self.TS_bar = list()
        self.TF_bar = list()
        self.TA_bar = list()
        self.USO_bar = list()

        T = []  # Tempo dos Eventos Discretos

        self.conta_chegada = 0
        self.conta_saida = 0

        self.tempo_utilizacao_Recurso = 0

        self.momento_chegada = dict()
        self.momento_saida = dict()
        self.tempo_sistema = dict()
        self.momento_entrada_fila = dict()
        self.momento_saida_fila = dict()
        self.tempo_fila = dict()
        self.inicia_atendimento = dict()
        self.finaliza_atendimento = dict()
        self.duracao_atendimento = dict()
        self.utilizacao = dict()
        self.T = list()

    def coleta_estatistica(self, nome=None, processo=None, tipo=None, valor=None, completa=False):
        if not completa:
            aux_salva = {"nome":nome, "processo":processo, "tipo":tipo, "tempo_inicio":valor, "tempo_fim":0.0}
            self.dados_list.append(aux_salva)
        else:
            a=0
    def coleta_dados_indicadores(self,
                                 env,
                                 tempo_aquecimento,
                                 numero_sistema,
                                 individuos_fila,
                                 tamanho_fila,
                                 entidade
                                 ):

        #global conta_saida
        #conta_saida = 0

        # Coleta dados para estatísticas
        #numero_sistema = conta_chegada - conta_saida

        if env.now > tempo_aquecimento:
            self.NS.append(numero_sistema)
            self.NA.append(individuos_fila)
            self.NF.append(tamanho_fila)

        self.momento_saida[entidade.nome] = env.now
        self.tempo_sistema[entidade.nome] = self.momento_saida[entidade.nome] - self.momento_chegada[entidade.nome]
        if env.now > tempo_aquecimento:
            self.TS.append(self.tempo_sistema[entidade.nome])
            self.TA.append(entidade.estatisticas[-1]['tempo_processando'])
            self.TF.append(entidade.estatisticas[-1]['tempo_fila'])
            self.USO.append(self.utilizacao['Equipe'])
            self.T.append(env.now)

    def computa_estatisticas(self,replicacao):
        print()
        comprimento_linha = 100
        print("=" * comprimento_linha)
        print("Indicadores de Desempenho da Replicacao {0:d}".format(replicacao), end="\n")
        print("=" * comprimento_linha)
        # print('NS: ', NS)
        # print('NF: ', NF)
        # print('NA: ', NA)
        # print('TS: ', TS)
        # print('TF: ', TF)
        # print('TA: ', TA)
        self.NS_i = np.mean(self.NS)
        self.NF_i = np.mean(self.NF)
        self.NA_i = np.mean(self.NA)
        self.TS_i = np.mean(self.TS)
        self.TF_i = np.mean(self.TF)
        self.TA_i = np.mean(self.TA)
        self.USO_i = np.mean(self.USO)
        #print('Chegadas: {0:d} máquinas'.format(conta_chegada))
        #print('Saidas:   {0:d} máquinas'.format(conta_saida))
        #print('WIP:      {0:d} máquinas'.format(conta_chegada - conta_saida))
        print('NS: {0:.2f} máquinas'.format(self.NS_i))
        print('NF: {0:.2f} máquinas'.format(self.NF_i))
        print('NA: {0:.2f} máquinas'.format(self.NA_i))
        print('TS: {0:.2f} horas'.format(self.TS_i))
        print('TF: {0:.2f} horas'.format(self.TF_i))
        print('TA: {0:.2f} horas'.format(self.TA_i))
        print('USO:{0:.2f}%'.format(self.USO_i * 100))
        print("=" * comprimento_linha, end="\n")
        self.NS_bar.append(self.NS_i)
        self.NF_bar.append(self.NF_i)
        self.NA_bar.append(self.NA_i)
        self.TS_bar.append(self.TS_i)
        self.TF_bar.append(self.TF_i)
        self.TA_bar.append(self.TA_i)
        self.USO_bar.append(self.USO_i)


    def publica_estatisticas(self):
        def calc_ic(lista):
            confidence = 0.95
            n = len(lista)
            # mean_se: Erro Padrão da Média
            mean_se = stats.sem(lista)
            h = mean_se * stats.t.ppf((1 + confidence) / 2., n - 1)
            # Intervalo de confiança: mean, +_h
            return h

        print()
        comprimento_linha = 100
        print("=" * comprimento_linha)
        print("Indicadores de Desempenho do Sistema", end="\n")
        print("=" * comprimento_linha)

        print('NS: {0:.2f} \u00B1 {1:.2f} máquinas (IC 95%)'.format(np.mean(self.NS_bar), calc_ic(self.NS)))
        print('NF: {0:.2f} \u00B1 {1:.2f} máquinas (IC 95%)'.format(np.mean(self.NF_bar), calc_ic(self.NF)))
        print('NA: {0:.2f} \u00B1 {1:.2f} máquinas (IC 95%)'.format(np.mean(self.NA_bar), calc_ic(self.NA)))
        print('TS: {0:.2f} \u00B1 {1:.2f} horas (IC 95%)'.format(np.mean(self.TS_bar), calc_ic(self.TS)))
        print('TF: {0:.2f} \u00B1 {1:.2f} horas (IC 95%)'.format(np.mean(self.TF_bar), calc_ic(self.TF)))
        print('TA: {0:.2f} \u00B1 {1:.2f} horas (IC 95%)'.format(np.mean(self.TA_bar), calc_ic(self.TA)))
        print('USO:{0:.2f}% \u00B1 {1:.2f}%  (IC 95%)'.format(np.mean(self.USO_bar) * 100, calc_ic(self.USO) * 100))
        print("=" * comprimento_linha, end="\n")

        matplotlib.rcParams['figure.figsize'] = (8.0, 6.0)
        matplotlib.style.use('ggplot')
        # cria os dados
        xi = self.T
        y = self.USO
        # usa a função plot
        plt.title('Indicador de Desempenho: \n\n' + "Utilização média da equipe de manutenção")
        plt.plot(xi, y, marker='o', linestyle='-', color='r', label='Dados')
        plt.ylim(0.0, 1.0)
        plt.xlim(0.0, 1000)
        plt.xlabel('Tempo (horas)')
        plt.ylabel('Valor')
        plt.show()

class Entidades:
    def __init__(self):
        self.lista_entidades = list()
        self.df_entidades = pd.DataFrame()
        self.resultados_entidades = pd.DataFrame()

    def fecha_estatisticas(self):
        def printa_media(coluna):
            res = round(np.mean(self.df_entidades[coluna]),2)
            print(f'{coluna} : {res}')

        tempo_sistema = list()
        for ent in self.lista_entidades:
            df_aux = pd.DataFrame(ent.estatisticas)
            self.df_entidades = pd.concat([self.df_entidades, df_aux])
            tempo_sistema.append(ent.saida_sistema - ent.entrada_sistema)


        dict_estatisticas_calculadas = {"tempo_sistema":np.mean(tempo_sistema),
        "tempo_processamento":round(np.mean(self.df_entidades['tempo_processando']),2),
        "tempo_fila" :round(np.mean(self.df_entidades['tempo_fila']),2)}
        printa_media(coluna='tempo_processando')
        printa_media(coluna='tempo_fila')
        print(f'TS: { np.mean(self.df_entidades.sai_processo)}') #TODO: Prof considerou a média do tempo que as máquinas sairam da manutenção, já que o sistema é continuo. Confirmar como fica em sistemas não-continuos
        self.resultados_entidades = pd.DataFrame([dict_estatisticas_calculadas])

class Entidade_individual(Entidades):
    def __new__(cls, *args, **kwargs):   #Usado para não relacionar um individuo com outro (substituindo o deepcopy)
        return object.__new__(cls)

    def __init__(self, nome):
        self.nome = nome
        self.entra_fila: float = 0.0
        self.sai_fila: float = 0.0
        self.entra_processo: float = 0.0
        self.sai_processo: float = 0.0
        self.estatisticas = list()
        self.entrada_sistema: float = 0.0
        self.saida_sistema: float = 0.0

    def fecha_ciclo(self, processo):
        aux_dados = {"entidade": self.nome,
                     "processo": processo,
                     "entra_fila": self.entra_fila,
                     "sai_fila": self.sai_fila,
                     "tempo_fila": self.sai_fila - self.entra_fila,
                     "entra_processo": self.entra_processo,
                     "sai_processo": self.sai_processo,
                     "tempo_processando": self.sai_processo - self.entra_processo,
                     "entra_sistema":  self.entrada_sistema,
                     "sai_sistema": self.saida_sistema}

        self.estatisticas.append(aux_dados)
        self.entra_fila: float = 0.0
        self.sai_fila: float = 0.0
        self.entra_processo: float = 0.0
        self.sai_processo: float = 0.0

class Recursos:
    def __init__(self, recursos, env):
        self.recursos = self.cria_recursos(recursos, env)
        self.df_estatisticas_recursos = pd.DataFrame()

    def cria_recursos(self, dict_recursos, env):
        recursos_dict = dict()
        for rec, cap in dict_recursos.items():
            rec_aux = simpy.Resource(env, capacity=cap)
            #copy_rec = type(rec_aux).__new__(type(rec_aux)) #Forma de copiar o recurso e inserir atributos sem alterar a biblioteca do simpy. Verificar se vai dar certo!
            #Criação dos atributos para estatísticas de cada recurso. Verificar se é necessário esse clone para acrescentar atributos!
            rec_aux.nome = rec
            rec_aux.inicia_utilizacao_recurso = 0
            rec_aux.finaliza_utilizacao_recurso = 0
            rec_aux.utilizacao = 0
            rec_aux.estatisticas = []
            #rec_aux.fecha_ciclo = fecha_ciclo
            recursos_dict[rec] = rec_aux

        return recursos_dict

    def fecha_ciclo(self, nome_recurso, momento):
        recurso = self.recursos[nome_recurso]
        #TODO: preciso usar o momento ou apenas o fecha_utilizacao_recurso ja tem esse dado, visto que será chamado após processo
        dict_aux = {"inicia_utilizacao_recurso": recurso.inicia_utilizacao_recurso,
                    "finaliza_utilizacao_recurso": recurso.finaliza_utilizacao_recurso,
                    "tempo_utilizacao_recurso": recurso.finaliza_utilizacao_recurso - recurso.inicia_utilizacao_recurso,
                    "utilizacao": recurso.finaliza_utilizacao_recurso - recurso.inicia_utilizacao_recurso/(recurso._capacity * momento),
                    "T": momento,
                    "fila_recurso": recurso.count,
                    "tamanho_fila": len(recurso.queue)
                    }

        recurso.estatisticas.append(dict_aux)

    def fecha_estatisticas(self):
        for nome, rec in self.recursos.items():
            df_aux = pd.DataFrame(rec.estatisticas)
            utilizacao_media = np.mean(df_aux['utilizacao'])
            print(f'Utilizacao Média do Recurso {nome}: {utilizacao_media}')
            df_aux['recurso'] = nome
            self.df_estatisticas_recursos = pd.concat([self.df_estatisticas_recursos, df_aux])
        b=0

class CorridaSimulacao():
    def __init__(self, replicacoes, simulacao: Simulacao, duracao_simulacao):
        self.replicacoes: int = replicacoes
        self.df_estatisticas_entidades = pd.DataFrame()  #Lista com cada estatística de cada rodada
        self.df_estatisticas_sistema = pd.DataFrame()
        self.df_estatisticas_recursos = pd.DataFrame()
        self.duracao_simulacao = duracao_simulacao
        #self.simulacoes = [type(simulacao).__new__(type(simulacao)) for i in range(replicacoes)]
        self.simulacoes = [deepcopy(simulacao) for i in range(replicacoes)]

    def roda_simulacao(self):
        for n_sim in range(len(self.simulacoes)):
            print(f'Simulação {n_sim + 1}')
            print('-' * 150)
            simulacao = self.simulacoes[n_sim]
            simulacao.comeca_simulacao()
            simulacao.env.run(until=self.duracao_simulacao)
            simulacao.finaliza_todas_estatisticas()
        b=0

    def fecha_estatisticas_experimento(self):
        def calc_ic(lista):
            confidence = 0.95
            n = len(lista)
            # mean_se: Erro Padrão da Média
            mean_se = stats.sem(lista)
            h = mean_se * stats.t.ppf((1 + confidence) / 2., n - 1)
            # Intervalo de confiança: mean, +_h
            return h
        #Agrupando os dados
        for n_sim in range(len(self.simulacoes)):
            df_entidades = self.simulacoes[n_sim].entidades.df_entidades
            df_entidades['Replicacao'] = n_sim + 1
            df_sistema = self.simulacoes[n_sim].estatisticas_sistema.df_estatisticas_simulacao
            df_sistema['Replicacao'] = n_sim + 1
            df_recursos = self.simulacoes[n_sim].recursos_est.df_estatisticas_recursos
            df_recursos['Replicacao'] = n_sim + 1
            self.df_estatisticas_entidades = pd.concat([self.df_estatisticas_entidades, df_entidades])
            self.df_estatisticas_sistema = pd.concat([self.df_estatisticas_sistema,df_sistema ])
            self.df_estatisticas_recursos = pd.concat([self.df_estatisticas_recursos, df_recursos])


        TS = [ent.saida_sistema - ent.entrada_sistema for sim in self.simulacoes for ent in sim.entidades.lista_entidades]
        TA = self.df_estatisticas_entidades['tempo_processando']
        TF = self.df_estatisticas_entidades['tempo_fila']
        NA = self.df_estatisticas_recursos['fila_recurso']
        NF = self.df_estatisticas_recursos['tamanho_fila']
        NS = [d['WIP'] for sim in self.simulacoes for d in sim.estatisticas_sistema.entidades_sistema ] #TODO: Confirmar esse cálculo!
        USO = self.df_estatisticas_recursos['utilizacao']

        TS_ = np.mean([ent.saida_sistema - ent.entrada_sistema for sim in self.simulacoes for ent in sim.entidades.lista_entidades])
        TA_ = np.mean(self.df_estatisticas_entidades['tempo_processando'])
        TF_ = np.mean(self.df_estatisticas_entidades['tempo_fila'])
        NA_ = np.mean(self.df_estatisticas_recursos['fila_recurso'])
        NF_ = np.mean(self.df_estatisticas_recursos['tamanho_fila'])
        NS_ = np.mean([d['WIP'] for sim in self.simulacoes for d in sim.estatisticas_sistema.entidades_sistema ])
        USO_= np.mean(self.df_estatisticas_recursos['utilizacao'])

        chegadas = np.mean([sim.estatisticas_sistema.chegadas for sim in self.simulacoes])
        saidas = np.mean([sim.estatisticas_sistema.saidas for sim in self.simulacoes])
        WIP = np.mean([sim.estatisticas_sistema.WIP for sim in self.simulacoes])
        print(f'Chegadas: {chegadas} máquinas')
        print(f'Saidas:   {saidas} máquinas')
        print(f'WIP:      {WIP} máquinas')
        print()
        comprimento_linha = 100
        print("=" * comprimento_linha)
        print("Indicadores de Desempenho do Sistema", end="\n")
        print("=" * comprimento_linha)

        print('NS: {0:.2f} \u00B1 {1:.2f} máquinas (IC 95%)'.format(np.mean(NS_), calc_ic(NS)))
        print('NF: {0:.2f} \u00B1 {1:.2f} máquinas (IC 95%)'.format(np.mean(NF_), calc_ic(NF)))
        print('NA: {0:.2f} \u00B1 {1:.2f} máquinas (IC 95%)'.format(np.mean(NA_), calc_ic(NA)))
        print('TS: {0:.2f} \u00B1 {1:.2f} horas (IC 95%)'.format(np.mean(TS_), calc_ic(TS)))
        print('TF: {0:.2f} \u00B1 {1:.2f} horas (IC 95%)'.format(np.mean(TF_), calc_ic(TF)))
        print('TA: {0:.2f} \u00B1 {1:.2f} horas (IC 95%)'.format(np.mean(TA_), calc_ic(TA)))
        print('USO:{0:.2f}% \u00B1 {1:.2f}%  (IC 95%)'.format(np.mean(USO) * 100, calc_ic(USO) * 100))
        print("=" * comprimento_linha, end="\n")

        #Calculando os resultados
            #Sempre que houver uma saída de invidiuo
        # NS = Média de individuos - S
        # NA = Fila para o recurso (Salvar informações nos dados do recurso) - .count
        # NF = Tamanho da Fila .queue


        #Média de cada entidade
        #TS: tempo no sistema (valor calculado por entidade)
        #TA: Tempo de atendimento
        #TF: Tempo em fila







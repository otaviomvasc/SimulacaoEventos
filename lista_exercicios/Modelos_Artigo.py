import simpy
import random
import numpy as np
from scipy import stats
import matplotlib
import matplotlib.pyplot as plt
import plotly.express as px
import pandas as pd
from copy import deepcopy
import math

""" 
Temos 3 tipos de estatisticas:
Da Simulação (NS)
Dos recursos (NA - Individuos em fila e NF)

Então a tentativa é fazer a captura para cada entidade/recurso e depois juntar tudo no final.
Também passei a estatística para uma classe para ficar mais fácil de usar em outros codigos.
"""
#TODO: Passar essas classes para abstratas e deixar como fixo!!!

class Simulacao():
    def __init__(self, distribuicoes, imprime, recursos, dist_prob, tempo, necessidade_recursos):
        self.env = simpy.Environment()
        self.distribuicoes = distribuicoes
        self.entidades = Entidades()
        self.recursos_est = Recursos(env=self.env,recursos=recursos)  # Foi necessário criar 2x de recursos. Pensar algo melhor!
        self.recursos = self.recursos_est.recursos
        self.estatisticas_sistema = EstatisticasSistema()
        self.imprime_detalhes = imprime
        self.dist_probabilidade = dist_prob
        self.tempo = tempo
        self.necessidade_recursos = necessidade_recursos


    def comeca_simulacao(self):
        self.env.process(self.gera_chegadas())
        #self.env.run(until=self.tempo) #valor de teste para desenvolvimento!!!!

    def gera_chegadas(self):
        def define_time_slot(hora_chegada, dia_atual):
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

            hora_chegada = hora_chegada - (3600*13.5 * dia_atual)#Definição hora chegada para rodar por mais dias
            coef = 3600  # TODO: Verificar unidade de tempo da simulação
            time_slot_1 = [0, 1.5 * coef, "time_slot_1"]
            time_slot_2 = [1.5 * coef, 3.5 * coef, "time_slot_2"]
            time_slot_3 = [3.5 * coef, 6 * coef, "time_slot_3"]
            time_slot_4 = [6 * coef, 8 * coef, "time_slot_4"]
            time_slot_5 = [8 * coef, 10 * coef, "time_slot_5"]
            time_slot_6 = [10 * coef, 12 * coef, "time_slot_6"]
            time_slot_7 = [12 * coef, 13.5 * coef, "time_slot_7"]

            slots = [time_slot_1, time_slot_2, time_slot_3, time_slot_4, time_slot_5, time_slot_6, time_slot_7]


            return next(slot[2] for slot in slots if hora_chegada >= slot[0] and hora_chegada <= slot[1])  # iterator para minimizar tempo de busca!



        time_slot = define_time_slot(self.env.now, 0)
        while True:

            yield self.env.timeout(self.distribuicoes(processo='chegada',slot=time_slot))
            dia = np.floor(self.env.now / (3600*13.5)) #Forma para calculo de hora de chegada dos dias!!
            time_slot = define_time_slot(self.env.now, dia)

            #nome = 'entidade' + " " + str(self.estatisticas_sistema.chegadas)
            self.estatisticas_sistema.computa_chegadas(momento=self.env.now)
            entidade_individual = Entidade_individual(nome='entidade' + " " + str(self.estatisticas_sistema.chegadas))
            entidade_individual.entrada_sistema = self.env.now
            entidade_individual.time_slot = time_slot #salvar para usar nas próximas decisões - Verificar necessidade!
            self.entidades.lista_entidades.append(entidade_individual)


            #Decisão de qual fluxo (Imagem ou Ultrassom a entidade irá seguir)
            aleatorio = random.random() #debug!!
            if self.distribuicoes(processo='decisao_fluxo', slot=entidade_individual.time_slot) <= aleatorio:
                if self.imprime_detalhes:
                    print(f"{self.env.now}: {entidade_individual.nome} Inicia a operação e vai para Check_in Imagem")
                self.env.process(self.check_in(entidade_individual=entidade_individual, recurso="check_in_imagem"))
            else:
                if self.imprime_detalhes:
                    print(f"{self.env.now}: {entidade_individual.nome} Inicia a operação e vai para Check_in Ultrassom")
                self.env.process(self.check_in(entidade_individual=entidade_individual, recurso="check_in_ultrassom"))

    def check_in(self, entidade_individual, recurso):
        def define_exame(origem):
            processos = self.dist_probabilidade.get(origem)
            aleatorio = random.random()
            return next(pr[2] for pr in processos if aleatorio >= pr[0] and aleatorio <= pr[1])

        entidade_individual.entra_fila = self.env.now

        request = self.recursos[recurso].request()
        #Seize/request
        yield request
        entidade_individual.processo_atual = recurso
        if self.imprime_detalhes:
            print(f'{self.env.now}: Atendente {recurso} começou o atendimento de {entidade_individual.nome}')

        #estatisticas
        entidade_individual.sai_fila = self.env.now
        entidade_individual.entra_processo = self.env.now #TODO: esse valor é sempre igual ao sai fila. Logo pode ser uma variável só!


        #delay
        tempo = self.distribuicoes(processo=recurso)
        yield self.env.timeout(tempo)

        #release
        #TODO: em casos de recursos com capacidade maior que 1 o tempo de inicio da utilização deve estar ligado ao request, e não a classe daquele recurso!!
        self.recursos_est.fecha_ciclo(nome_recurso=recurso, momento=self.env.now, inicio_utilizacao=request.usage_since)
        self.recursos[recurso].release(request)


        #estatisticas
        entidade_individual.sai_processo = self.env.now

        #Fecha estatisticas de entidade e recurso deste processo!!
        entidade_individual.fecha_ciclo(processo=recurso)

        #Decide próximo processo!

        if recurso == "check_in_ultrassom":
            aleat = random.random() #Aleatoriedade de entidades que fazer check-in numa zona mas vão realizar outro exame!
            if aleat >= 0.15:
                if self.imprime_detalhes:
                    print(f'{self.env.now}: {entidade_individual.nome} foi para o ultrassom')
                self.env.process(self.realiza_exame(exame="Ultrasound", entidade_individual=entidade_individual))
            else:
                proximo_exame = define_exame(origem="check_in_imagem")
                if self.imprime_detalhes:
                    print(f'{self.env.now}: {entidade_individual.nome} fez check-in no ultrassom mas foi para {proximo_exame}')
                self.env.process(self.realiza_exame(exame=proximo_exame, entidade_individual=entidade_individual))
        else:
            aleat = random.random() #Aleatoriedade de entidades que fazer check-in numa zona mas vão realizar outro exame!
            if aleat >= 0.15:
                proximo_exame = define_exame(origem="check_in_imagem")
                if self.imprime_detalhes:
                    print(f'{self.env.now}: {entidade_individual.nome} foi para o {proximo_exame}')
                self.env.process(self.realiza_exame(exame=proximo_exame, entidade_individual=entidade_individual))
            else:
                if self.imprime_detalhes:
                    print(f'{self.env.now}: {entidade_individual.nome} fez check-in na Imagem mas foi para o ultrassom!')
                self.env.process(self.realiza_exame(exame="Ultrasound", entidade_individual=entidade_individual))

    def realiza_exame(self, exame, entidade_individual):
        def define_exame(origem):
            processos = self.dist_probabilidade.get(origem)
            aleatorio = random.random()
            return next(pr[2] for pr in processos if aleatorio >= pr[0] and aleatorio <= pr[1])

        """
        ATENÇÃO!!!!!!!
        Mesmo código do método acima, com excessão da decisão. tentar unificar isso!
        """

        recurso = exame #tentativa de deixar explicativo
        entidade_individual.entra_fila = self.env.now

        #TODO: Formas de se fazer N requests juntos:
        # Seize/request

        requests_recursos = [self.recursos[recurso_humando].request() for recurso_humando in self.necessidade_recursos[exame]]
        for request in requests_recursos:
            yield request

        entidade_individual.processo_atual = exame
        if self.imprime_detalhes:
            print(f'{self.env.now}:  Entidade: {entidade_individual.nome} começou o Exame{exame}')

        # estatisticas - Alterar para todos os recursos e verificar como vai ficar para situações com recursos de mais capacidades!
        entidade_individual.sai_fila = self.env.now
        entidade_individual.entra_processo = self.env.now  # TODO: esse valor é sempre igual ao sai fila. Logo pode ser uma variável só!

        # delay
        yield self.env.timeout(self.distribuicoes(processo=recurso))

        if exame == "MRI": #TODO: Confirmar se é necessário zerar as estatisticas quando o paciente repete a ressonância.
            aleat = random.random()
            while aleat <= 0.32:
                if self.imprime_detalhes:
                    print(f'{self.env.now}: {entidade_individual} vai repetir a MRI')#Repete exame - IF se só repetir uma vez ou while se puder repetir mais de uma!!
                yield self.env.timeout(self.distribuicoes(processo=recurso)) #TODO: Só repete a ressonância uma vez?
                aleat = random.random()
                #self.realiza_exame(exame="MRI", entidade_individual=entidade_individual)
        # release

        for i in range(len(self.necessidade_recursos[exame])):
            self.recursos_est.fecha_ciclo(nome_recurso=self.necessidade_recursos[exame][i], momento=self.env.now, inicio_utilizacao=requests_recursos[i].usage_since)
            self.recursos[self.necessidade_recursos[exame][i]].release(requests_recursos[i])


        # estatisticas
        entidade_individual.sai_processo = self.env.now

        #Fecha estatística de entidade deste processo!!
        entidade_individual.fecha_ciclo(processo=recurso)


        proximo_exame = define_exame(origem=exame)
        if proximo_exame == "Exit":
            entidade_individual.saida_sistema = self.env.now
            entidade_individual.fecha_ciclo(processo="saida_sistema")
            self.estatisticas_sistema.computa_saidas(self.env.now)
            if self.imprime_detalhes:
                print(f'{self.env.now}: Entidade {entidade_individual.nome} saiu do sistema!')
        else:
            self.env.process(self.realiza_exame(exame=proximo_exame, entidade_individual=entidade_individual))
            if self.imprime_detalhes:
                print(f'{self.env.now}: Entidade {entidade_individual.nome} vai realizar outro exame: {proximo_exame}!')

    def finaliza_todas_estatisticas(self):
        self.entidades.fecha_estatisticas()
        self.recursos_est.fecha_estatisticas()
        self.estatisticas_sistema.fecha_estatisticas()

    def gera_graficos(self):
        def define_time_slot(hora_chegada, dia_atual):
            hora_chegada = hora_chegada - (3600*13.5 * dia_atual)#Definição hora chegada para rodar por mais dias
            coef = 3600  # TODO: Verificar unidade de tempo da simulação
            time_slot_1 = [0, 1.5 * coef, "time_slot_1"]
            time_slot_2 = [1.5 * coef, 3.5 * coef, "time_slot_2"]
            time_slot_3 = [3.5 * coef, 6 * coef, "time_slot_3"]
            time_slot_4 = [6 * coef, 8 * coef, "time_slot_4"]
            time_slot_5 = [8 * coef, 10 * coef, "time_slot_5"]
            time_slot_6 = [10 * coef, 12 * coef, "time_slot_6"]
            time_slot_7 = [12 * coef, 13.5 * coef, "time_slot_7"]

            slots = [time_slot_1, time_slot_2, time_slot_3, time_slot_4, time_slot_5, time_slot_6, time_slot_7]


            return next(slot[2] for slot in slots if hora_chegada >= slot[0] and hora_chegada <= slot[1])  # iterator para minimizar tempo de busca!

        def calcula_time_slot(hora_chegada, define_time_slot):
            dia = np.floor(hora_chegada['T'] / (3600 * 13.5))  # Forma para calculo de hora de chegada dos dias!!
            ts = define_time_slot(hora_chegada['T'], dia)
            return ts

        time_slots = pd.unique(self.entidades.df_entidades['time_slot'])
        self.recursos_est.df_estatisticas_recursos['time_slot'] = self.recursos_est.df_estatisticas_recursos.apply(lambda x: calcula_time_slot(x.T, define_time_slot), axis=1 )

        # GRÁFICOS DE UTILIZAÇÃO
        fig = px.line(self.recursos_est.df_estatisticas_recursos,
                      x="T", y="utilizacao", color="recurso", title='Grafico de Utilizacao Total dos Recursos')
        fig.show()

        for time_s in time_slots:
            df_recursos = self.recursos_est.df_estatisticas_recursos.loc[
                self.recursos_est.df_estatisticas_recursos.time_slot == time_s]
            fig = px.line(df_recursos,
                          x="T", y="utilizacao", color="recurso",
                          title=f'Grafico de Utilizacao Total dos Recursos no {time_s}')
            fig.show()

        #GRÁFICOS TEMPO DE FILA
        df_tempo_fila_time_slot = self.entidades.df_entidades.groupby(by=['time_slot']).agg({"tempo_fila":"mean"}).reset_index()
        fig = px.bar(df_tempo_fila_time_slot,x='time_slot', y="tempo_fila", title='Media de tempo em fila por time_slot')
        fig.show()

        df_tempo_fila_time_slot_processo = self.entidades.df_entidades.groupby(by=['time_slot', 'processo']).agg({"tempo_fila":"mean"}).reset_index()
        fig = px.bar(df_tempo_fila_time_slot_processo,x='time_slot', y="tempo_fila", color='processo', title='Media de tempo em fila por time_slot e por processo')
        fig.show()

class EstatisticasSistema():
    def __init__(self):
        self.chegadas = 0
        self.saidas = 0
        self.WIP = 0
        self.df_estatisticas_simulacao = pd.DataFrame()
        self.entidades_sistema = list()
        self.df_entidades_brutas = pd.DataFrame()

    def fecha_estatisticas(self):
        print(f'Chegadas: {self.chegadas}')
        print(f'Saídas: {self.saidas}')
        print(f'WIP: {self.WIP} ')
        entidades_sistema = np.mean([rec["WIP"] for rec in self.entidades_sistema]) #TODO: Verificar como esse cálculo ta sendo feito!!
        dict_aux = {"Chegadas": self.chegadas,
                    "Saidas": self.saidas,
                    "WIP": self.WIP,
                    "Media_Sistema": entidades_sistema}

        self.df_entidades_brutas = pd.DataFrame(self.entidades_sistema)
        self.df_estatisticas_simulacao = pd.DataFrame([dict_aux])

    def computa_chegadas(self, momento):
        #TODO: Adaptar para computar chegadas de mais de um indivíduo!!!!
        self.chegadas += 1
        self.WIP += 1
        self.entidades_sistema.append({"discretizacao": momento,
                                       "WIP": self.WIP,
                                       "processo": "chegada"})

    def computa_saidas(self, momento):
        self.saidas += 1
        self.WIP -= 1
        self.entidades_sistema.append({"discretizacao": momento,
                                       "WIP": self.WIP,
                                       "processo": "saida"})

class Entidades:
    def __init__(self):
        self.lista_entidades = list()
        self.df_entidades = pd.DataFrame()
        self.resultados_entidades = pd.DataFrame()

    def fecha_estatisticas(self):
        def printa_media(coluna):
            res = round(np.mean(self.df_entidades[coluna]),2)
            print(f'{coluna} : {res/60} minutos')

        tempo_sistema = list() #TODO:Loop está muito lento. Melhorar!
        self.df_entidades = pd.DataFrame([est for ent in self.lista_entidades for est in ent.estatisticas])


        dict_estatisticas_calculadas = {"tempo_sistema":np.mean([ent.saida_sistema - ent.entrada_sistema for ent in self.lista_entidades if ent.saida_sistema > 1]),
        "tempo_processamento":round(np.mean(self.df_entidades['tempo_processando']),2),
        "tempo_fila" :round(np.mean(self.df_entidades['tempo_fila']),2)}
        printa_media(coluna='tempo_processando')
        printa_media(coluna='tempo_fila')
        print(f'TS: { dict_estatisticas_calculadas["tempo_sistema"] / 60} minutos') #TODO: Prof considerou a média do tempo que as máquinas sairam da manutenção, já que o sistema é continuo. Confirmar como fica em sistemas não-continuos
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
        self.time_slot = None
        self.tempo_sistema = 0
        self.processo_atual: str

    def fecha_ciclo(self, processo):
        if not processo == "saida_sistema":
            aux_dados = {"entidade": self.nome,
                         "processo": processo,
                         "entra_fila": self.entra_fila,
                         "sai_fila": self.sai_fila,
                         "tempo_fila": self.sai_fila - self.entra_fila,
                         "entra_processo": self.sai_fila,
                         "sai_processo": self.sai_processo,
                         "tempo_processando": self.sai_processo - self.entra_processo,
                         "time_slot" : self.time_slot}

            self.estatisticas.append(aux_dados)
            self.entra_fila: float = 0.0
            self.sai_fila: float = 0.0
            self.entra_processo: float = 0.0
            self.sai_processo: float = 0.0

        else:
            self.tempo_sistema = self.saida_sistema - self.entrada_sistema

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
            rec_aux.tempo_utilizacao_recurso = 0
            #rec_aux.fecha_ciclo = fecha_ciclo
            recursos_dict[rec] = rec_aux

        return recursos_dict

    def fecha_ciclo(self, nome_recurso, momento, inicio_utilizacao):
        recurso = self.recursos[nome_recurso]
        recurso.tempo_utilizacao_recurso += round(momento - inicio_utilizacao)
        #inicio_utilizacao = request.usage_since
        #TODO: preciso usar o momento ou apenas o fecha_utilizacao_recurso ja tem esse dado, visto que será chamado após processo
        dict_aux = {"recurso": nome_recurso,
                    "inicia_utilizacao_recurso": inicio_utilizacao,
                    "finaliza_utilizacao_recurso": momento,
                    "tempo_utilizacao_recurso": momento - inicio_utilizacao,
                    "utilizacao": recurso.tempo_utilizacao_recurso/(recurso._capacity * momento),
                    "T": momento,
                    "em_atendimento": recurso.count,
                    "tamanho_fila": len(recurso.queue)
                    }

        recurso.estatisticas.append(dict_aux)

    def fecha_estatisticas(self):
        for nome, rec in self.recursos.items():
            df_aux = pd.DataFrame(rec.estatisticas)
            print(f'Utilizacao Média do recurso {nome}: {round(np.mean(df_aux["utilizacao"]),2)*100}%')
            print(f'Média da Fila do recurso {nome}: {round(np.mean(df_aux["tamanho_fila"]) / 60)} minutos')
            df_aux['recurso'] = nome
            self.df_estatisticas_recursos = pd.concat([self.df_estatisticas_recursos, df_aux])
        b=0

class CorridaSimulacao():
    def __init__(self, replicacoes, simulacao: Simulacao, duracao_simulacao, periodo_warmup):
        self.replicacoes: int = replicacoes
        self.df_estatisticas_entidades = pd.DataFrame()  #Lista com cada estatística de cada rodada
        self.df_estatisticas_sistema = pd.DataFrame()
        self.df_estatisticas_recursos = pd.DataFrame()
        self.df_estatistcas_sistemas_brutos = pd.DataFrame()
        self.duracao_simulacao = duracao_simulacao
        self.simulacoes = [deepcopy(simulacao) for i in range(replicacoes)]
        self.periodo_warmup = periodo_warmup
    def roda_simulacao(self):
        for n_sim in range(len(self.simulacoes)):
            print(f'Simulação {n_sim + 1}')
            print('-' * 150)
            simulacao = self.simulacoes[n_sim]
            simulacao.comeca_simulacao()
            simulacao.env.run(until=simulacao.tempo)
            simulacao.finaliza_todas_estatisticas()
            if len(self.simulacoes) == 1:
                simulacao.gera_graficos()

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
            #junção dos dados das entidades
            df_entidades = self.simulacoes[n_sim].entidades.df_entidades
            df_entidades = df_entidades.loc[df_entidades.entra_processo > self.periodo_warmup]
            df_entidades['Replicacao'] = n_sim + 1


            #junção dos dados das estatísticas do sistema
            df_sistema = self.simulacoes[n_sim].estatisticas_sistema.df_estatisticas_simulacao
            df_sistema['Replicacao'] = n_sim + 1

            df_sistema_bruto = self.simulacoes[n_sim].estatisticas_sistema.df_entidades_brutas
            df_sistema_bruto = df_sistema_bruto.loc[df_sistema_bruto.discretizacao > self.periodo_warmup]
            df_sistema_bruto['Replicacao'] = n_sim + 1

            #junção dos dados das estatísticas dos recursos
            df_recursos = self.simulacoes[n_sim].recursos_est.df_estatisticas_recursos
            df_recursos = df_recursos.loc[df_recursos['T'] > self.periodo_warmup]
            df_recursos['Replicacao'] = n_sim + 1


            self.df_estatisticas_entidades = pd.concat([self.df_estatisticas_entidades, df_entidades])
            self.df_estatisticas_sistema = pd.concat([self.df_estatisticas_sistema,df_sistema ])
            self.df_estatisticas_recursos = pd.concat([self.df_estatisticas_recursos, df_recursos])
            self.df_estatistcas_sistemas_brutos = pd.concat([self.df_estatistcas_sistemas_brutos, df_sistema_bruto])


        TS = [(ent.saida_sistema - ent.entrada_sistema)/60 for sim in self.simulacoes for ent in sim.entidades.lista_entidades if ent.saida_sistema > 1]
        TS2 = [(ent.saida_sistema - ent.entrada_sistema)/60 if ent.saida_sistema > 1 else (self.duracao_simulacao - ent.entrada_sistema) for sim in self.simulacoes for ent in sim.entidades.lista_entidades]
        TA = self.df_estatisticas_entidades['tempo_processando']
        TF = self.df_estatisticas_entidades['tempo_fila']
        NA = self.df_estatisticas_recursos['em_atendimento']
        NA2 = self.df_estatisticas_recursos.groupby(by=["recurso"]).agg({'em_atendimento': 'mean'}).reset_index().em_atendimento
        NF = self.df_estatisticas_recursos['tamanho_fila']
        NF2 = self.df_estatisticas_recursos.groupby(by=["recurso"]).agg({'tamanho_fila': 'mean'}).reset_index().tamanho_fila
        NS = self.df_estatistcas_sistemas_brutos["WIP"]
        USO = self.df_estatisticas_recursos['utilizacao']

        TS_ = round(np.mean(TS)/60, 2)
        TS2_ = round(np.mean(TS2)/60,2)
        TA_ = round(np.mean(self.df_estatisticas_entidades['tempo_processando'])/60,2)
        TF_ = round(np.mean(self.df_estatisticas_entidades['tempo_fila'])/60,2)
        NA_ = round(np.mean(self.df_estatisticas_recursos['em_atendimento'])/60,2)
        NA2_ = round(sum(self.df_estatisticas_recursos.groupby(by=["recurso"]).agg({'em_atendimento': 'mean'}).reset_index().em_atendimento),2)
        NF_ = round(np.mean(self.df_estatisticas_recursos['tamanho_fila']),2)
        NF2_ = round(sum(self.df_estatisticas_recursos.groupby(by=["recurso"]).agg({'tamanho_fila': 'mean'}).reset_index().tamanho_fila),2)
        NS_ = round(np.mean(self.df_estatistcas_sistemas_brutos["WIP"]), 2)
        USO_= round(np.mean(self.df_estatisticas_recursos['utilizacao']),2)


        df_aux = self.df_estatistcas_sistemas_brutos.groupby(by=['processo', "Replicacao"]).agg({"WIP": "count"}).reset_index()
        chegadas = np.mean(df_aux.loc[df_aux.processo == 'chegada']['WIP'])
        saidas = np.mean(df_aux.loc[df_aux.processo == 'saida']['WIP'])
        df_wip = self.df_estatistcas_sistemas_brutos.groupby(by=["Replicacao"]).agg({"WIP": "mean"}).reset_index()
        WIP = round(np.mean([self.df_estatistcas_sistemas_brutos["WIP"]]))
        print(f'Chegadas: {chegadas} entidades')
        print(f'Saidas:   {saidas} entidades')
        print(f'WIP:      {WIP} entidades')
        print()
        comprimento_linha = 100
        print("=" * comprimento_linha)
        print("Indicadores de Desempenho do Sistema", end="\n")
        print("=" * comprimento_linha)

        #TODO: Preciso calcular recursos/entidades por processo ?
        print('NS: {0:.2f} \u00B1 {1:.2f} entidades (IC 95%)'.format(np.mean(NS_), calc_ic(NS)))
        print('NF: {0:.2f} \u00B1 {1:.2f} entidades (IC 95%)'.format(np.mean(NF_), calc_ic(NF)))
        print('NF: {0:.2f} \u00B1 {1:.2f} entidades (IC 95%) - FORMA DE CÁLCULO 2'.format(np.mean(NF2_), calc_ic(NF2)))
        print('NA: {0:.2f} \u00B1 {1:.2f} entidades (IC 95%)'.format(np.mean(NA_), calc_ic(NA)))
        print('NA: {0:.2f} \u00B1 {1:.2f} entidades (IC 95%) - FORMA DE CÁLCULO 2'.format(np.mean(NA2_), calc_ic(NA2)))
        print('TS: {0:.2f} \u00B1 {1:.2f} minutos (IC 95%)'.format(np.mean(TS_), calc_ic(TS)))
        print('TS: {0:.2f} \u00B1 {1:.2f} minutos (IC 95%) - FORMA DE CÁLCULO CONSIDERANDO WIPS'.format(np.mean(TS2_), calc_ic(TS2)))
        print('TF: {0:.2f} \u00B1 {1:.2f} minutos (IC 95%)'.format(np.mean(TF_), calc_ic(TF)))
        print('TA: {0:.2f} \u00B1 {1:.2f} minutos (IC 95%)'.format(np.mean(TA_), calc_ic(TA)))
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







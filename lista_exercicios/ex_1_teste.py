import simpy
import random
import numpy as np
import scipy
import matplotlib
import matplotlib.pyplot as plt
from random import expovariate, seed
from scipy import stats

from Modelos import Estatistica_v1, Entidades,Entidade_individual, Recursos, CorridaSimulacao, Simulacao






def distribuicoes(tipo):
    taxa_chegadas=1         # por hora
    taxa_operacao=1/(3*24)  # por hora
    taxa_manutencao=1/24    # por hora
    return {
        'chegada': expovariate(taxa_chegadas),
        'operacao': expovariate(taxa_operacao),
        'manutencao': expovariate(taxa_manutencao)
    }.get(tipo,0.0)


if __name__ == '__main__':
    seed(1)
    CAP_EQUIPE = 1
    qntd_chegadas = 4
    imprime = True
    duracao_da_simulacao = 1000


    #Teste de estrutura genérica para criação de recursos. Não sei se vai dar certo
    recursos = {'equipes': 1}
    #TODO: Criar outra classe chamada Simulação para controlar a quantidade de Simulações
    Simulacao = Simulacao(
                          distribuicoes=distribuicoes,
                          CAP_EQUIPE=CAP_EQUIPE,
                          qntd_chegadas=qntd_chegadas,
                          imprime=imprime,
                          recursos=recursos
                          )


    Corrida_Simulacao = CorridaSimulacao(replicacoes=5,
                                         simulacao=Simulacao,
                                         duracao_simulacao=1000)

    Corrida_Simulacao.roda_simulacao()
    # Simulacao.comeca_simulacao()
    # Simulacao.env.run(duracao_da_simulacao) #TODO: Verificar se da pra passar para dentro do self
    # Simulacao.entidades.fecha_estatisticas()
    # Simulacao.estatisticas.computa_estatisticas(1)
    # Simulacao.estatisticas.publica_estatisticas()
    # b=0
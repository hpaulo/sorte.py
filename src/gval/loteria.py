import random

class LoteriaNaoSuportada(Exception):
    def __init__(self, nome):
        self.nome = nome
        Exception.__init__(self, nome)

class QuantidadeInvalida(Exception):
    def __init__(self, valor):
        self.valor = valor
        Exception.__init__(self, valor)


APELIDOS = {
    'sena': 'megasena',
}

LOTERIAS = {
    'quina': {'validos': (5, 80), 'faixa': (1, 80)},
    'megasena': {'validos': (6, 60), 'faixa': (1, 60), 'nome': "Mega-Sena"},
}

class Loteria:
    def __init__(self, nome):
        try:
            c = LOTERIAS[APELIDOS.get(nome, nome)]
        except KeyError, err:
            raise LoteriaNaoSuportada(err.message)
        else:
            self.nome = c.get('nome', nome.title())
            self.qmin = c['validos'][0]
            self.qmax = c['validos'][1]
            self.range = xrange(c['faixa'][0], c['faixa'][1] + 1)

    def gerar_aposta(self, quant=None):
        qmin, qmax = self.qmin, self.qmax
        if quant is None:
            quant = qmin
        if not (qmin <= quant <= qmax):
            raise QuantidadeInvalida(quant)
        result = random.sample(self.range, quant)
        return tuple(sorted(result))

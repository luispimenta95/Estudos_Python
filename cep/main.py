import requests as req
cep_input = input('Digite um CEP\n')
if len(cep_input) !=8:
    print("CEP " + cep_input + " inválido")
    exit()
requisicao = req.get(f'https://viacep.com.br/ws/{cep_input}/json/')
endereco = requisicao.json()
if 'erro' not in endereco:
    print('CEP ENCONTRADO\n')
    print(endereco)
else:
    print("CEP " + cep_input + " inválido")
    exit()
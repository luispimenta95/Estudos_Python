import sys
import functions


def main():

    if not functions.deve_executar():
        print("Hoje não é dia de execução do relatório.")
        sys.exit()

    dados = functions.gerar_relatorio()

    mensagem = functions.montar_mensagem(dados)

    functions.sendMessageTelegram(mensagem)


if __name__ == "__main__":
    main()
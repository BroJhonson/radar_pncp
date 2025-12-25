# backend/teste_email.py
import os
import requests
from dotenv import load_dotenv

load_dotenv()

def testar_mailgun():
    domain = os.getenv('MAILGUN_DOMAIN')
    api_key = os.getenv('MAILGUN_API_KEY')
    # Use um remetente do mesmo domínio configurado
    sender = os.getenv('EMAIL_REMETENTE', f'Teste Finnd <postmaster@{domain}>')
    
    # COLOQUE SEU EMAIL PESSOAL AQUI PARA TESTAR
    destinatario = "brucedebruine@gmail.com" 

    print(f"--- DIAGNÓSTICO MAILGUN ---")
    print(f"1. Domínio: {domain}")
    print(f"2. API Key Carregada? {'SIM' if api_key else 'NÃO'}")
    print(f"3. Remetente: {sender}")
    print(f"4. Enviando para: {destinatario}")

    url = f"https://api.mailgun.net/v3/{domain}/messages"
    
    try:
        response = requests.post(
            url,
            auth=("api", api_key),
            data={
                "from": sender,
                "to": [destinatario],
                "subject": "Teste de Configuração - Finnd",
                "text": "Se você recebeu isso, o Mailgun está funcionando perfeitamente!"
            }
        )

        print(f"\n--- RESULTADO DA REQUISIÇÃO ---")
        print(f"Status Code: {response.status_code}")
        print(f"Resposta: {response.text}")

        if response.status_code == 200:
            print("\n✅ SUCESSO! O problema não é credencial.")
        elif response.status_code == 401:
            print("\n❌ ERRO 401: API Key incorreta ou não autorizada.")
        elif response.status_code == 404:
            print("\n❌ ERRO 404: Domínio incorreto (ou URL da API errada). Verifique se é US ou EU.")
        else:
            print("\n❌ ERRO: Verifique a mensagem acima.")

    except Exception as e:
        print(f"Erro fatal de conexão: {e}")

if __name__ == "__main__":
    testar_mailgun()
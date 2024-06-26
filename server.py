import json
import requests
from bs4 import BeautifulSoup
import pandas as pd
import io

PASSWORD = 'password123'

def lambda_handler(event, context):
    url_base = event['queryStringParameters']['url']
    password = event['queryStringParameters']['password']

    if password != PASSWORD:
        return {
            'statusCode': 401,
            'body': 'Unauthorized: senha incorreta'
        }

    if not url_base:
        return {
            'statusCode': 400,
            'body': 'Bad Request: parâmetro url_base faltando'
        }

    dados_imoveis = scrape_imoveis(url_base)
    excel_data = salvar_excel(dados_imoveis)

    return {
        'statusCode': 200,
        'headers': {
            'Content-Disposition': 'attachment; filename="dados_imoveis.xlsx"',
            'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        },
        'body': excel_data.read(),
        'isBase64Encoded': True
    }

def obter_numero_paginas(url_base):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    response = requests.get(url_base, headers=headers)
    if response.status_code != 200:
        print(f'Falha ao carregar a página: {response.status_code}')
        return 0

    soup = BeautifulSoup(response.content, 'html.parser')

    paginacao = soup.find('ul', {'data-cy': 'frontend.search.base-pagination.nexus-pagination'})
    if not paginacao:
        return 1

    paginas = paginacao.find_all('li')
    total_paginas = int(paginas[-2].text.strip()) if paginas else 1
    return total_paginas

def scrape_imoveis(url_base):
    dados_imoveis = []
    total_paginas = obter_numero_paginas(url_base)

    for pagina in range(1, total_paginas + 1):
        url = f'{url_base}&page={pagina}'
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            print(f'Falha ao carregar a página {pagina}: {response.status_code}')
            continue

        soup = BeautifulSoup(response.content, 'html.parser')

        articles = soup.find_all('article', {'data-cy': 'listing-item'})

        for article in articles:
            try:
                localizacao = article.find('p', class_='css-1dvtw4c eejmx80').text.strip() if article.find('p',
                                                                                                           class_='css-1dvtw4c eejmx80') else 'N/A'
                preco = article.find('span', class_='css-1uwck7i evk7nst0').text.strip() if article.find('span',
                                                                                                         class_='css-1uwck7i evk7nst0') else 'N/A'
                tipologia = article.find('dt', string='Tipologia').find_next_sibling('dd').text.strip() if article.find(
                    'dt', string='Tipologia') else 'N/A'
                metros_quadrados = article.find('dt', string='Zona').find_next_sibling('dd').text.strip() if article.find(
                    'dt', string='Zona') else 'N/A'
                preco_por_metro_quadrado = article.find('dt', string='Preço por metro quadrado').find_next_sibling(
                    'dd').text.strip() if article.find('dt', string='Preço por metro quadrado') else 'N/A'

                link = article.find('a', {'data-cy': 'listing-item-link'})['href'] if article.find('a', {
                    'data-cy': 'listing-item-link'}) else 'N/A'
                link_completo = f'https://www.imovirtual.com{link}' if link != 'N/A' else 'N/A'

                dados_imovel = {
                    'preço': preco,
                    'localização': localizacao,
                    'tipologia': tipologia,
                    'm2': metros_quadrados,
                    'preço por m2': preco_por_metro_quadrado,
                    'link': link_completo
                }

                dados_imoveis.append(dados_imovel)
            except Exception as e:
                print(f'Erro ao processar um artigo na página {pagina}: {e}')

    return dados_imoveis

def salvar_excel(dados):
    df = pd.DataFrame(dados)

    output = io.BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    df.to_excel(writer, index=False, sheet_name='Dados Imóveis')
    writer.save()
    output.seek(0)
    
    return output


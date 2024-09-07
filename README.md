# Techjobmatcher

Esta API encontra a vaga de TI mais relevante para a sua pesquisa.

# Como instalar

A seguinte lista de requirements deve ser instalada antes de rodar a API:
```bash
fastapi
uvicorn
pytest
scikit-learn
httpx
pandas
```

## Rodando o projeto com docker

```bash
docker build -t techjobmatcher .
docker run -d -p 8435:8435 techjobmatcher
```
# Como funciona

Após receber uma query via endpoint no seguinte formato: http://localhost:8435/query?query={palavras que quer pesquisa}, a API Tech Job Matcher vai procurar qual a vaga mais relevante no banco de dados com base na relevância TF-IDF (Term Frequency-Inverse Document Frequency), um método que avalia a importância de uma palavra em um documento em relação a um conjunto de documentos. A TF-IDF dá mais peso a palavras que são frequentes em um documento, mas raras em outros documentos, ajudando a identificar palavras chave para cada vaga. A acurácia é melhorada devido ao uso de uma lista de stop words (palavras que não agregam significado) que são ignoradas no cálculo. Também é usado um sistema de Similaridade do Cosseno, que calcula a similaridade entre o vetor da consulta e os vetores das vagas de emprego. A similaridade é baseada no ângulo entre os vetores, permitindo comparar quão similares são as descrições de vagas com a consulta.

# De onde vieram os dados

Eu fiz um Web Scrapper de página dinâmica (com Java Script ativo e dados mudando em tempo real) com Selenium. O Web Scrapper (raspador de dados da internet) foi feito em Python especificamente para pegar dados do site de vagas Indeed, que permite algumas centenas de raspagens gratuitas por dia. Os dados dessa base de dados vieram especificamente desta pesquisa no indeed: https://br.indeed.com/jobs?q=desenvolvedor+de+software&l=&from=searchOnHP&vjk=918f94e6e372b669 . Com isso, minha base de dados é única, pois o arquivo que tenho não baixei pronto de lugar algum, eu de fato investi horas para fazer um web scrapper que atendesse minhas necessidades.

# Como testar

É possível digitar http://10.103.0.28:8435/query?query={palavras que quer pesquisar} na web e escolher a lista de palavras que for mais interessante para você, mas aqui estão alguns exemplos e possíveis resultados:

Um teste que retorna pelo menos 10 resultados:
    [/query?query=html](http://10.103.0.28:8435/query?query=html)
Um teste que retorna entre 1 e 10 resultados:
    [/query?query=python java django](http://10.103.0.28:8435/query?query=python java django)
Um teste que retorna um resultado não óbvio:
    [/query?query=Desenvolvedor de software com experiência em fintechs](http://10.103.0.28:8435/query?query=Desenvolvedor de software com experiência em fintechs)
    Obs: Considerei como não óbvio pois os resultados de fato abordam a "experiência em fintech" ao invés de pegar vagas genéricas de "Desenvolvedor" e "Software".

# Relevância do tema

Existem muitas áreas de atuação possível em TI, então decidi ajudar a entender a descrição das vagas que são mais relevantes para as habilidades e ou ferramentas que o Dev precisa. Com base nos resultados da minha API, é mais fácil entender o que é cobrado nas ofertas de emprego que se adequam aos seus interesses.

## Autor

Henrique Rocha Bomfim

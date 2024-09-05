from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import csv
import threading
from queue import Queue
import time
import re
import random

# Configurações do Selenium para o navegador Brave
brave_options = Options()
brave_options.binary_location = r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"
brave_service = Service(ChromeDriverManager().install())  # Atualiza automaticamente o WebDriver para Chrome

# URL base para o Indeed
base_url = "https://br.indeed.com/jobs?q=desenvolvedor+de+software&l=&from=searchOnHP&vjk=918f94e6e372b669"

# Lista para armazenar os dados das vagas
jobs_data = []
job_count = 0
max_jobs = 1000
available_jobs = 0

# Configuração da fila para multi-threading
job_queue = Queue()

# Controle de abas abertas
max_tabs = 10
open_drivers = []

# Função que realiza o scraping de uma vaga
def scrape_job_data(job_url):
    global job_count
    try:
        # Inicia o navegador Brave
        driver = webdriver.Chrome(service=brave_service, options=brave_options)
        open_drivers.append(driver)
        
        # Acessa a URL da vaga
        driver.get(job_url)
        
        # Espera o carregamento completo da página
        driver.implicitly_wait(15)

        print(f"Processing job: {job_url}")

        # Tenta encontrar e clicar no botão de rejeitar todos os cookies, se ele estiver presente
        try:
            reject_all_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, 'onetrust-reject-all-handler'))
            )
            reject_all_button.click()
            print("Clicked on reject all cookies button.")
        except Exception as e:
            print(f"No reject all cookies button or could not click it: {e}")

        pattern = re.compile(r'jobsearch-JobInfoHeader-title(?:\.[\w-]+)?(?:\s\.e1tiznh50)?')

        # Título da vaga
        h1_elements = WebDriverWait(driver, 20).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'h1'))
        )

        # Encontra o <h2> que corresponde ao padrão
        for h1_element in h1_elements:
            class_attribute = h1_element.get_attribute('class')
            if pattern.match(class_attribute):
                # Encontra o elemento <span> dentro do <h2>
                span_element = h1_element.find_element(By.TAG_NAME, 'span')

                # Obtém o texto do <span>
                title = span_element.text.strip()
                print("Title:", title)
                break
        else:
            print("No matching <h1> element found.")
        
        # Descrição da vaga
        descricao = get_job_description(driver)
        
        print(f"Job {job_count + 1}: {title}")
        
        # Adiciona os dados coletados à lista
        jobs_data.append([title, descricao])
        job_count += 1
        
        # Fecha o navegador após obter os dados
        driver.quit()
        open_drivers.remove(driver)
    except Exception as e:
        print(f"Erro ao processar a vaga: {e}")
        if driver in open_drivers:
            driver.quit()
            open_drivers.remove(driver)

def get_job_description(driver):
    description_div = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, 'div.jobsearch-JobComponent-description.css-16y4thd.eu4oa1w0'))
    )
    
    texts = []

    for tag in ['p', 'ul', 'li', 'br', 'b']:
        elements = description_div.find_elements(By.TAG_NAME, tag)
        for element in elements:
            texts.append(element.text.strip())
    
    descricao = '\n'.join(texts)
    
    descricao_utf8 = descricao.encode('utf-8').decode('utf-8')
    
    return descricao_utf8

def go_to_next_page(driver):
    global job_count
    
    if job_count >= max_jobs:
        return
    
    # Tenta encontrar e clicar no botão de rejeitar todos os cookies, se ele estiver presente
    try:
        reject_all_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, 'onetrust-reject-all-handler'))
        )
        reject_all_button.click()
        print("Clicked on reject all cookies button.")
    except Exception as e:
        print(f"No reject all cookies button or could not click it: {e}")

    # Adiciona uma pequena pausa para garantir que o banner de cookies seja removido
    time.sleep(2)
    
    # Força a rolagem para garantir que o botão da próxima página esteja visível
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    
    # Espera o botão da página atual
    current_page_element = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, 'a[data-testid="pagination-page-current"]'))
    )
    
    # Obtém o número da página atual
    current_page_number = int(current_page_element.text.strip())
    print(f"Current page: {current_page_number}")
    
    # Calcula o número da próxima página
    next_page_number = current_page_number + 1
    
    # Encontra o botão da próxima página
    next_page_selector = f'a[data-testid="pagination-page-{next_page_number}"]'
    
    # Adiciona uma pequena pausa para garantir que a próxima página seja visível
    time.sleep(2)
    
    # Tenta clicar na próxima página e garantir que o elemento seja clicável
    try:
        next_page_element = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, next_page_selector))
        )
        next_page_element.click()
        print(f"Moved to page {next_page_number}.")
    except Exception as e:
        print(f"Could not click on next page button: {e}")
    
    # Aguarda o carregamento da nova página
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, 'h2.jobsearch-JobInfoHeader-title span'))
    )

def process_page(url):
    global job_count
    global available_jobs
    
    while available_jobs < max_jobs:
        # Limita o número máximo de abas abertas
        while len(open_drivers) >= max_tabs:
            # Fecha a aba mais antiga
            driver = open_drivers.pop(0)
            driver.quit()
        
        driver = webdriver.Chrome(service=brave_service, options=brave_options)
        open_drivers.append(driver)
        
        driver.get(url)
        
        driver.implicitly_wait(15)

        td_elements = driver.find_elements(By.CSS_SELECTOR, "td.resultContent.css-1qwrrf0.eu4oa1w0")
        
        print(f"Encontrados {len(td_elements)} elementos.")

        for card in td_elements:
            if job_count >= max_jobs:
                break
            job_link = card.find_element(By.CSS_SELECTOR, "a.jcs-JobTitle.css-jspxzf.eu4oa1w0")
            job_url = job_link.get_attribute("href")
            print(f"Processing page job: {job_url}")
            
            job_queue.put(job_url)
        
        try:
            if available_jobs < max_jobs:
                go_to_next_page(driver)
                available_jobs += len(td_elements)
                print(f"Available jobs: {available_jobs}")
                next_page_url = driver.current_url
                driver.quit()
                open_drivers.remove(driver)
                process_page(next_page_url)
        except Exception as e:
            print(f"No more pages or error in finding the next page: {e}")
        
        driver.quit()
        open_drivers.remove(driver)

# Preenche a fila de URLs
process_page(base_url)

# Função do worker que processa os URLs da fila
def worker():
    while not job_queue.empty():
        job_url = job_queue.get()
        scrape_job_data(job_url)
        job_queue.task_done()
        print(job_queue.qsize(), "jobs left to process")
        
        # Introduz um atraso aleatório entre 1 e 3 segundos antes de processar o próximo trabalho
        delay = random.uniform(1, 3)
        print(f"Waiting for {delay:.2f} seconds before processing the next job...")
        time.sleep(delay)

print(f"Starting to process {job_queue.qsize()} jobs...")
# Cria e inicia as threads após o preenchimento da fila
threads = []
for _ in range(max_tabs):
    if job_count < max_jobs:
        thread = threading.Thread(target=worker)
        thread.start()
        threads.append(thread)

# Aguarda a conclusão de todas as threads
for thread in threads:
    thread.join()

# Escrevendo os dados coletados em um arquivo CSV
with open('indeed_jobs_big.csv', 'w', newline='', encoding='utf-8') as file:
    writer = csv.writer(file)
    writer.writerow(["title", "content"])
    writer.writerows(jobs_data)

print(f"Scraping completed. {job_count} job postings saved to indeed_jobs_big.csv")
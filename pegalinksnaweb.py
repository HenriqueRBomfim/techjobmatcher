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
brave_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36")
brave_options.add_argument("--disable-blink-features=AutomationControlled")

# URL base para o Indeed
base_url = "https://br.indeed.com/jobs?q=desenvolvedor+de+software&l=&from=searchOnHP&vjk=918f94e6e372b669"

# Variáveis globais
job_count = 0
max_jobs = 1000
available_jobs = 0

# Configuração da fila para multi-threading
job_queue = Queue()

# Controle de abas abertas
max_tabs = 5
open_drivers = []
open_drivers_lock = threading.Lock()

# Locks para sincronização
csv_lock = threading.Lock()
job_count_lock = threading.Lock()

# Define o semáforo para permitir no máximo 5 threads simultâneas
thread_limit = threading.Semaphore(max_tabs)

def go_to_next_page(driver):
    global job_count
    global available_jobs

    if job_count >= max_jobs or available_jobs >= max_jobs:
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

# Inicializa o arquivo CSV para salvar os links das vagas
with open('job_links.csv', 'w', newline='', encoding='utf-8') as file:
    writer = csv.writer(file)
    writer.writerow(["job_url"])  # Cabeçalho

def process_page(url):
    global job_count
    global available_jobs

    while available_jobs < max_jobs:
        # Limita o número máximo de abas abertas
        with open_drivers_lock:
            while len(open_drivers) >= max_tabs:
                driver_to_close = open_drivers.pop(0)
                driver_to_close.quit()

        # Inicia um novo driver
        driver = webdriver.Chrome(service=brave_service, options=brave_options)
        with open_drivers_lock:
            open_drivers.append(driver)

        # Acessa a URL da página atual
        driver.get(url)
        driver.implicitly_wait(15)

        # Encontra os elementos das vagas
        td_elements = driver.find_elements(By.CSS_SELECTOR, "td.resultContent.css-1qwrrf0.eu4oa1w0")
        
        print(f"Encontrados {len(td_elements)} elementos.")

        with open('job_links.csv', 'a', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)

            for card in td_elements:
                if job_count >= max_jobs:
                    break
                try:
                    job_link = card.find_element(By.CSS_SELECTOR, "a.jcs-JobTitle.css-jspxzf.eu4oa1w0")
                    job_url = job_link.get_attribute("href")
                    print(f"Saving job link: {job_url}")
                    # Salva o link da vaga no arquivo CSV
                    writer.writerow([job_url])
                except Exception as e:
                    print(f"Erro ao extrair o link da vaga: {e}")
        
        try:
            if available_jobs < max_jobs:
                go_to_next_page(driver)
                available_jobs += len(td_elements)
                print(f"Available jobs: {available_jobs}")
                next_page_url = driver.current_url
                driver.quit()
                with open_drivers_lock:
                    try:
                        open_drivers.remove(driver)
                    except Exception as e:
                        print(f"No driver to remove from open_drivers: {e}")
                process_page(next_page_url)
                return  # Evita a execução do código abaixo
        except Exception as e:
            print(f"No more pages or error in finding the next page: {e}")
        
        # Remove o driver somente se ainda estiver na lista
        with open_drivers_lock:
            if driver in open_drivers:
                driver.quit()
                try:
                    open_drivers.remove(driver)
                except Exception as e:
                    print(f"No driver to remove from open_drivers: {e}")

# Preenche a fila de URLs
process_page(base_url)

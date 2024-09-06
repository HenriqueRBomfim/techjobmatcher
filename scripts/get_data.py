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
max_tabs = 1
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

def scrape_job_data(job_url, retries=1):
    global job_count
    try:
        for attempt in range(retries):
            try:
                driver = webdriver.Chrome(service=brave_service, options=brave_options)
                with open_drivers_lock:
                    open_drivers.append(driver)
                
                driver.get(job_url)
                
                # Aguarda o carregamento completo da página
                WebDriverWait(driver, 20).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'div.jobsearch-JobComponent-description.css-16y4thd.eu4oa1w0'))
                )

                print(f"Processing job: {job_url}")

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
                h1_elements = WebDriverWait(driver, 15).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'h1'))
                )

                # Encontra o <h1> que corresponde ao padrão
                for h1_element in h1_elements:
                    class_attribute = h1_element.get_attribute('class')
                    if pattern.match(class_attribute):
                        # Encontra o elemento <span> dentro do <h1>
                        span_element = h1_element.find_element(By.TAG_NAME, 'span')

                        # Obtém o texto do <span>
                        title = span_element.text.strip()
                        print("Title:", title)
                        break
                else:
                    print("No matching <h1> element found.")
                    title = "N/A"
                
                # Descrição da vaga
                descricao = get_job_description(driver)
                
                print(f"Job {job_count + 1}: {title}")
                
                # Adiciona os dados coletados ao arquivo CSV de forma thread-safe
                with csv_lock:
                    with open('indeed_jobs_big.csv', 'a', newline='', encoding='utf-8') as file:
                        writer = csv.writer(file)
                        writer.writerow([title, descricao])
                
                # Atualiza o contador de vagas de forma thread-safe
                with job_count_lock:
                    job_count += 1
                
                # Fecha o navegador após obter os dados
                driver.quit()
                with open_drivers_lock:
                    try:
                        open_drivers.remove(driver)
                    except Exception as e:
                        print(f"No driver to remove from open_drivers: {e}")
                
                # Se conseguiu processar a vaga, sai do loop de tentativas
                break

            except Exception as e:
                print(f"Attempt {attempt + 1} failed: {e}")
                if attempt < retries - 1:
                    print("Retrying...")
                    time.sleep(1)  # Aguarda um pouco antes de tentar novamente
                else:
                    print("Max retries reached. Skipping this job.")
                    if 'driver' in locals():
                        driver.quit()
                        with open_drivers_lock:
                            try:
                                open_drivers.remove(driver)
                            except Exception as e:
                                print(f"No driver to remove from open_drivers: {e}")
    except Exception as e:
        print(f"Erro ao processar a vaga: {e}")
        if 'driver' in locals():
            with open_drivers_lock:
                if driver in open_drivers:
                    driver.quit()
                    try:
                        open_drivers.remove(driver)
                    except Exception as e:
                        print(f"No driver to remove from open_drivers: {e}")

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

# Função para processar um link de vaga
def worker():
    global job_count
    while not job_queue.empty():
        job_url = job_queue.get()

        # Aguarda liberação do semáforo para continuar
        with thread_limit:
            scrape_job_data(job_url)
            job_queue.task_done()

            print(f"{job_queue.qsize()} jobs left to process")
            
            # Introduz um atraso aleatório entre 1 e 2 segundos antes de processar o próximo trabalho
            delay = random.uniform(1, 1.5)
            print(f"Waiting for {delay:.2f} seconds before processing the next job...")
            time.sleep(delay)

# Função para carregar os links das vagas do arquivo CSV e preencher a fila
def load_jobs_from_csv(file_path, start_line=17):
    global available_jobs
    with open(file_path, 'r', newline='', encoding='utf-8') as file:
        reader = csv.reader(file)
        
        # Pular até a linha start_line (0-indexed, então para linha 11, pulamos 10 linhas)
        for _ in range(start_line - 1):
            next(reader)
        
        # Ler a partir da linha start_line
        for row in reader:
            job_url = row[0]
            job_queue.put(job_url)
            print(f"Added job link to queue: {job_url}")
        available_jobs = job_queue.qsize()

# Função para iniciar as threads
def start_threads():
    global job_count

    print(f"Starting to process {job_queue.qsize()} jobs...")

    threads = []
    while not job_queue.empty() or threading.active_count() > 1:  # Garantir que todas as threads sejam processadas
        if threading.active_count() <= max_tabs:
            thread = threading.Thread(target=worker)
            thread.start()
            threads.append(thread)
            print(f"Started new thread. Active threads: {threading.active_count()}")
        
        # Aguarda um pouco para permitir que as threads atuais processem alguns trabalhos
        time.sleep(1)

    # Aguarda a conclusão de todas as threads
    print("Waiting for all threads to finish...")
    for thread in threads:
        thread.join()  # Aguarda cada thread terminar

    print(f"Scraping completed. {job_count} job postings saved to indeed_jobs_big.csv")

# Carrega os links das vagas e inicia o processo com multi-threading
load_jobs_from_csv('job_links.csv', start_line=810)
start_threads()

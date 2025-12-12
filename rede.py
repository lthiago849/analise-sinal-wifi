import csv
import time
import datetime
import subprocess
import re # Necessário para analisar a saída do comando

# Nome do arquivo onde os dados serão salvos
NOME_ARQUIVO = 'dados_wifi_coleta.csv'

# Cabeçalhos do arquivo CSV
CAMPOS = [
    'timestamp', 'x', 'y', 'rssi_dbm', 'snr', 'ruido',
    'frequencia_ghz', 'canal', 'bssid'
]

def inicializar_csv():
    """Cria o arquivo CSV e escreve os cabeçalhos."""
    with open(NOME_ARQUIVO, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(CAMPOS)

def coletar_dados_sistema(interface='wlan0'):
    """
    Função REAL para Linux: Executa iwconfig e extrai as métricas de RF.
    Calcula o SNR (Signal-to-Noise Ratio) como RSSI - Ruído.
    """
    try:
        # 1. Executa o comando iwconfig
        # Captura a saída de texto do comando
        output = subprocess.check_output(["iwconfig", interface], stderr=subprocess.STDOUT).decode("utf-8")
        
    except subprocess.CalledProcessError as e:
        print(f"Erro ao executar iwconfig. Verifique a interface ({interface}) ou se o pacote 'wireless-tools' está instalado.")
        print(f"Detalhes do erro: {e.output.decode()}")
        return None
    except FileNotFoundError:
        print("Erro: O comando 'iwconfig' não foi encontrado. Instale o pacote 'wireless-tools'.")
        return None
    
    # Dicionário para armazenar os dados coletados
    dados_rf = {}

    # 2. Extração de RSSI (Signal Level) e Ruído (Noise Level)
    # Padrão: 'Signal level=-65 dBm' ou 'Noise level=-95 dBm'
    rssi_match = re.search(r'Signal level\s*=\s*(\-?\d+)\s*dBm', output)
    noise_match = re.search(r'Noise level\s*=\s*(\-?\d+)\s*dBm', output)
    
    # 3. Extração de Frequência
    # Padrão: 'Frequency:2.437 GHz' (ou 5.x GHz)
    freq_match = re.search(r'Frequency:([\d\.]+) GHz', output)
    
    # 4. Extração de BSSID
    # Padrão: 'Access Point: 00:1A:2B:3C:4D:5E'
    bssid_match = re.search(r'Access Point:\s*([0-9A-Fa-f:]{17})', output)
    
    # 5. Processamento e Cálculo
    
    # RSSI
    dados_rf['rssi_dbm'] = int(rssi_match.group(1)) if rssi_match else None
    
    # Ruído
    dados_rf['ruido'] = int(noise_match.group(1)) if noise_match else None

    # SNR (Cálculo: RSSI - Ruído). Atenção: Ruído é um número negativo.
    if dados_rf['rssi_dbm'] is not None and dados_rf['ruido'] is not None:
        dados_rf['snr'] = dados_rf['rssi_dbm'] - dados_rf['ruido']
    else:
        dados_rf['snr'] = None

    # Frequência (em GHz)
    dados_rf['frequencia_ghz'] = float(freq_match.group(1)) if freq_match else None
    
    # BSSID
    dados_rf['bssid'] = bssid_match.group(1) if bssid_match else None

    # Canal (Precisa ser calculado a partir da Frequência)
    # Isso é uma aproximação e pode ser complexo. Por simplicidade,
    # se a frequência for 2.4 GHz, consideramos o canal 6 (o mais comum se não for especificado)
    # ou deixar como None se for muito difícil de extrair de forma robusta no iwconfig.
    # Se você quiser preencher, você teria que criar uma função de mapeamento de frequência para canal.
    dados_rf['canal'] = None # Deixamos como None, ou use um valor fixo para a rede de teste
    
    return dados_rf

def salvar_dados(x, y, dados_rf):
    """Salva uma linha de dados no arquivo CSV."""
    if dados_rf is None:
        print("Coleta de dados RF falhou. Linha ignorada.")
        return
        
    timestamp = datetime.datetime.utcnow().isoformat()
    linha = [
        timestamp,
        x,
        y,
        dados_rf.get('rssi_dbm'),
        dados_rf.get('snr'),
        dados_rf.get('ruido'),
        dados_rf.get('frequencia_ghz'),
        dados_rf.get('canal'),
        dados_rf.get('bssid')
    ]
    with open(NOME_ARQUIVO, mode='a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(linha)
    print(f"Dados salvos: Posição ({x}, {y}) | RSSI: {dados_rf.get('rssi_dbm')} dBm | SNR: {dados_rf.get('snr')}")

def executar_coleta():
    """Loop principal para a coleta de dados."""
    inicializar_csv()
    print("Iniciando a coleta de dados para o Radiomap.")
    print("Certifique-se de estar conectado à rede Wi-Fi que deseja medir.")
    print("Digite 'sair' para encerrar a coleta.")

    while True:
        # Pede a coordenada (X, Y) manualmente
        entrada = input("\nDigite a posição (x, y) em metros (ex: 1.0, 3.5) ou 'sair': ")

        if entrada.lower() == 'sair':
            break

        try:
            # Tenta converter a entrada (x, y) em números
            x_str, y_str = entrada.split(',')
            x = float(x_str.strip())
            y = float(y_str.strip())
        except ValueError:
            print("Formato inválido. Use 'x, y' (ex: 1.0, 3.5).")
            continue

        # Coleta a medição RF
        # Chama a função que usa iwconfig para obter dados reais

        # EXECUTE
        # ip link show

        dados_rf = coletar_dados_sistema(interface='wlp0s20f3')
        
        if dados_rf is not None and dados_rf.get('rssi_dbm') is not None:
            # Salva no arquivo CSV
            salvar_dados(x, y, dados_rf)
        else:
            print("Não foi possível obter dados válidos. Tente novamente ou verifique a conexão.")

        # Adiciona um pequeno delay. Recomenda-se um delay maior
        # para dar tempo de você se mover para o próximo ponto de medição.
        time.sleep(3) 

    print(f"\nColeta finalizada. Dados salvos em '{NOME_ARQUIVO}'.")

if __name__ == "__main__":
    # Certifique-se de que sua interface de rede esteja ligada e conectada.
    executar_coleta()
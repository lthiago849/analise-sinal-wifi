import csv
import time
import datetime
import subprocess
import re 

NOME_ARQUIVO = 'dados_wifi_coleta.csv'

# Um valor comum para ambientes internos é -95 dBm.
NOISE_FLOOR_ASSUMIDO = -95 

# Cabeçalhos do arquivo CSV
CAMPOS = [
    'timestamp', 'x', 'y', 'rssi_dbm', 'snr', 'ruido',
    'frequencia_ghz', 'canal', 'bssid'
]

def inicializar_csv():
    with open(NOME_ARQUIVO, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(CAMPOS)

def mapear_frequencia_para_canal(frequencia_ghz):

    if frequencia_ghz is None:
        return None
        
    freq = round(frequencia_ghz, 3) # Arredonda para 3 casas decimais

    # Canais de 2.4 GHz
    if 2.400 < freq < 2.500:
        # Frequências centrais dos canais de 2.4 GHz
        freq_canais_2_4 = {
            2.412: 1, 2.417: 2, 2.422: 3, 2.427: 4, 
            2.432: 5, 2.437: 6, 2.442: 7, 2.447: 8,
            2.452: 9, 2.457: 10, 2.462: 11, 2.467: 12, 
            2.472: 13, 2.484: 14 
        }
        # Encontra o canal com a frequência mais próxima
        closest_freq = min(freq_canais_2_4.keys(), 
                           key=lambda x: abs(x - freq))
        
        if abs(closest_freq - freq) < 0.005:
            return freq_canais_2_4[closest_freq]

    # Canais de 5 GHz (mapeamento simplificado)
    elif 5.100 < freq < 5.900:
        if 5.175 < freq < 5.250: return 36
        if 5.250 < freq < 5.350: return 52
        if 5.470 < freq < 5.725: return 100
        if 5.725 < freq < 5.850: return 149
        
    return None

def coletar_dados_sistema(interface='wlan0'):

    try:
        output = subprocess.check_output(["iwconfig", interface], stderr=subprocess.STDOUT).decode("utf-8")
        
    except subprocess.CalledProcessError as e:
        print(f"Erro ao executar iwconfig. Verifique a interface ({interface}) ou se o pacote 'wireless-tools' está instalado.")
        print(f"Detalhes do erro: {e.output.decode()}")
        return None
    except FileNotFoundError:
        print("Erro: O comando 'iwconfig' não foi encontrado. Instale o pacote 'wireless-tools'.")
        return None
    
    dados_rf = {}

    # 1. Extração de RSSI (Signal Level)
    rssi_match = re.search(r'Signal level\s*=\s*(\-?\d+)\s*dBm', output)
    # 2. Extração de Ruído (Tenta o padrão comum)
    noise_match = re.search(r'Noise level\s*=\s*(\-?\d+)\s*dBm', output)
    
    # Processamento de RSSI
    dados_rf['rssi_dbm'] = int(rssi_match.group(1)) if rssi_match else None
    
    # Processamento de Ruído
    if noise_match:
        dados_rf['ruido'] = int(noise_match.group(1))
    else:
        # SE NÃO ENCONTRAR O RUÍDO, USA O VALOR ASSUMIDO E AVISA
        dados_rf['ruido'] = NOISE_FLOOR_ASSUMIDO
        print(f"Aviso: Ruído não detectado pelo iwconfig. Usando valor assumido: {NOISE_FLOOR_ASSUMIDO} dBm.")


    # SNR (Cálculo: RSSI - Ruído). O Ruído é sempre um número negativo.
    if dados_rf['rssi_dbm'] is not None and dados_rf['ruido'] is not None:
        dados_rf['snr'] = dados_rf['rssi_dbm'] - dados_rf['ruido']
    else:
        dados_rf['snr'] = None

    # Extração de Frequência, Canal e BSSID
    freq_match = re.search(r'Frequency:([\d\.]+) GHz', output)
    bssid_match = re.search(r'Access Point:\s*([0-9A-Fa-f:]{17})', output)

    dados_rf['frequencia_ghz'] = float(freq_match.group(1)) if freq_match else None
    dados_rf['canal'] = mapear_frequencia_para_canal(dados_rf['frequencia_ghz'])
    dados_rf['bssid'] = bssid_match.group(1) if bssid_match else None
    
    return dados_rf

def salvar_dados(x, y, dados_rf):
    """Salva uma linha de dados no arquivo CSV."""
    if dados_rf is None:
        print("Coleta de dados RF falhou. Linha ignorada.")
        return

    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
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
    print(f"Dados salvos: Posição ({x}, {y}) | RSSI: {dados_rf.get('rssi_dbm')} dBm | SNR: {dados_rf.get('snr')} dB | Ruído: {dados_rf.get('ruido')} dBm | Canal: {dados_rf.get('canal')}")

def executar_coleta():
    """Loop principal para a coleta de dados."""
    # Se o arquivo já existe, ele será sobrescrito.
    if not input(f"O arquivo '{NOME_ARQUIVO}' será sobrescrito. Continuar? (s/n): ").lower().startswith('s'):
        print("Coleta cancelada.")
        return
        
    inicializar_csv()
    print("Iniciando a coleta de dados para o Radiomap.")
    print(f"O Ruído de Fundo será assumido como {NOISE_FLOOR_ASSUMIDO} dBm.")
    print("Digite 'sair' para encerrar a coleta.")
    
    interface_wifi = input("Digite o nome da sua interface Wi-Fi (ex: wlp0s20f3, wlan0): ")

    while True:
        entrada = input("\nDigite a posição (x, y) em metros (ex: 1.0, 3.5) ou 'sair': ")

        if entrada.lower() == 'sair':
            break

        try:
            x_str, y_str = entrada.split(',')
            x = float(x_str.strip())
            y = float(y_str.strip())
        except ValueError:
            print("Formato inválido. Use 'x, y' (ex: 1.0, 3.5).")
            continue

        dados_rf = coletar_dados_sistema(interface=interface_wifi)
        
        if dados_rf is not None and dados_rf.get('rssi_dbm') is not None:
            salvar_dados(x, y, dados_rf)
        else:
            print("Não foi possível obter dados válidos. Tente novamente ou verifique a conexão.")

        time.sleep(3) 

    print(f"\nColeta finalizada. Dados salvos em '{NOME_ARQUIVO}'.")

if __name__ == "__main__":
    executar_coleta()
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import griddata

NOME_ARQUIVO = 'dados_wifi_coleta.csv'

def calcular_distancia(df):
    """Calcula a distância euclidiana do ponto (x, y) até a origem (0, 0)."""
    # Roteador em (0, 0)
    df['distancia'] = np.sqrt(df['x']**2 + df['y']**2)
    return df

def gerar_mapa_calor_rssi(df, titulo):
    """Gera um Heatmap 2D do RSSI interpolando os pontos coletados."""
    
    df = df.dropna(subset=['rssi_dbm']).copy()
    if df.empty:
        print("Erro: Não há dados válidos para o RSSI.")
        return

    # 1. Preparar dados
    pontos = df[['x', 'y']].values
    valores = df['rssi_dbm'].values
    
    # 2. Definir a grade e interpolar
    # Define a margem de visualização
    x_min, x_max = df['x'].min() - 1, df['x'].max() + 1
    y_min, y_max = df['y'].min() - 1, df['y'].max() + 1
    
    grid_x, grid_y = np.mgrid[x_min:x_max:100j, y_min:y_max:100j]
    grid_z = griddata(pontos, valores, (grid_x, grid_y), method='cubic')
    
    # 3. Plotar o Heatmap 
    plt.figure(figsize=(10, 8))
    
    # cmap='plasma' ou 'viridis' para visualização de intensidade
    plt.imshow(grid_z.T, extent=(x_min, x_max, y_min, y_max), origin='lower', 
               cmap='viridis', aspect='auto')
               
    plt.scatter(df['x'], df['y'], c='red', s=50, edgecolors='k', label='Pontos de Coleta')
    plt.scatter([0], [0], c='yellow', s=150, marker='*', edgecolors='black', label='Roteador (0,0)')
    
    plt.colorbar(label='RSSI (dBm) - Sinal Forte (menos negativo) / Fraco (mais negativo)')
    plt.title(titulo)
    plt.xlabel('Eixo X (metros)')
    plt.ylabel('Eixo Y (metros)')
    plt.legend()
    plt.grid(True)
    plt.savefig('heatmap_rssi.png')
    plt.show()

def gerar_grafico_rssi_distancia(df):
    """Gera o Gráfico RSSI vs Distância para analisar o Path Loss."""
    df = df.dropna(subset=['rssi_dbm', 'distancia']).copy()
    
    plt.figure(figsize=(10, 6))
    plt.scatter(df['distancia'], df['rssi_dbm'], alpha=0.7)
    
    # Opcional: Adicionar uma linha de regressão para tendência
    # z = np.polyfit(df['distancia'], df['rssi_dbm'], 1)
    # p = np.poly1d(z)
    # plt.plot(df['distancia'], p(df['distancia']), "r--", label='Tendência (Path Loss)')
    
    plt.title('Gráfico RSSI vs. Distância (Análise de Path Loss)')
    plt.xlabel('Distância do Roteador (metros)')
    plt.ylabel('RSSI (dBm)')
    plt.grid(True, linestyle='--')
    plt.legend()
    plt.savefig('rssi_vs_distancia.png')
    plt.show()

def main_analise():
    """Função principal para executar a análise e visualização."""
    try:
        df = pd.read_csv(NOME_ARQUIVO)
    except FileNotFoundError:
        print(f"Erro: Arquivo '{NOME_ARQUIVO}' não encontrado. Execute o script de coleta primeiro.")
        return

    # Limpeza e cálculo da distância
    df = calcular_distancia(df)
    
    if len(df) < 5:
         print(f"Aviso: Você coletou apenas {len(df)} pontos. Colete mais dados (pelo menos 10-15) em áreas distintas para um bom mapa de calor.")
         
    # 1. Geração do Heatmap do RSSI
    gerar_mapa_calor_rssi(df, 'Mapa de Cobertura Wi-Fi RSSI')

    # 2. Geração do Gráfico RSSI vs. Distância
    gerar_grafico_rssi_distancia(df)

    # 3. Preparação dos Dados para a IA (LLM)
    print("\n--- Dados Estatísticos Chave para Análise da IA (LLM) ---")
    
    # Calcular RSSI Médio e Desvio Padrão
    stats_df = df.dropna(subset=['rssi_dbm']).copy()
    
    # Desvio Padrão (Oscilação) para a IA interpretar multipercurso
    mean_rssi = stats_df['rssi_dbm'].mean()
    std_rssi = stats_df['rssi_dbm'].std()

    print(f"* RSSI Médio Geral: {mean_rssi:.2f} dBm")
    print(f"* Desvio Padrão do RSSI: {std_rssi:.2f} dB (Mede a oscilação do sinal, importante para multipercurso)")
    
    # Ponto de Pior Sinal (Zona de Sombra)
    pior_sinal = stats_df.loc[stats_df['rssi_dbm'].idxmin()]
    
    print("\n--- Pontos Críticos para a Explicação da IA ---")
    print("Ponto de Pior Sinal (Zona de Sombra):")
    print(f"Coordenadas: ({pior_sinal['x']:.1f}, {pior_sinal['y']:.1f})")
    print(f"RSSI: {pior_sinal['rssi_dbm']} dBm | Distância: {pior_sinal['distancia']:.1f} m")

    print("\nInstruções para a IA:")
    print("1. Envie o print do Heatmap e do Gráfico RSSI vs Distância ao LLM.")
    print("2. Peça ao LLM para analisar a relação entre a distância e a queda do sinal (Path Loss).")
    print("3. Peça ao LLM para explicar por que o Ponto de Pior Sinal tem um RSSI tão baixo, correlacionando com a Camada Física (ex: absorção por paredes, zonas de sombra).")


if __name__ == "__main__":
    main_analise()
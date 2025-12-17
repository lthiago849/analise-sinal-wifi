import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import griddata

NOME_ARQUIVO = 'dados_wifi_coleta.csv'

def calcular_distancia(df):
    """Calcula a distância euclidiana do ponto (x, y) até a origem (0, 0)."""
    df['distancia'] = np.sqrt(df['x']**2 + df['y']**2)
    return df

def configurar_plot_base(df):
    """Retorna os limites da grade e a posição do roteador."""
    x_min, x_max = df['x'].min() - 1, df['x'].max() + 1
    y_min, y_max = df['y'].min() - 1, df['y'].max() + 1
    return x_min, x_max, y_min, y_max

def gerar_mapa_calor_generico(df, coluna_valor, titulo, label_cor, nome_arquivo, cmap_name):
    """Gera um Heatmap 2D forçando a barra lateral a seguir o mapa."""
    
    df = df.dropna(subset=[coluna_valor]).copy()
    if df.empty:
        print(f"Erro: Não há dados válidos para {coluna_valor}.")
        return

    # 1. Preparar dados
    pontos = df[['x', 'y']].values
    valores = df[coluna_valor].values
    
    # Define limites fixos de cor baseados nos dados para sincronizar fundo e pontos
    v_min, v_max = valores.min(), valores.max()
    
    # 2. Definir a grade e interpolar
    x_min, x_max, y_min, y_max = configurar_plot_base(df)
    grid_x, grid_y = np.mgrid[x_min:x_max:100j, y_min:y_max:100j]
    grid_z = griddata(pontos, valores, (grid_x, grid_y), method='cubic')
    
    # 3. Plotar o Heatmap 
    plt.figure(figsize=(10, 8))
    
    # Guardamos o objeto 'imagem_mapa' que o imshow cria
    imagem_mapa = plt.imshow(grid_z.T, extent=(x_min, x_max, y_min, y_max), origin='lower', 
                             cmap=cmap_name, aspect='auto', vmin=v_min, vmax=v_max)
               
    # Plot dos pontos usando os MESMOS limites (vmin/vmax) e o MESMO mapa de cores
    plt.scatter(df['x'], df['y'], c=valores, cmap=cmap_name, s=60, edgecolors='k', 
                vmin=v_min, vmax=v_max, label='Pontos de Coleta')
    
    # Plot do Roteador (Amarelo fixo)
    plt.scatter([0], [0], c='gold', s=200, marker='*', edgecolors='black', label='Roteador (0,0)')
    
    # --- AMARRA A BARRA LATERAL AO MAPA ---
    # Passamos 'imagem_mapa' para garantir que a barra use as cores certas
    cbar = plt.colorbar(imagem_mapa, label=label_cor)
    
    plt.title(titulo)
    plt.xlabel('Eixo X (metros)')
    plt.ylabel('Eixo Y (metros)')
    plt.legend()
    plt.grid(True, linestyle=':', alpha=0.6)
    plt.savefig(nome_arquivo)
    plt.close() # Fecha a figura para não sobrar lixo na memória
    print(f"Gerado: {nome_arquivo}")

def gerar_grafico_rssi_distancia(df):
    """Gera o Gráfico RSSI vs Distância."""
    df = df.dropna(subset=['rssi_dbm', 'distancia']).copy()
    
    plt.figure(figsize=(10, 6))
    plt.scatter(df['distancia'], df['rssi_dbm'], alpha=0.7, c='blue', edgecolors='k')
    
    try:
        df_fit = df[df['distancia'] > 0.5].copy() 
        z = np.polyfit(np.log10(df_fit['distancia']), df_fit['rssi_dbm'], 1)
        p = np.poly1d(z)
        dist_range = np.linspace(df_fit['distancia'].min(), df_fit['distancia'].max(), 50)
        plt.plot(dist_range, p(np.log10(dist_range)), "r--", linewidth=2, label='Tendência (Path Loss)')
    except Exception:
        pass
    
    plt.title('Gráfico RSSI vs. Distância (Análise de Path Loss)')
    plt.xlabel('Distância do Roteador (metros)')
    plt.ylabel('RSSI (dBm)')
    plt.grid(True, linestyle='--')
    plt.legend()
    plt.savefig('rssi_vs_distancia.png')
    plt.close()
    print("Gerado: rssi_vs_distancia.png")

def calcular_variancia_local(df):
    """Calcula a variância do RSSI por ponto."""
    variancia_df = df.groupby(['x', 'y'])['rssi_dbm'].agg(['std']).reset_index()
    variancia_df = variancia_df.rename(columns={'std': 'variancia_rssi'})
    variancia_df['variancia_rssi'] = variancia_df['variancia_rssi'].fillna(0)
    return variancia_df

def main_analise():
    """Função principal."""
    try:
        df = pd.read_csv(NOME_ARQUIVO)
    except FileNotFoundError:
        print(f"Erro: Arquivo '{NOME_ARQUIVO}' não encontrado.")
        return

    df = calcular_distancia(df)
    
    if len(df) < 5:
         print(f"Aviso: Poucos dados ({len(df)} pontos).")
         
    print("--- Gerando Visualizações ---")
    
    # 1. RSSI: Usa RdYlBu (Vermelho=Fraco, Azul=Forte)
    gerar_mapa_calor_generico(df, 'rssi_dbm', '1. Mapa de Cobertura Wi-Fi RSSI', 
                              'RSSI (dBm)', 'heatmap_rssi.png', 'RdYlBu')

    # 2. Path Loss
    gerar_grafico_rssi_distancia(df)

    # 3. Variância: Usa hot (Preto=Estável, Branco/Amarelo=Instável)
    variancia_df = calcular_variancia_local(df)
    if not variancia_df['variancia_rssi'].empty and variancia_df['variancia_rssi'].max() > 0:
        gerar_mapa_calor_generico(variancia_df, 'variancia_rssi', '2. Heatmap da Variância (Fading)', 
                                  'Desvio Padrão (dB)', 'heatmap_variancia.png', 'hot')
    else:
        print("Aviso: Variância não gerada (falta de repetições no mesmo ponto).")
    
    # 4. Ruído
    gerar_mapa_calor_generico(df, 'ruido', '3. Mapa de Ruído', 
                              'Ruído (dBm)', 'heatmap_ruido.png', 'plasma')

    # 5. SNR: Usa RdYlBu (Vermelho=Ruim, Azul=Bom)
    gerar_mapa_calor_generico(df, 'snr', '4. Qualidade do Sinal (SNR)', 
                              'SNR (dB)', 'heatmap_snr.png', 'RdYlBu')

    # Estatísticas
    stats_df = df.dropna(subset=['rssi_dbm']).copy()
    print("\n--- Estatísticas Finais ---")
    print(f"* RSSI Médio: {stats_df['rssi_dbm'].mean():.2f} dBm")
    print(f"* Desvio Padrão Geral: {stats_df['rssi_dbm'].std():.2f} dB")
    
    pior = stats_df.loc[stats_df['rssi_dbm'].idxmin()]
    print(f"Pior Sinal: {pior['rssi_dbm']} dBm em ({pior['x']}, {pior['y']})")

if __name__ == "__main__":
    main_analise()
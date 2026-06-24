import matplotlib
matplotlib.use('Agg')  # Força o matplotlib a renderizar arquivos sem interface gráfica

import bagpy
from bagpy import bagreader
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.spatial.transform import Rotation as R
import os
import rosbag  # Biblioteca nativa do ROS para leitura direta e robusta

# 1. Verificar a existência da bag do Hector SLAM
print("🔄 Carregando a rosbag do Hector SLAM via ROS...")
nome_bag = 'resultados_amcl_hector.bag'

if not os.path.exists(nome_bag):
    raise FileNotFoundError(f"❌ O arquivo '{nome_bag}' não foi encontrado na pasta atual!")

# 2. Extrair o AMCL_POSE usando o bagpy
print("📦 Extraindo dados do AMCL...")
b = bagreader(nome_bag)
amcl_pose_csv = b.message_by_topic('/amcl_pose')
df_amcl = pd.read_csv(amcl_pose_csv)

# 3. Extrair o GROUND TRUTH direto da Bag usando rosbag nativo
print("🔍 Extraindo Ground Truth (/gazebo/model_states) diretamente dos frames do ROS...")
bag = rosbag.Bag(nome_bag)

gt_dados = []

for topic, msg, t in bag.read_messages(topics=['/gazebo/model_states']):
    try:
        if 'husky' in msg.name:
            r_idx = msg.name.index('husky')
        else:
            r_idx = 1 if len(msg.name) > 1 else 0
            
        p = msg.pose[r_idx]
        
        gt_dados.append({
            'Time': t.to_sec(),
            'x': p.position.x,
            'y': p.position.y,
            'qx': p.orientation.x,
            'qy': p.orientation.y,
            'qz': p.orientation.z,
            'qw': p.orientation.w
        })
    except Exception as e:
        continue

bag.close()

df_gt = pd.DataFrame(gt_dados)

if df_gt.empty:
    print("❌ Erro grave: O tópico /gazebo/model_states está vazio ou não foi encontrado.")
    exit(1)

print(f"✅ Dados brutos carregados. AMCL: {len(df_amcl)} amostras | Gazebo: {len(df_gt)} amostras.")

# --- MAPEAMENTO DAS COLUNAS DO AMCL ---
amcl_x_col = [c for c in df_amcl.columns if 'pose' in c and 'position.x' in c][0]
amcl_y_col = [c for c in df_amcl.columns if 'pose' in c and 'position.y' in c][0]
amcl_qx_col = [c for c in df_amcl.columns if 'pose' in c and 'orientation.x' in c][0]
amcl_qy_col = [c for c in df_amcl.columns if 'pose' in c and 'orientation.y' in c][0]
amcl_qz_col = [c for c in df_amcl.columns if 'pose' in c and 'orientation.z' in c][0]
amcl_qw_col = [c for c in df_amcl.columns if 'pose' in c and 'orientation.w' in c][0]

# --- ALINHAMENTO TEMPORAL (INTERPOLAÇÃO) ---
print("⏱️ Sincronizando timestamps entre AMCL e Gazebo...")
gt_x_interp = np.interp(df_amcl['Time'], df_gt['Time'], df_gt['x'])
gt_y_interp = np.interp(df_amcl['Time'], df_gt['Time'], df_gt['y'])

gt_qx = np.interp(df_amcl['Time'], df_gt['Time'], df_gt['qx'])
gt_qy = np.interp(df_amcl['Time'], df_gt['Time'], df_gt['qy'])
gt_qz = np.interp(df_amcl['Time'], df_gt['Time'], df_gt['qz'])
gt_qw = np.interp(df_amcl['Time'], df_gt['Time'], df_gt['qw'])

amcl_x = df_amcl[amcl_x_col].values
amcl_y = df_amcl[amcl_y_col].values

# =========================================================================
# 📐 ABORDAGEM COM VALORES FIXOS DO URDF (CORREÇÃO DE REFERENCIAL)
# =========================================================================
print("📐 Aplicando alinhamento estático com base nos valores do URDF...")
X_OFFSET_URDF = -4.65
Y_OFFSET_URDF = -3.0

# Correção algébrica do vetor de translação do ambiente lar_gazebo
gt_x_alinhado = gt_x_interp + X_OFFSET_URDF
gt_y_alinhado = gt_y_interp + Y_OFFSET_URDF

# --- CÁLCULO DAS MÉTRICAS (SOBRE O REFERENCIAL CORRIGIDO) ---

# 1. Erro de Posição Instantâneo (Distância Euclidiana Real)
erros_posicao = np.sqrt((amcl_x - gt_x_alinhado)**2 + (amcl_y - gt_y_alinhado)**2)

# 2. RMSE de Posição
rmse_posicao = np.sqrt(np.mean(erros_posicao**2))

# 3. Erro Final de Posição
erro_final = erros_posicao[-1]

# 4. Erro de Orientação (Yaw) sem artifício dinâmico
def quaternion_to_yaw(x, y, z, w):
    r = R.from_quat(np.column_stack((x, y, z, w)))
    return r.as_euler('xyz', degrees=True)[:, 2]

amcl_yaw = quaternion_to_yaw(df_amcl[amcl_qx_col], df_amcl[amcl_qy_col], 
                             df_amcl[amcl_qz_col], df_amcl[amcl_qw_col])

gt_yaw = quaternion_to_yaw(gt_qx, gt_qy, gt_qz, gt_qw)

erros_orientacao = np.abs(amcl_yaw - gt_yaw)
erros_orientacao = np.where(erros_orientacao > 180, 360 - erros_orientacao, erros_orientacao)
rmse_orientacao = np.sqrt(np.mean(erros_orientacao**2))

# 5. Estabilidade da Localização (Desvio Padrão)
estabilidade_std = np.std(erros_posicao)

# --- EXIBIÇÃO DOS RESULTADOS ---
print("\n" + "="*50)
print("📊 RESULTADOS CIENTÍFICOS FIXOS: HECTOR SLAM + AMCL")
print("="*50)
print(f"🔹 Erro Médio de Posição:    {np.mean(erros_posicao):.4f} metros")
print(f"🔹 RMSE de Posição:         {rmse_posicao:.4f} metros")
print(f"🔹 Erro Final de Posição:   {erro_final:.4f} metros")
print(f"🔹 Erro Médio de Orientação: {np.mean(erros_orientacao):.4f} graus")
print(f"🔹 RMSE de Orientação:      {rmse_orientacao:.4f} graus")
print(f"🔹 Estabilidade (Desvio Padrão): {estabilidade_std:.4f}")
print("="*50)

# --- GERAR E SALVAR GRÁFICOS ---
print("📈 Gerando gráficos de desempenho...")
tempo = df_amcl['Time'] - df_amcl['Time'].iloc[0]

plt.figure(figsize=(14, 5))

# Gráfico 1: Estabilidade de Posição com Offset Fixo
plt.subplot(1, 2, 1)
plt.plot(tempo, erros_posicao, color='#2e7d32', linewidth=1.5, label='Erro Absoluto Calibrado')
plt.axhline(y=rmse_posicao, color='black', linestyle='--', label=f'RMSE ({rmse_posicao:.3f}m)')
plt.title('Estabilidade da Localização (Hector - URDF Offset)')
plt.xlabel('Tempo (segundos)')
plt.ylabel('Erro de Posição (metros)')
plt.grid(True, linestyle=':', alpha=0.6)
plt.legend()

# Gráfico 2: Erro Angular Puro (Yaw)
plt.subplot(1, 2, 2)
plt.plot(tempo, erros_orientacao, color='#1565c0', linewidth=1.5, label='Erro Angular Absoluto')
plt.axhline(y=np.mean(erros_orientacao), color='black', linestyle='--', label=f'Média ({np.mean(erros_orientacao):.2f}°)')
plt.title('Erro de Orientação Absoluta (Hector - Yaw)')
plt.xlabel('Tempo (segundos)')
plt.ylabel('Erro Angular (graus)')
plt.grid(True, linestyle=':', alpha=0.6)
plt.legend()

plt.tight_layout()
nome_grafico = 'analise_hector_amcl_fixo.png'
plt.savefig(nome_grafico, dpi=300)
print(f"💾 Gráfico científico salvo com sucesso como: '{nome_grafico}'")
print("🎉 Processamento concluído!")
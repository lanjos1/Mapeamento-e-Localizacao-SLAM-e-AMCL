import matplotlib
matplotlib.use('Agg')

import bagpy
from bagpy import bagreader
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.spatial.transform import Rotation as R
import os
import rosbag

def processar_bag(nome_bag, label_slam):
    print(f"\n🔄 Processando {label_slam} ({nome_bag})...")
    if not os.path.exists(nome_bag):
        print(f"❌ Arquivo '{nome_bag}' não encontrado. Pulando...")
        return None

    # Extração de AMCL
    b = bagreader(nome_bag)
    amcl_pose_csv = b.message_by_topic('/amcl_pose')
    df_amcl = pd.read_csv(amcl_pose_csv)

    # Extração de Ground Truth
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
                'Time': t.to_sec(), 'x': p.position.x, 'y': p.position.y,
                'qx': p.orientation.x, 'qy': p.orientation.y, 'qz': p.orientation.z, 'qw': p.orientation.w
            })
        except:
            continue
    bag.close()
    df_gt = pd.DataFrame(gt_dados)

    # Mapeamento de colunas do AMCL
    amcl_x_col = [c for c in df_amcl.columns if 'pose' in c and 'position.x' in c][0]
    amcl_y_col = [c for c in df_amcl.columns if 'pose' in c and 'position.y' in c][0]
    amcl_qx_col = [c for c in df_amcl.columns if 'pose' in c and 'orientation.x' in c][0]
    amcl_qy_col = [c for c in df_amcl.columns if 'pose' in c and 'orientation.y' in c][0]
    amcl_qz_col = [c for c in df_amcl.columns if 'pose' in c and 'orientation.z' in c][0]
    amcl_qw_col = [c for c in df_amcl.columns if 'pose' in c and 'orientation.w' in c][0]

    # Interpolação temporal
    gt_x_interp = np.interp(df_amcl['Time'], df_gt['Time'], df_gt['x'])
    gt_y_interp = np.interp(df_amcl['Time'], df_gt['Time'], df_gt['y'])
    gt_qx = np.interp(df_amcl['Time'], df_gt['Time'], df_gt['qx'])
    gt_qy = np.interp(df_amcl['Time'], df_gt['Time'], df_gt['qy'])
    gt_qz = np.interp(df_amcl['Time'], df_gt['Time'], df_gt['qz'])
    gt_qw = np.interp(df_amcl['Time'], df_gt['Time'], df_gt['qw'])

    amcl_x = df_amcl[amcl_x_col].values
    amcl_y = df_amcl[amcl_y_col].values

    # =========================================================================
    # 📐 ABORDAGEM COM VALORES FIXOS DO URDF (CORREÇÃO DE SINAL)
    # =========================================================================
    # Valores extraídos do arquivo gazebo_ground_truth.urdf do lar_gazebo
    X_OFFSET_URDF = -4.65
    Y_OFFSET_URDF = -3.0

    # A correção correta do vetor exige a soma algébrica dos referenciais
    gt_x_alinhado = gt_x_interp + X_OFFSET_URDF
    gt_y_alinhado = gt_y_interp + Y_OFFSET_URDF

    # Cálculo dos Erros de Posição absolutos após o alinhamento geométrico do mapa
    erros_pos = np.sqrt((amcl_x - gt_x_alinhado)**2 + (amcl_y - gt_y_alinhado)**2)
    rmse_pos = np.sqrt(np.mean(erros_pos**2))
    erro_fin_pos = erros_pos[-1]

    # --- Tratamento de Orientação Angular (Yaw) ---
    def quat_to_yaw(x, y, z, w):
        r = R.from_quat(np.column_stack((x, y, z, w)))
        return r.as_euler('xyz', degrees=True)[:, 2]

    amcl_yaw = quat_to_yaw(df_amcl[amcl_qx_col], df_amcl[amcl_qy_col], df_amcl[amcl_qz_col], df_amcl[amcl_qw_col])
    gt_yaw = quat_to_yaw(gt_qx, gt_qy, gt_qz, gt_qw)
    
    # Diferença angular pura entre os tópicos
    erros_ori = np.abs(amcl_yaw - gt_yaw)
    erros_ori = np.where(erros_ori > 180, 360 - erros_ori, erros_ori)
    rmse_ori = np.sqrt(np.mean(erros_ori**2))

    tempo = df_amcl['Time'] - df_amcl['Time'].iloc[0]

    return {
        'tempo': tempo, 'erros_pos': erros_pos, 'erros_ori': erros_ori,
        'rmse_pos': rmse_pos, 'mean_pos': np.mean(erros_pos), 'final_pos': erro_fin_pos,
        'rmse_ori': rmse_ori, 'mean_ori': np.mean(erros_ori), 'std_pos': np.std(erros_pos)
    }

# --- EXECUÇÃO DO CONFRONTO ---
res_hector = processar_bag('resultados_amcl_hector.bag', 'Hector SLAM')
res_gmapping = processar_bag('resultados_amcl_gmapping.bag', 'Gmapping')

print("\n" + "="*60)
print("📊 RESULTADOS COM AMCL")
print("="*60)
print(f"{'Métrica Analisada':<30} | {'Hector SLAM':<12} | {'Gmapping':<12}")
print("-"*60)
if res_hector and res_gmapping:
    print(f"{'Erro Médio de Posição (m)':<30} | {res_hector['mean_pos']:<12.4f} | {res_gmapping['mean_pos']:<12.4f}")
    print(f"{'RMSE de Posição (m)':<30} | {res_hector['rmse_pos']:<12.4f} | {res_gmapping['rmse_pos']:<12.4f}")
    print(f"{'Erro Final de Posição (m)':<30} | {res_hector['final_pos']:<12.4f} | {res_gmapping['final_pos']:<12.4f}")
    print(f"{'Erro Médio de Orientação (°)':<30} | {res_hector['mean_ori']:<12.4f} | {res_gmapping['mean_ori']:<12.4f}")
    print(f"{'RMSE de Orientação (°)':<30} | {res_hector['rmse_ori']:<12.4f} | {res_gmapping['rmse_ori']:<12.4f}")
    print(f"{'Estabilidade (Desvio Padrão)':<30} | {res_hector['std_pos']:<12.4f} | {res_gmapping['std_pos']:<12.4f}")
print("="*60)

if res_hector and res_gmapping:
    print("📈 Gerando gráfico comparativo com offset fixo...")
    plt.figure(figsize=(15, 6))

    # Plot Posição
    plt.subplot(1, 2, 1)
    plt.plot(res_hector['tempo'], res_hector['erros_pos'], color='#b71c1c', label=f"Hector Fix (RMSE: {res_hector['rmse_pos']:.3f}m)", alpha=0.8)
    plt.plot(res_gmapping['tempo'], res_gmapping['erros_pos'], color='#e65100', label=f"Gmapping Fix (RMSE: {res_gmapping['rmse_pos']:.3f}m)", alpha=0.8)
    plt.title('Comparativo Fixo: Estabilidade do Erro de Posição')
    plt.xlabel('Tempo (segundos)')
    plt.ylabel('Erro (metros)')
    plt.grid(True, linestyle=':', alpha=0.6)
    plt.legend()

    # Plot Orientação
    plt.subplot(1, 2, 2)
    plt.plot(res_hector['tempo'], res_hector['erros_ori'], color='#0d47a1', label=f"Hector Fix (RMSE: {res_hector['rmse_ori']:.2f}°)", alpha=0.8)
    plt.plot(res_gmapping['tempo'], res_gmapping['erros_ori'], color='#004d40', label=f"Gmapping Fix (RMSE: {res_gmapping['rmse_ori']:.2f}°)", alpha=0.8)
    plt.title('Comparativo Fixo: Erro Angular (Yaw)')
    plt.xlabel('Tempo (segundos)')
    plt.ylabel('Erro (graus)')
    plt.grid(True, linestyle=':', alpha=0.6)
    plt.legend()

    plt.tight_layout()
    nome_grafico = 'analise_comparativa_amcl_fixo.png'
    plt.savefig(nome_grafico, dpi=300)
    print(f"💾 Gráfico salvo com sucesso como: '{nome_grafico}'")
    print("🎉 Processamento concluído!")
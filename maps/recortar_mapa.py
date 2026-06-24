import cv2
import numpy as np

# 1. Carrega o arquivo PGM bruto gerado pelo Gmapping
nome_mapa_pgm = 'mapa_gmapping.pgm' # Substitua pelo nome correto do seu .pgm se for diferente

img_pgm = cv2.imread(nome_mapa_pgm, cv2.IMREAD_GRAYSCALE)

if img_pgm is None:
    print(f"❌ Não foi possível encontrar o arquivo '{nome_mapa_pgm}' nesta pasta.")
    exit()

altura, largura = img_pgm.shape
print(f"Dimensões originais do PGM: {largura}x{altura} pixels")

# =========================================================================
# ✂️ RECORTE: O SEGREDO PARA APROXIMAR (RETIRAR O ESPAÇO VAZIO)
# O Gmapping cria uma imagem gigante (ex: 2048x2048 ou 4000x4000) cheia de cinza.
# Mude as porcentagens abaixo para "enquadrar" apenas a sua sala do LAR.
# =========================================================================
# Pegando apenas o miolo do mapa (de 45% a 55%)
x_inicial, x_final = int(largura * 0.45), int(largura * 0.55)
y_inicial, y_final = int(altura * 0.45), int(altura * 0.55)

mapa_recortado = img_pgm[y_inicial:y_final, x_inicial:x_final]

# =========================================================================
# 🔍 SUPER ZOOM SEM PERDA (INTERPOLAÇÃO VIZINHO MAIS PRÓXIMO)
# =========================================================================
fator_zoom = 18  # Aumenta o tamanho em 8 vezes! (Altere para 4, 6, 10 conforme desejar)

mapa_final_zoom = cv2.resize(
    mapa_recortado, 
    (0, 0), 
    fx=fator_zoom, 
    fy=fator_zoom, 
    interpolation=cv2.INTER_NEAREST
)

# 3. Salva diretamente em PNG de alta resolução para colocar no Word/LaTeX
nome_saida = 'mapa_gmapping_alta_resolucao.png'
cv2.imwrite(nome_saida, mapa_final_zoom)

print(f"🎉 Sucesso! Mapa com super-zoom salvo em: '{nome_saida}'")
# Atividade Prática: Mapeamento e Localização com SLAM + AMCL

## Base

Esta atividade utiliza como infraestrutura o repositório **[lar-deeufba/lar_gazebo](https://github.com/lar-deeufba/lar_gazebo)**, desenvolvido pelo Laboratório de Automação e Robótica (LAR) do DEE/UFBA. Ele fornece:

- O **modelo 3D do laboratório LAR** para simulação no Gazebo
- O **robô Husky** configurado para o ambiente
- Os **scripts de container Docker** (`build.sh`, `run_husky.sh`, `shell.sh`) que encapsulam todo o ambiente ROS Noetic

Clone o repositório antes de iniciar:

```bash
git clone https://github.com/lar-deeufba/lar_gazebo.git ~/lar_gazebo-noetic
```

---

## Objetivo

Gerar mapas do ambiente de simulação usando dois algoritmos de SLAM (**GMapping** e **Hector SLAM**), executar o **AMCL** sobre cada mapa gerado e comparar a pose estimada com o ground truth fornecido pelo Gazebo.

---

## Visão Geral

```
sensores_laboratorio.bag      → Bag usada para gerar os mapas
bag_teste_localizacao.bag     → Bag usada para rodar o AMCL
resultados_amcl_gmapping.bag  → Gravação dos resultados com mapa do GMapping
resultados_amcl_hector.bag    → Gravação dos resultados com mapa do Hector SLAM
```

---

## Parte 1 — Geração de Mapas

### 1.1 Gravar a bag de sensores (caso não tenha)

Abra 3 terminais:

**Terminal 1 — Robô no mundo:**
```bash
cd ~/lar_gazebo-noetic
./scripts/run_husky.sh
```

**Terminal 2 — Gravação da bag:**
```bash
cd ~/lar_gazebo-noetic && ./scripts/shell.sh
cd /ws/src/lar_gazebo/maps/
rosbag record /front/scan /odometry/filtered /tf /tf_static -O sensores_laboratorio.bag
```

**Terminal 3 — Teleop:**
```bash
cd ~/lar_gazebo-noetic && ./scripts/shell.sh
rosrun teleop_twist_keyboard teleop_twist_keyboard.py
```

Navegue pelo ambiente até cobrir bem o espaço, depois encerre a gravação com `Ctrl+C` no Terminal 2.

---

### 1.2 Gerar mapa com GMapping

**Terminal 1 — roscore:**
```bash
cd ~/lar_gazebo-noetic && ./scripts/shell.sh
roscore
```

**Terminal 2 — GMapping:**
```bash
cd ~/lar_gazebo-noetic && ./scripts/shell.sh
rosparam set use_sim_time true
rosrun gmapping slam_gmapping scan:=front/scan _base_frame:=base_link _odom_frame:=odom _map_frame:=map
```

**Terminal 3 — Reproduzir a bag:**
```bash
cd ~/lar_gazebo-noetic && ./scripts/shell.sh
cd /ws/src/lar_gazebo/maps/
rosbag play --clock sensores_laboratorio.bag
```

**Terminal 4 — Salvar o mapa (após a bag terminar):**
```bash
cd ~/lar_gazebo-noetic && ./scripts/shell.sh
cd /ws/src/lar_gazebo/maps/
rosrun map_server map_saver -f mapa_gmapping
```

> Serão gerados os arquivos `mapa_gmapping.pgm` e `mapa_gmapping.yaml`.

---

### 1.3 Gerar mapa com Hector SLAM

**Terminal 1 — roscore:**
```bash
cd ~/lar_gazebo-noetic && ./scripts/shell.sh
roscore
```

**Terminal 2 — Hector SLAM:**
```bash
cd ~/lar_gazebo-noetic && ./scripts/shell.sh
rosparam set use_sim_time true
roslaunch lar_gazebo hector_slam.launch
```

**Terminal 3 — Reproduzir a bag:**
```bash
cd ~/lar_gazebo-noetic && ./scripts/shell.sh
cd /ws/src/lar_gazebo/maps/
rosbag play --clock sensores_laboratorio.bag
```

**Terminal 4 — Salvar o mapa (após a bag terminar):**
```bash
cd ~/lar_gazebo-noetic && ./scripts/shell.sh
cd /ws/src/lar_gazebo/maps/
rosrun map_server map_saver -f mapa_hector
```

> Serão gerados os arquivos `mapa_hector.pgm` e `mapa_hector.yaml`.

---

## Parte 2 — Gravar bag de localização (caso não tenha)

Abra 3 terminais:

**Terminal 1 — Robô no mundo:**
```bash
cd ~/lar_gazebo-noetic
./scripts/run_husky.sh
```

**Terminal 2 — Gravação:**
```bash
cd ~/lar_gazebo-noetic && ./scripts/shell.sh
cd /ws/src/lar_gazebo/maps/
rosbag record /front/scan /odometry/filtered /tf /tf_static /gazebo/model_states -O bag_teste_localizacao.bag
```

**Terminal 3 — Teleop:**
```bash
cd ~/lar_gazebo-noetic && ./scripts/shell.sh
rosrun teleop_twist_keyboard teleop_twist_keyboard.py
```

---

## Parte 3 — AMCL sobre o mapa do Hector SLAM

**Terminal 0 — roscore:**
```bash
cd ~/lar_gazebo-noetic && ./scripts/shell.sh
roscore
```

**Terminal 1 — Carregar mapa:**
```bash
rosparam set use_sim_time true
rosrun map_server map_server /ws/src/lar_gazebo/maps/mapa_hector.yaml
```

**Terminal 2 — AMCL:**
```bash
cd ~/lar_gazebo-noetic && ./scripts/shell.sh
rosrun amcl amcl scan:=/front/scan _base_frame_id:=base_link _odom_frame_id:=odom _global_frame_id:=map
```

**Terminal 3 — Gravar resultados:**
```bash
rosbag record /amcl_pose /gazebo/model_states -O resultados_amcl_hector.bag
```

**Terminal 4 — Reproduzir bag de localização:**
```bash
cd /ws/src/lar_gazebo/maps/
rosbag play --clock bag_teste_localizacao.bag
```

**Terminal 5 — RViz (opcional, para visualização):**
```bash
cd ~/lar_gazebo-noetic && ./scripts/shell.sh
rosrun rviz rviz
```

No RViz, configure:
- Fixed Frame → `map`
- Adicione: `Map` (`/map`), `PoseArray` (`/particlecloud`), `LaserScan` (`/front/scan`), `RobotModel`

---

## Parte 4 — AMCL sobre o mapa do GMapping

**Terminal 1 — roscore:**
```bash
cd ~/lar_gazebo-noetic && ./scripts/shell.sh
roscore
```

**Terminal 2 — Carregar mapa e publisher do robô:**
```bash
cd ~/lar_gazebo-noetic && ./scripts/shell.sh
rosparam set use_sim_time true
rosrun map_server map_server /ws/src/lar_gazebo/maps/mapa_gmapping.yaml &
roslaunch husky_description description.launch &
rosrun robot_state_publisher robot_state_publisher
```

**Terminal 3 — AMCL:**
```bash
cd ~/lar_gazebo-noetic && ./scripts/shell.sh
rosrun amcl amcl scan:=/front/scan _base_frame_id:=base_link _odom_frame_id:=odom _global_frame_id:=map
```

**Terminal 4 — RViz:**
```bash
cd ~/lar_gazebo-noetic && ./scripts/shell.sh
rosrun rviz rviz
```

**Terminal 5 — Gravar resultados:**
```bash
cd /ws/src/lar_gazebo/
rosbag record /amcl_pose /gazebo/model_states -O resultados_amcl_gmapping.bag
```

**Terminal 6 — Reproduzir bag de localização:**
```bash
cd /ws/src/lar_gazebo/maps/
rosbag play --clock bag_teste_localizacao.bag
```

---

## Parte 5 — Análise dos Resultados

### Instalar dependências

```bash
cd ~/lar_gazebo-noetic && ./scripts/shell.sh
pip install "numpy==1.17.4" "pandas<1.0.0" "scipy<1.5.0" matplotlib
pip install bagpy --no-dependencies
pip install seaborn --no-deps
pip install packaging pyyaml --no-deps
```

### Rodar scripts de análise

```bash
cd /src/lar_gazebo/maps
python3 analise_amcl_hector_slam.py
python3 analise_amcl_gmapping.py
python3 analise_amcl_comparativo.py
```

---

## Parte 6 — Resultados Obtidos e Discussão

### GMapping + AMCL

| Métrica                     | Valor    |
|-----------------------------|----------|
| Erro Médio de Posição       | 0.6488 m |
| RMSE de Posição             | 0.7179 m |
| Erro Final de Posição       | 1.0535 m |
| Erro Médio de Orientação    | 3.1316°  |
| RMSE de Orientação          | 3.9410°  |
| Estabilidade (Desvio Padrão)| 0.3072 m |

### Hector SLAM + AMCL

| Métrica                     | Valor    |
|-----------------------------|----------|
| Erro Médio de Posição       | 0.7631 m |
| RMSE de Posição             | 0.8498 m |
| Erro Final de Posição       | 1.2919 m |
| Erro Médio de Orientação    | 2.5432°  |
| RMSE de Orientação          | 3.1249°  |
| Estabilidade (Desvio Padrão)| 0.3741 m |

### Confronto Direto

| Métrica                        | Hector SLAM | GMapping | Vencedor   |
|-------------------------------|-------------|----------|------------|
| Erro Médio de Posição (m)     | 0.7631      | 0.6488   | GMapping ✅ |
| RMSE de Posição (m)           | 0.8498      | 0.7179   | GMapping ✅ |
| Erro Final de Posição (m)     | 1.2919      | 1.0535   | GMapping ✅ |
| Erro Médio de Orientação (°)  | 2.5432      | 3.1316   | Hector ✅  |
| RMSE de Orientação (°)        | 3.1249      | 3.9410   | Hector ✅  |
| Estabilidade (Desvio Padrão)  | 0.3741      | 0.3072   | GMapping ✅ |

### Análise Crítica

**Por que o GMapping venceu em posição e estabilidade?**
O GMapping usa um filtro de partículas Rao-Blackwellized que integra ativamente os dados de odometria durante a construção do mapa. Como o Gazebo fornece odometria com baixo ruído, o mapa gerado apresenta melhor consistência geométrica global, favorecendo a localização do AMCL.

**Por que o Hector SLAM venceu em orientação?**
O Hector SLAM ignora a odometria e baseia-se exclusivamente em scan matching de alta frequência do LIDAR. Essa abordagem o torna mais preciso na detecção de rotações, gerando bordas angulares mais nítidas no mapa e permitindo que o AMCL estime o ângulo Yaw com menor erro.

**Drift acumulado:**
Em ambos os algoritmos, o Erro Final de Posição é maior que o Erro Médio. Esse comportamento é esperado na literatura: pequenas incertezas se acumulam ao longo do tempo, gerando uma deriva gradual que cresce com a distância percorrida.

---

## Referências

- **lar-deeufba/lar_gazebo** — Repositório base com o modelo 3D do LAR/UFBA, robô Husky e scripts de container: https://github.com/lar-deeufba/lar_gazebo
- ROS Wiki — [gmapping](http://wiki.ros.org/gmapping)
- ROS Wiki — [hector_slam](http://wiki.ros.org/hector_slam)
- ROS Wiki — [amcl](http://wiki.ros.org/amcl)
- ROS Wiki — [map_server](http://wiki.ros.org/map_server)
- Gazebo Simulator — http://gazebosim.org/
- Husky UGV (ROS) — http://wiki.ros.org/Robots/Husky

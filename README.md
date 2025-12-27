# 🔋 Smart Battery Manager for macOS

Uma implementação **open‑source**, leve e programável para ajudar a prolongar a vida útil de baterias em Macs com Apple Silicon.

> Projetado para uso em máquinas que ficam muito tempo na tomada. Este projeto atua em conjunto com a CLI `battery` para aplicar limites de carga, proteção térmica ativa e um modo de histerese para evitar micro‑ciclos.

---

## 📋 Sumário

- [Motivação e Ciência](#-motivação-e-ciência)
- [Funcionalidades](#-funcionalidades)
- [Requisitos](#-requisitos)
- [Instalação](#-instalação)
- [Uso e Configuração](#-uso-e-configuração)
- [Serviço (LaunchAgent)](#-serviço-launchagent)
- [Referências](#-referências)
- [Contribuir](#-contribuir)
- [Licença](#-licença)

---

## 🔬 Motivação e Ciência

Este projeto aplica princípios eletroquímicos aceitos para reduzir os principais vetores de degradação das baterias de íon‑lítio:

- Limitar a carga final (~80%) reduz a tensão e a oxidação da interface (SEI).
- Controlar temperatura (pausar carregamento acima de ~33°C) evita aceleração da degradação.
- Usar um intervalo de recarga (80% → 75%) a cada 12 horas evita micro‑ciclos constantes ao mesmo tempo que evita a tensão elétrica constante para manter sempre em 80%.

> "A redução da tensão de fim de carga de 4.2V para 4.1V prolonga a vida útil em ciclos consideravelmente." — Battery University

---

## 🚀 Funcionalidades

- **Proteção térmica**: pausa carregamento ao ultrapassar `MAX_TEMP_TRIGGER` (padrão 33°C).
- **Sailing Cooldown**: Após carregar até `TARGET_LIMIT` (Padrão 80%), o script trava a carga (Hold Mode) usando energia da parede por 12 horas. Só após esse período ele permite um novo ciclo de relaxamento (Sailing).
- **Force Discharge**: comandos que instruem o macOS a parar/permitir carga quando necessário.
- **Leve**: único script Python rodando em background com baixo uso de CPU.

---

## 📋 Requisitos

- macOS (Apple Silicon: M1/M2/M3/M4)
- Python 3
- CLI `battery` (https://github.com/actuallymentor/battery)

---

## 🛠️ Instalação

### Instalação rápida (recomendada)

```bash
git clone https://github.com/ttholmes/mac-smart-battery-manager.git
cd mac-smart-battery-manager
chmod +x install.sh
./install.sh
```

O instalador cuida de instalar dependências (via Homebrew), copiar o script e registrar o LaunchAgent.

### Instalação manual

1. Instale a CLI `battery`:

```bash
brew install battery
```

2. Copie o script para um diretório de sua escolha (ex.: `~/scripts`) e torne executável:

```bash
mkdir -p ~/scripts
cp src/battery_manager.py ~/scripts/
chmod +x ~/scripts/battery_manager.py
```

3. Copie e carregue o LaunchAgent (edite o `plist` para ajustar caminhos):

```bash
cp com.user.batterymanager.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.user.batterymanager.plist
```

---

## ⚙️ Uso e Configuração

Edite as variáveis no topo de `src/battery_manager.py` para ajustar o comportamento:

```python
MAX_TEMP_TRIGGER = 33.0   # Temperatura máxima permitida
TARGET_LIMIT = 80         # % de carga máxima
SAILING_FLOOR = 75        # % para reativar recarga
CHECK_INTERVAL = 45       # segundos entre checagens
```

---

## 📂 Serviço (LaunchAgent)

- O arquivo `com.user.batterymanager.plist` no repositório é um exemplo para `~/Library/LaunchAgents/`.
- Edite os caminhos dentro do `plist` para apontar para onde você instalou o script.
- Carregue com `launchctl load ~/Library/LaunchAgents/com.user.batterymanager.plist`.

---

## 📚 Referências

- Battery University — How to Prolong Lithium‑based Batteries: https://batteryuniversity.com/article/bu-808-how-to-prolong-lithium-based-batteries
- Sandia National Laboratories — Battery publications: https://www.sandia.gov/ess-ssl/publications/
- Nature — Degradation factors of commercial lithium‑ion batteries: https://www.nature.com/articles/s41598-017-15064-0

---

## 🤝 Contribuir

Contribuições são bem‑vindas: abra issues ou PRs. Siga o padrão de código e escreva testes quando possível.

---

## 📄 License

[MIT](LICENSE)

---

## ⚠️ Isenção de Responsabilidade

Este software manipula configurações de energia do hardware. Use por sua conta e risco.

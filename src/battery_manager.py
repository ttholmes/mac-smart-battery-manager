#!/usr/bin/env python3
"""
Smart Battery Manager for macOS (Apple Silicon)
Features: Thermal Protection, Sailing Mode, Force Discharge.
License: MIT
"""
#!/usr/bin/env python3
import subprocess
import time
import re
import os
import json
import shutil
import sys
from datetime import datetime

# ==============================================================================
# CONFIGURAÇÕES DO USUÁRIO
# ==============================================================================

# --- PROTEÇÃO TÉRMICA ---
# Se a bateria passar de 33°C, o carregamento é cortado IMEDIATAMENTE.
MAX_TEMP_TRIGGER = 33.0    

# Temperatura segura para retomar o funcionamento normal.
SAFE_TEMP_RESUME = 29.0    

# --- SAILING MODE (HISTERESE) ---
# Teto de carga: O Mac carrega até aqui.
TARGET_LIMIT = 80          

# Chão do Sailing: Forçamos a descarga até aqui antes de voltar a carregar.
SAILING_FLOOR = 75         

# Intervalo de checagem em segundos.
CHECK_INTERVAL = 45

# Caminho para salvar o estado (persistência entre reboots).
STATE_FILE = os.path.expanduser("~/scripts/battery_state.json")

# ==============================================================================
# FUNÇÕES DO SISTEMA
# ==============================================================================

# Busca o binário 'battery'
def find_battery_cli():
    """Localiza o binário 'battery'."""
    trusted_paths = [
        "/opt/homebrew/bin/battery",
        "/usr/local/bin/battery",
        f"/Users/{os.environ.get('USER')}/.local/bin/battery"
    ]
    for p in trusted_paths:
        if os.path.exists(p) and os.access(p, os.X_OK):
            return p        
    cmd_from_path = shutil.which("battery")
    if cmd_from_path:
        if cmd_from_path.startswith("/usr") or cmd_from_path.startswith("/opt"):
            return cmd_from_path
            
    return None


BATTERY_CMD = find_battery_cli()

def log(msg):
    """Log simples com timestamp."""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def get_status():
    """
    Lê o status atual do hardware via IOReg e PMSet.
    Retorna: (porcentagem_int, temperatura_float)
    """
    try:
        # 1. Temperatura (Apple Silicon)
        res_temp = subprocess.check_output(
            ["ioreg", "-r", "-n", "AppleSmartBattery"], 
            stderr=subprocess.DEVNULL
        ).decode("utf-8")
        match_temp = re.search(r'"Temperature"\s*=\s*(\d+)', res_temp)
        temp = int(match_temp.group(1)) / 100.0 if match_temp else 0.0
        
        # 2. Porcentagem
        res_batt = subprocess.check_output(
            ["pmset", "-g", "batt"], 
            stderr=subprocess.DEVNULL
        ).decode("utf-8")
        match_batt = re.search(r'(\d+)%', res_batt)
        level = int(match_batt.group(1)) if match_batt else 100
        
        return level, temp
    except:
        return 100, 0.0

def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return {"mode": "charging", "heat_paused": False}

def save_state(state):
    try:
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f)
    except:
        pass

def execute_battery_cmd(action, value=None):
    """
    Executa comandos do CLI 'battery'.
    Trata erros de sintaxe enviando argumentos corretamente.
    """
    if not BATTERY_CMD:
        log("❌ ERRO: Comando 'battery' não encontrado.")
        return

    args = [BATTERY_CMD, action]
    if value is not None:
        args.append(str(value))
    
    try:
        # Log de debug opcional (descomente para ver os comandos reais)
        # log(f"DEBUG EXEC: battery {action} {value if value else ''}")
        subprocess.run(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        log(f"Erro ao executar comando: {e}")

# ==============================================================================
# LOOP PRINCIPAL
# ==============================================================================

def main():
    if not BATTERY_CMD:
        print("❌ ERRO CRÍTICO: Ferramenta CLI 'battery' não encontrada.")
        print("   Instale com: brew install battery")
        sys.exit(1)

    log(f"🔋 Smart Battery Manager Iniciado.")
    log(f"   Configs: Teto {TARGET_LIMIT}% | Piso {SAILING_FLOOR}% | Max Temp {MAX_TEMP_TRIGGER}°C")
    
    while True:
        level, temp = get_status()
        state = load_state()
        
        # --- 1. LÓGICA DE PROTEÇÃO TÉRMICA ---
        # Prioridade máxima: Se esquentar, corta tudo.
        
        if temp >= MAX_TEMP_TRIGGER and not state.get("heat_paused"):
            log(f"🔥 ALERTA TÉRMICO ({temp}°C).")
            log(f"   Ação: Forçando descarga até 20% para esfriar bateria.")
            
            # Isso força o Mac a parar de puxar energia da parede.
            execute_battery_cmd("discharge", 20)
            
            state["heat_paused"] = True
            save_state(state)
            
        elif temp <= SAFE_TEMP_RESUME and state.get("heat_paused"):
            log(f"❄️ Temperatura normalizada ({temp}°C). Retomando operação.")
            
            state["heat_paused"] = False
            state["mode"] = "re-evaluate" # Força rechecagem imediata
            save_state(state)

        # --- 2. LÓGICA DE SAILING / CARGA ---
        # Só roda se a temperatura estiver ok
        
        if not state.get("heat_paused"):
            current_mode = state.get("mode", "charging")
            
            # >> MODO: CARREGANDO (Subindo)
            if current_mode == "charging" or current_mode == "re-evaluate":
                
                # Se viemos de um reset, garantimos porta aberta
                if current_mode == "re-evaluate":
                    execute_battery_cmd("limit", TARGET_LIMIT)
                    state["mode"] = "charging"
                    save_state(state)

                # Verifica se atingimos o teto
                if level >= TARGET_LIMIT:
                    log(f"⚓️ Teto atingido ({level}%). Ativando SAILING FORÇADO.")
                    log(f"   Ação: Descarregando ativamente até {SAILING_FLOOR}%.")
                    
                    # Isso garante que o Mac pare de carregar.
                    execute_battery_cmd("discharge", SAILING_FLOOR)
                    
                    state["mode"] = "sailing"
                    save_state(state)

            # >> MODO: SAILING
            elif current_mode == "sailing":
                # Verifica se atingimos o piso
                if level <= SAILING_FLOOR:
                    log(f"⚡️ Piso atingido ({level}%). Iniciando RECARGA.")
                    log(f"   Ação: Limite restaurado para {TARGET_LIMIT}%.")
                    
                    # Libera o carregamento novamente
                    execute_battery_cmd("limit", TARGET_LIMIT)
                    
                    state["mode"] = "charging"
                    save_state(state)
                
                # Nota: Se estiver entre Piso e Teto descendo, o comando 'discharge'
                # enviado anteriormente continua valendo, então o Mac continua usando bateria.

        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n🛑 Encerrando Smart Battery Manager.")


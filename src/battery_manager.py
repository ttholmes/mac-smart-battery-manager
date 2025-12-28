#!/usr/bin/env python3
"""
Smart Battery Manager for macOS (Apple Silicon)
Features: Thermal Protection, Smart Sailing Cooldown, Force Discharge.
License: MIT
"""
import subprocess
import time
import re
import os
import json
import shutil
import sys
from datetime import datetime, timedelta
import urllib.request

# ==============================================================================
# METADADOS E ATUALIZAÇÃO
# ==============================================================================
VERSION = "1.0"
GITHUB_RAW_URL = "https://raw.githubusercontent.com/ttholmes/mac-smart-battery-manager/main/src/battery_manager.py"

# ==============================================================================
# CONFIGURAÇÕES TÉCNICAS
# ==============================================================================

# PROTEÇÃO TÉRMICA
MAX_TEMP_TRIGGER = 35.0    # C° - Para tudo se passar daqui
SAFE_TEMP_RESUME = 31.0    # C° - Retoma operação normal
THERMAL_THROTTLE_TEMP = 30.0 # C° - Reduz limite de carga preventivamente

# LIMITES DE CARGA
TARGET_LIMIT_NORMAL = 80   # % - Limite padrão
TARGET_LIMIT_HOT = 70      # % - Limite no calor (>30°C)
SAILING_DROP = 5           # % - Histerese (80 -> 75)

# FREQUÊNCIA DE SAILING 
# Tempo mínimo em horas entre dois ciclos de Sailing forçado.
# Evita micro-ciclagens excessivas se a bateria descarregar rápido.
SAILING_COOLDOWN_HOURS = 12 

CHECK_INTERVAL = 45
STATE_FILE = os.path.expanduser("~/scripts/battery_state.json")

# ==============================================================================
# FUNÇÕES DE SISTEMA
# ==============================================================================

def find_battery_cli():
    """Busca segura do binário battery"""
    trusted_paths = [
        "/opt/homebrew/bin/battery",
        "/usr/local/bin/battery",
        f"/Users/{os.environ.get('USER')}/.local/bin/battery"
    ]
    for p in trusted_paths:
        if os.path.exists(p) and os.access(p, os.X_OK): return p
    
    cmd = shutil.which("battery")
    if cmd and (cmd.startswith("/usr") or cmd.startswith("/opt")): return cmd
    return None

BATTERY_CMD = find_battery_cli()

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def get_status():
    """Retorna (nivel, temp)"""
    try:
        res_temp = subprocess.check_output(["ioreg", "-r", "-n", "AppleSmartBattery"], stderr=subprocess.DEVNULL).decode("utf-8")
        match_temp = re.search(r'"Temperature"\s*=\s*(\d+)', res_temp)
        temp = int(match_temp.group(1)) / 100.0 if match_temp else 0.0
        
        res_batt = subprocess.check_output(["pmset", "-g", "batt"], stderr=subprocess.DEVNULL).decode("utf-8")
        match_batt = re.search(r'(\d+)%', res_batt)
        level = int(match_batt.group(1)) if match_batt else 100
        return level, temp
    except: return 100, 0.0

def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r') as f: return json.load(f)
        except: pass
    # last_charge_time: Timestamp de quando a bateria atingiu o teto pela última vez
    return {"mode": "charging", "heat_paused": False, "last_charge_time": 0}

def save_state(state):
    try:
        with open(STATE_FILE, 'w') as f: json.dump(state, f)
    except: pass

def execute_battery_cmd(action, value=None):
    if not BATTERY_CMD: return
    args = [BATTERY_CMD, action]
    if value is not None: args.append(str(value))
    try: subprocess.run(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except: pass

    def check_for_updates():
    """
    Verifica se há uma nova versão no GitHub.
    Lê o arquivo remoto, busca a string VERSION e compara.
    """
    try:
        log("🔍 Verificando atualizações...")
        # Timeout curto para não travar o boot do script caso esteja sem internet
        with urllib.request.urlopen(GITHUB_RAW_URL, timeout=5) as response:
            remote_code = response.read().decode('utf-8')
            
            # Busca a versão no código remoto usando Regex
            match = re.search(r'VERSION\s*=\s*"([\d\.]+)"', remote_code)
            if match:
                remote_version = match.group(1)
                if remote_version > VERSION:
                    log(f"✨ Nova versão disponível: v{remote_version} (Atual: v{VERSION})")
                    send_notification(
                        "Atualização Disponível!", 
                        f"Nova versão v{remote_version} do Smart Battery. Rode 'git pull' para atualizar."
                    )
                else:
                    log("✅ Script atualizado.")
    except Exception as e:
        log(f"⚠️ Não foi possível verificar atualizações: {e}")

def send_notification(title, message):
    """Envia notificação nativa do macOS"""
    try:
        clean_msg = message.replace('"', '\\"')
        clean_title = title.replace('"', '\\"')
        
        script = f'display notification "{clean_msg}" with title "{clean_title}" sound name "Glass"'
        subprocess.run(["osascript", "-e", script])
    except: pass

# ==============================================================================
# LÓGICA PRINCIPAL 
# ==============================================================================

def main():
    if not BATTERY_CMD:
        print("❌ ERRO CRÍTICO: 'battery' CLI não encontrado.")
        sys.exit(1)

    log(f"🔋 Smart Battery v{VERSION} Iniciado.")
    check_for_updates()
    log(f"   Cooldown de Sailing: {SAILING_COOLDOWN_HOURS} horas")
    
    while True:
        level, temp = get_status()
        state = load_state()
        now = time.time()
        
        # --- CÁLCULO DE LIMITES ---
        target_limit = TARGET_LIMIT_HOT if temp >= THERMAL_THROTTLE_TEMP else TARGET_LIMIT_NORMAL
        sailing_floor = target_limit - SAILING_DROP

        # --- 1. PROTEÇÃO TÉRMICA (Prioridade Máxima) ---
        if temp >= MAX_TEMP_TRIGGER and not state.get("heat_paused"):
            log(f"🔥 ALERTA TÉRMICO ({temp}°C). Forçando descarga de emergência.")
            execute_battery_cmd("discharge", 20)
            state["heat_paused"] = True
            save_state(state)
            
        elif temp <= SAFE_TEMP_RESUME and state.get("heat_paused"):
            log(f"❄️ Temperatura segura ({temp}°C). Retomando.")
            state["heat_paused"] = False
            state["mode"] = "re-evaluate"
            save_state(state)

        # --- 2. GESTÃO DE CARGA E SAILING ---
        if not state.get("heat_paused"):
            current_mode = state.get("mode", "charging")
            last_charge = state.get("last_charge_time", 0)
            
            # >> MODO: CARREGANDO
            if current_mode == "charging" or current_mode == "re-evaluate":
                if current_mode == "re-evaluate":
                    execute_battery_cmd("limit", target_limit)
                    state["mode"] = "charging"
                    save_state(state)

                if level >= target_limit:
                    # Bateu no teto. Verifica se podemos fazer Sailing (Cooldown)
                    hours_since_last = (now - last_charge) / 3600
                    
                    if hours_since_last >= SAILING_COOLDOWN_HOURS:
                        # Cooldown ok -> Inicia Sailing
                        log(f"⚓️ Teto atingido ({level}%). Cooldown OK ({hours_since_last:.1f}h). Iniciando SAILING.")
                        execute_battery_cmd("discharge", sailing_floor)
                        state["mode"] = "sailing"
                        state["last_charge_time"] = now # Marca o momento que completou a carga
                        save_state(state)
                    else:
                        # Cooldown ativo -> Apenas mantém a carga (Trickle prevention via Maintain)
                        # Nota: O 'maintain' do battery CLI segura a carga onde está.
                        # Isso evita descarregar, mas também evita empurrar corrente excessiva.
                        # É um "Hold Mode".
                        
                        # Para não spammar o log/comando a cada 45s, só executamos se mudou algo
                        # Mas como 'maintain' é seguro, reforçamos o limite.
                        # log(f"⏳ Teto atingido, mas em Cooldown ({hours_since_last:.1f}h / {SAILING_COOLDOWN_HOURS}h). Mantendo carga.")
                        execute_battery_cmd("maintain", target_limit)
                        # Não mudamos para 'sailing', continuamos 'charging' logicamente até o tempo passar
                        # Ou criamos um estado 'holding' se preferir visualização.
                        
                        # Atualiza timestamp para garantir que o cooldown conte a partir do momento que ficou cheio
                        state["last_charge_time"] = now 
                        save_state(state)

            # >> MODO: SAILING
            elif current_mode == "sailing":
                if level <= sailing_floor:
                    log(f"⚡️ Piso atingido ({level}%). Iniciando RECARGA.")
                    execute_battery_cmd("limit", target_limit)
                    state["mode"] = "charging"
                    save_state(state)

        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    try: main()
    except KeyboardInterrupt: pass

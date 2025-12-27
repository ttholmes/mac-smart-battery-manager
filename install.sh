#!/bin/bash

# ==============================================================================
# Smart Battery Manager - Script de Instalação Automatizada
# ==============================================================================

# Cores para output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Caminhos
INSTALL_DIR="$HOME/scripts"
SCRIPT_NAME="battery_manager.py"
PLIST_NAME="com.user.batterymanager.plist"
PLIST_DEST="$HOME/Library/LaunchAgents/$PLIST_NAME"
SRC_SCRIPT="src/$SCRIPT_NAME"
SRC_PLIST="$PLIST_NAME"

echo -e "${GREEN}🔋 Iniciando instalação do Smart Battery Manager...${NC}"

# 1. Verificar dependências (Python3 e Battery CLI)
echo -e "\n${YELLOW}>>> Verificando pré-requisitos...${NC}"

if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 não encontrado. Instale-o primeiro.${NC}"
    exit 1
fi

# Verifica se o 'battery' está no path ou em locais comuns
if ! command -v battery &> /dev/null && [ ! -f "/opt/homebrew/bin/battery" ] && [ ! -f "/usr/local/bin/battery" ]; then
    echo -e "${RED}❌ CLI 'battery' não encontrada.${NC}"
    echo "   Por favor, instale rodando: brew install battery"
    exit 1
else
    echo -e "${GREEN}✅ Pré-requisitos encontrados.${NC}"
fi

# 2. Criar diretório de instalação
echo -e "\n${YELLOW}>>> Preparando diretórios...${NC}"
if [ ! -d "$INSTALL_DIR" ]; then
    mkdir -p "$INSTALL_DIR"
    echo "   Criado diretório: $INSTALL_DIR"
fi

# 3. Copiar Script Python
echo -e "\n${YELLOW}>>> Instalando script Python...${NC}"
if [ -f "$SRC_SCRIPT" ]; then
    cp "$SRC_SCRIPT" "$INSTALL_DIR/$SCRIPT_NAME"
    chmod +x "$INSTALL_DIR/$SCRIPT_NAME"
    echo -e "${GREEN}✅ Script instalado em: $INSTALL_DIR/$SCRIPT_NAME${NC}"
else
    echo -e "${RED}❌ Erro: Arquivo $SRC_SCRIPT não encontrado na pasta atual.${NC}"
    echo "   Certifique-se de rodar este script da raiz do repositório."
    exit 1
fi

# 4. Configurar e Instalar Plist (Daemon)
echo -e "\n${YELLOW}>>> Configurando serviço de background...${NC}"

if [ -f "$SRC_PLIST" ]; then
    # Ajusta o caminho do script dentro do plist dinamicamente
    # Substitui "/Users/SEU_USUARIO/..." pelo caminho real do usuário atual
    sed "s|/Users/SEU_USUARIO/scripts|$INSTALL_DIR|g" "$SRC_PLIST" > "/tmp/$PLIST_NAME"
    
    # Move para LaunchAgents
    mv "/tmp/$PLIST_NAME" "$PLIST_DEST"
    
    # Recarrega o serviço
    if launchctl list | grep -q "com.user.batterymanager"; then
        launchctl unload "$PLIST_DEST"
    fi
    launchctl load "$PLIST_DEST"
    
    echo -e "${GREEN}✅ Serviço configurado e iniciado!${NC}"
else
    echo -e "${RED}❌ Erro: Arquivo $SRC_PLIST não encontrado.${NC}"
    exit 1
fi

# 5. Finalização
echo -e "\n${GREEN}==============================================${NC}"
echo -e "${GREEN}🎉 Instalação Concluída com Sucesso!${NC}"
echo -e "O Smart Battery Manager está rodando em background."
echo -e "Para ver logs, use: tail -f /tmp/smart_battery.log"
echo -e "${GREEN}==============================================${NC}"

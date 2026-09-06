import os
import sys
from pathlib import Path
from src.config import PipelineConfig, save_config
from src.preflight import check_preflight

def clear_screen():
    os.system("cls" if sys.platform == "win32" else "clear")

def print_banner():
    print("=" * 70)
    print("      📸 FOTOS BACKUP WORKFLOW - RESILIENT MEDIA PIPELINE 🚀")
    print("   Perda Zero | Astrofotografia | Timelapses | Google Fotos | Pássaros")
    print("=" * 70)

def display_menu(config: PipelineConfig) -> str:
    print_banner()
    
    # Quick health summary
    pf = check_preflight(config.destination_root)
    status_exif = "✅ OK" if pf.exiftool_ok else "❌ Ausente"
    status_ff = "✅ OK" if pf.ffprobe_ok else "❌ Ausente"
    drives_str = ", ".join(pf.removable_drives) if pf.removable_drives else "Nenhum detectado"

    print(f"[STATUS] Exiftool: {status_exif} | FFprobe: {status_ff} | Espaço Livre: {pf.free_disk_space_gb} GB")
    print(f"[DRIVES] Cartões Removíveis: {drives_str}")
    print(f"[DESTINO] {config.destination_root}")
    print("-" * 70)
    print(" 1. 📥 Ingerir e Organizar Fotos/Vídeos (Cartão SD ou Pasta)")
    print(" 2. ☁️  Upload para o Google Fotos (Fotos da Biblioteca)")
    print(" 3. ⏱️  Compilar Timelapse da GoPro (Chamar script existente)")
    print(" 4. 📋 Visualizar Último Relatório de Auditoria")
    print(" 5. ⚙️  Ajustar Configurações (Caminhos, Notificações, Timer)")
    print(" 0. 🚪 Sair")
    print("-" * 70)
    
    choice = input("Selecione uma opção [0-5]: ").strip()
    return choice

def settings_menu(config: PipelineConfig):
    while True:
        clear_screen()
        print_banner()
        print("⚙️  CONFIGURAÇÕES DO WORKFLOW:")
        print(f" 1. Pasta Raiz de Destino: {config.destination_root}")
        print(f" 2. Intervalo de Rajada (segundos): {config.burst_interval_seconds}s")
        print(f" 3. Zoom Mínimo para Astrofotografia Lua: {config.moon_zoom_threshold_mm}mm")
        print(f" 4. Tempo do Timer Countdown: {config.countdown_seconds}s")
        print(f" 5. Notificações Windows Toast: {'Ativado' if config.notifications.toast_enabled else 'Desativado'}")
        print(f" 6. Notificações ntfy.sh (Tópico): {config.notifications.ntfy_topic}")
        print(f" 7. Script Timelapse GoPro: {config.gopro_script_path or 'Não configurado'}")
        print(" 0. Voltar ao menu principal")
        print("-" * 70)

        op = input("Selecione para alterar [0-7]: ").strip()
        if op == "0" or not op:
            break
        elif op == "1":
            val = input(f"Novo caminho de destino [{config.destination_root}]: ").strip()
            if val:
                config.destination_root = val
                save_config(config)
        elif op == "2":
            val = input(f"Novo intervalo de rajada em segundos [{config.burst_interval_seconds}]: ").strip()
            if val:
                try:
                    config.burst_interval_seconds = float(val)
                    save_config(config)
                except ValueError:
                    pass
        elif op == "3":
            val = input(f"Novo zoom mín para Astro Lua [{config.moon_zoom_threshold_mm}]: ").strip()
            if val:
                try:
                    config.moon_zoom_threshold_mm = float(val)
                    save_config(config)
                except ValueError:
                    pass
        elif op == "4":
            val = input(f"Novo timeout do countdown [{config.countdown_seconds}]: ").strip()
            if val:
                try:
                    config.countdown_seconds = int(val)
                    save_config(config)
                except ValueError:
                    pass
        elif op == "5":
            config.notifications.toast_enabled = not config.notifications.toast_enabled
            save_config(config)
        elif op == "6":
            val = input(f"Novo tópico ntfy.sh [{config.notifications.ntfy_topic}]: ").strip()
            if val:
                config.notifications.ntfy_topic = val
                save_config(config)
        elif op == "7":
            val = input(f"Caminho do script de timelapse GoPro [{config.gopro_script_path}]: ").strip()
            if val:
                config.gopro_script_path = val
                save_config(config)

import os
import sys
from pathlib import Path
from src.config import PipelineConfig, save_config
from src.preflight import check_preflight
from src.project import Project, list_projects, load_project, create_project

STAGE_NAMES = {
    0: "Novo Projeto (Não iniciado)",
    1: "Etapa 1 Concluída (Ingestão SSD)",
    2: "Etapa 2 Concluída (Plano Criado)",
    3: "Etapa 3 Concluída (Organização Física)",
    4: "Etapa 4 Concluída (Upload Web Confirmado)",
    5: "Etapa 5 Concluída (Movido para UPLOADED)",
    6: "Etapa 6 Concluída (Timelapses Renderizados)",
    7: "Etapa 7 Concluída (Limpeza Efetuada)",
}

def clear_screen():
    os.system("cls" if sys.platform == "win32" else "clear")

def print_banner(project: Project | None = None):
    print("=" * 74)
    print("        📸 FOTOS BACKUP WORKFLOW - PIPELINE EM 7 ETAPAS 🚀")
    if project:
        stage_desc = STAGE_NAMES.get(project.current_stage, f"Etapa {project.current_stage}")
        print(f"   Projeto Ativo: [{project.project_id}] | Status: [{stage_desc}]")
    else:
        print("   Nenhum projeto ativo selecionado.")
    print("=" * 74)

def display_menu(config: PipelineConfig, project: Project | None = None) -> str:
    print_banner(project)

    pf = check_preflight(config.destination_root)
    status_exif = "✅ OK" if pf.exiftool_ok else "❌ Ausente"
    status_ff = "✅ OK" if pf.ffprobe_ok else "❌ Ausente"
    drives_str = ", ".join(pf.removable_drives) if pf.removable_drives else "Nenhum detectado"

    print(f"[STATUS] Exiftool: {status_exif} | FFprobe: {status_ff} | Espaço Livre: {pf.free_disk_space_gb} GB")
    print(f"[DRIVES] Cartões Removíveis: {drives_str}")
    print(f"[DESTINO] {config.destination_root}")
    print("-" * 74)
    print(" [ENTER] 🚀 EXECUTAR TUDO (Sequencial 1 a 7 com pausas de 180s e alertas)")
    print("-" * 74)
    print("  1. 📥 Etapa 1: Ingestão SD -> SSD (Verificação SHA-256 e limpeza do SD)")
    print("  2. 📝 Etapa 2: Scan dos arquivos e criação do plano (project_plan.json)")
    print("  3. 🏷️  Etapa 3: Executar renomeação e organização física")
    print("  4. ☁️  Etapa 4: Confirmação de Upload Web (Google Fotos - Storage Saver)")
    print("  5. 📦 Etapa 5: Mover fotos enviadas para pasta UPLOADED")
    print("  6. ⏱️  Etapa 6: Renderizar Timelapses (timelapse_studio.py)")
    print("  7. 🧹 Etapa 7: Limpeza de fotos enviadas no SSD (Baseado no log)")
    print("-" * 74)
    print("  P. 📂 Selecionar / Criar Projeto")
    print("  C. ⚙️  Configurações (Caminhos, Notificações, Timer)")
    print("  0. 🚪 Sair")
    print("-" * 74)

    choice = input("Selecione uma opção [ENTER ou 1-7, P, C, 0]: ").strip()
    return choice

def project_selection_menu(current_project: Project | None) -> Project | None:
    clear_screen()
    print("📂 GERENCIAMENTO DE PROJETOS / SESSÕES\n")
    projs = list_projects()

    if projs:
        print("Projetos Existentes:")
        for idx, p_name in enumerate(projs, start=1):
            p = load_project(p_name)
            stage_str = STAGE_NAMES.get(p.current_stage if p else 0, "Desconhecido")
            active_marker = " (ATIVO)" if current_project and current_project.project_id == p_name else ""
            print(f"  {idx}. {p_name} - {stage_str}{active_marker}")
        print()

    print("  N. ➕ Criar Novo Projeto")
    print("  0. ↩️  Voltar ao menu principal")
    print("-" * 70)

    choice = input("Opção: ").strip()
    if choice == "0" or not choice:
        return current_project

    if choice.upper() == "N":
        name = input("Nome/ID do novo projeto (ex: 2026-09-06_sessao_01): ").strip()
        if not name:
            from datetime import datetime
            name = datetime.now().strftime("%Y-%m-%d_sessao_%H%M%S")

        src = input("Pasta de origem (ex: E:\\DCIM ou C:\\Fotos_Inbox): ").strip()
        if not src:
            src = "E:\\DCIM"

        proj = create_project(name, src)
        print(f"\n✅ Projeto '{name}' criado e ativado!")
        input("Pressione ENTER para continuar...")
        return proj

    try:
        idx = int(choice)
        if 1 <= idx <= len(projs):
            selected_name = projs[idx - 1]
            proj = load_project(selected_name)
            print(f"\n✅ Projeto '{selected_name}' selecionado!")
            input("Pressione ENTER para continuar...")
            return proj
    except ValueError:
        pass

    return current_project

def settings_menu(config: PipelineConfig):
    while True:
        clear_screen()
        print("⚙️  CONFIGURAÇÕES DO WORKFLOW:")
        print(f" 1. Pasta Raiz de Destino: {config.destination_root}")
        print(f" 2. Pasta de Staging: {config.staging_dir}")
        print(f" 3. Pasta UPLOADED: {config.uploaded_dir}")
        print(f" 4. Script Timelapse Studio: {config.timelapse_studio_path}")
        print(f" 5. Intervalo de Rajada: {config.burst_interval_seconds}s")
        print(f" 6. Tempo do Timer Countdown: {config.countdown_seconds}s")
        print(f" 7. Notificações Windows Toast: {'Ativado' if config.notifications.toast_enabled else 'Desativado'}")
        print(f" 8. Notificações ntfy.sh (Tópico): {config.notifications.ntfy_topic}")
        print(" 0. Voltar")
        print("-" * 70)

        op = input("Selecione para alterar [0-8]: ").strip()
        if op == "0" or not op:
            break
        elif op == "1":
            val = input(f"Novo caminho de destino [{config.destination_root}]: ").strip()
            if val:
                config.destination_root = val
                save_config(config)
        elif op == "2":
            val = input(f"Novo staging [{config.staging_dir}]: ").strip()
            if val:
                config.staging_dir = val
                save_config(config)
        elif op == "3":
            val = input(f"Novo uploaded [{config.uploaded_dir}]: ").strip()
            if val:
                config.uploaded_dir = val
                save_config(config)
        elif op == "4":
            val = input(f"Caminho timelapse_studio.py [{config.timelapse_studio_path}]: ").strip()
            if val:
                config.timelapse_studio_path = val
                save_config(config)
        elif op == "5":
            val = input(f"Novo intervalo de rajada [{config.burst_interval_seconds}]: ").strip()
            if val:
                try:
                    config.burst_interval_seconds = float(val)
                    save_config(config)
                except ValueError:
                    pass
        elif op == "6":
            val = input(f"Novo timer [{config.countdown_seconds}]: ").strip()
            if val:
                try:
                    config.countdown_seconds = int(val)
                    save_config(config)
                except ValueError:
                    pass
        elif op == "7":
            config.notifications.toast_enabled = not config.notifications.toast_enabled
            save_config(config)
        elif op == "8":
            val = input(f"Novo tópico ntfy.sh [{config.notifications.ntfy_topic}]: ").strip()
            if val:
                config.notifications.ntfy_topic = val
                save_config(config)

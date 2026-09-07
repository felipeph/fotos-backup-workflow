import os
import sys

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

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
        upload_info = ""
        if project.upload_status == "pendente_timeout":
            upload_info = " | Upload: [Pendente (Timeout 180s)]"
        elif project.upload_status == "pendente_usuario":
            upload_info = " | Upload: [Pendente (Recusado)]"
        elif project.upload_status == "concluido":
            upload_info = " | Upload: [Concluído]"
        print(f"   Projeto Ativo: [{project.project_id}] | Status: [{stage_desc}]{upload_info}")
    else:
        print("   Nenhum projeto ativo selecionado.")
    print("=" * 74)

def display_menu(config: PipelineConfig, project: Project | None = None) -> str:
    print_banner(project)

    source_to_check = project.source_path if (project and project.source_path) else None
    pf = check_preflight(config.destination_root, source_path=source_to_check)
    status_exif = "✅ OK" if pf.exiftool_ok else "❌ Ausente"
    status_ff = "✅ OK" if pf.ffprobe_ok else "❌ Ausente"
    drives_str = ", ".join(pf.removable_drives) if pf.removable_drives else "Nenhum detectado"

    print("[STATUS DO AMBIENTE]")
    print(f"  • Exiftool:           {status_exif}")
    print(f"  • FFprobe:            {status_ff}")
    print(f"  • Espaço Livre SSD:   {pf.free_disk_space_gb} GB")
    if source_to_check:
        status_space = "✅ Suficiente" if pf.has_enough_space else "❌ Insuficiente"
        print(f"  • Origem Ativa:       {source_to_check}")
        print(f"  • Mídias Filtradas:   {pf.source_media_count} fotos/vídeos ({pf.source_media_size_gb} GB)")
        print(f"  • Status de Espaço:   {status_space}")
    print(f"  • Cartões Removíveis: {drives_str}")
    print(f"  • Raiz de Destino:    {config.destination_root}")
    print("-" * 74)
    print(" [ENTER] 🚀 EXECUTAR TUDO (Sequencial 1 a 7 com pausas de 180s e alertas)")
    print("-" * 74)
    print("  1. 📥 Etapa 1: Ingestão SD -> SSD (Verificação SHA-256 e limpeza do SD)")
    print("  2. 📝 Etapa 2: Scan dos arquivos e criação do plano (project_plan.json)")
    print("  3. 🏷️  Etapa 3: Executar renomeação e organização física")
    print("  4. ☁️  Etapa 4: Confirmação de Upload Web (Google Fotos - Storage Saver)")
    print("  5. 📦 Etapa 5: Mover arquivos enviados para pasta UPLOADED")
    print("  6. ⏱️  Etapa 6: Renderizar Timelapses (timelapse_studio.py)")
    print("  7. 🧹 Etapa 7: Limpeza de arquivos enviados no SSD (Baseado no log)")
    print("-" * 74)
    print("  P. 📂 Selecionar / Criar Projeto")
    print("  C. ⚙️  Configurações (Caminhos, Notificações, Timer)")
    print("  0. 🚪 Sair")
    print("-" * 74)

    choice = input("Selecione uma opção [ENTER ou 1-7, P, C, 0]: ").strip()
    return choice

def prompt_create_new_project(config: PipelineConfig | None = None) -> Project:
    print("\n➕ CRIAR NOVO PROJETO")
    from datetime import datetime
    default_name = datetime.now().strftime("%Y-%m-%d_sessao_%H%M%S")
    name = input(f"Nome/ID do novo projeto [ENTER para '{default_name}']: ").strip()
    if not name:
        name = default_name

    # Sugestão inteligente de pasta de origem (detecta cartões removíveis se houver)
    default_src = "E:\\DCIM"
    try:
        from src.preflight import find_removable_drives
        drives = find_removable_drives()
        if drives:
            dcim = Path(drives[0]) / "DCIM"
            default_src = str(dcim) if dcim.exists() else drives[0]
    except Exception:
        pass

    src = input(f"Pasta de origem [ENTER para '{default_src}']: ").strip()
    if not src:
        src = default_src

    proj = create_project(name, src)
    print(f"\n✅ Projeto '{name}' criado e ativado!")
    input("Pressione ENTER para continuar...")
    return proj

def initial_project_prompt(config: PipelineConfig) -> Project | None:
    """
    Pergunta logo no início se deseja retomar o último projeto ou criar um novo.
    Retorna o Project ativo ou None caso o usuário deseje sair.
    """
    projs = list_projects()
    if not projs:
        clear_screen()
        print("=" * 74)
        print("        📸 FOTOS BACKUP WORKFLOW - PIPELINE EM 7 ETAPAS 🚀")
        print("=" * 74)
        print("📂 Nenhum projeto anterior encontrado.")
        print("➕ Vamos criar o seu primeiro projeto:\n")
        return prompt_create_new_project(config)

    latest_id = projs[0]
    latest_proj = load_project(latest_id)
    if not latest_proj:
        return prompt_create_new_project(config)

    stage_desc = STAGE_NAMES.get(latest_proj.current_stage, f"Etapa {latest_proj.current_stage}")
    n_items = len(latest_proj.items)

    clear_screen()
    print("=" * 74)
    print("        📸 FOTOS BACKUP WORKFLOW - PIPELINE EM 7 ETAPAS 🚀")
    print("=" * 74)
    print(f"📂 Último projeto encontrado: [{latest_proj.project_id}]")
    print(f"   • Status:  {stage_desc}")
    print(f"   • Mídias:  {n_items} arquivos registrados")
    if latest_proj.source_path:
        print(f"   • Origem:  {latest_proj.source_path}")
    print("-" * 74)
    print(" Como deseja começar?")
    print("-" * 74)
    print(f"  [ENTER] ou 1. 🔄 Retomar último projeto ({latest_proj.project_id})")
    print("          2. ➕ Criar um NOVO projeto")
    print("          3. 📂 Selecionar outro projeto da lista")
    print("          0. 🚪 Sair")
    print("-" * 74)

    while True:
        try:
            choice = input("Selecione uma opção [ENTER/1, 2, 3, 0]: ").strip().upper()
        except KeyboardInterrupt:
            return None

        if choice in ("", "1", "R"):
            return latest_proj
        elif choice in ("2", "N"):
            return prompt_create_new_project(config)
        elif choice in ("3", "P"):
            selected = project_selection_menu(latest_proj, config=config)
            return selected if selected else latest_proj
        elif choice == "0":
            return None
        print("Opção inválida. Digite ENTER, 1, 2, 3 ou 0.")

def project_selection_menu(current_project: Project | None, config: PipelineConfig | None = None) -> Project | None:
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
        return prompt_create_new_project(config)

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
        burst_desc = f"Ativado ({config.burst_interval_seconds}s)" if config.enable_burst_detection else "Desativado (Apenas por dia)"
        print(f" 5. Detecção de Rajadas: {burst_desc}")
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
            current_st = "Ativado" if config.enable_burst_detection else "Desativado (Apenas por dia)"
            print(f"\nStatus atual da detecção de rajadas: {current_st}")
            ans = input("Deseja alternar ativação das rajadas? [S/N]: ").strip().lower()
            if ans in ("s", "sim", "y", "yes"):
                config.enable_burst_detection = not config.enable_burst_detection
                if config.enable_burst_detection:
                    val = input(f"Intervalo de rajada em segundos [{config.burst_interval_seconds}]: ").strip()
                    if val:
                        try:
                            config.burst_interval_seconds = float(val)
                        except ValueError:
                            pass
                save_config(config)
                print(f"Configuração salva: {'Ativado' if config.enable_burst_detection else 'Desativado'}")
                input("Pressione ENTER para continuar...")
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

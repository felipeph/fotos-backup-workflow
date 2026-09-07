import argparse
import sys
import os
from pathlib import Path
from datetime import datetime

if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from src.config import load_config, PipelineConfig
from src.project import Project, list_projects, load_project, create_project
from src.preflight import check_preflight, find_removable_drives
from src.notifier import notify_event, countdown_prompt
from src.stages import (
    run_stage1,
    run_stage2,
    run_stage3,
    run_stage4,
    run_stage5,
    run_stage6,
    run_stage7,
)
from src.tui import display_menu, settings_menu, project_selection_menu, clear_screen, print_banner

from rich.table import Table
from src.telemetry import console

STAGE_FUNCTIONS = {
    1: ("Etapa 1 (Ingestão SD -> SSD)", run_stage1),
    2: ("Etapa 2 (Criação do Plano JSON)", run_stage2),
    3: ("Etapa 3 (Organização Física)", run_stage3),
    4: ("Etapa 4 (Confirmação Upload Web)", run_stage4),
    5: ("Etapa 5 (Mover para UPLOADED)", run_stage5),
    6: ("Etapa 6 (Timelapse Studio)", run_stage6),
    7: ("Etapa 7 (Limpeza SSD)", run_stage7),
}

def execute_stage(stage_num: int, project: Project, config: PipelineConfig, **kwargs) -> bool:
    name, fn = STAGE_FUNCTIONS[stage_num]

    try:
        if stage_num == 1:
            success = fn(project, config, auto_delete_sd=kwargs.get("auto_delete_sd", False))
        elif stage_num == 4:
            success = fn(project, config, auto_confirm=kwargs.get("auto_confirm_upload", False))
        elif stage_num == 7:
            success = fn(project, config, auto_confirm=kwargs.get("auto_confirm_cleanup", False))
        else:
            success = fn(project, config)
    except KeyboardInterrupt:
        console.print(f"\n[bold yellow]🛑 Execução interrompida pelo usuário (Ctrl+C).[/bold yellow]")
        console.print(f"💾 Checkpoint salvo no projeto '[bold cyan]{project.project_id}[/bold cyan]'.")
        console.print("ℹ️ O progresso foi preservado. Você pode retomar a qualquer momento!\n")
        project.save()
        return False

    if success:
        notify_event(
            title=f"Fotos Backup - {name}",
            message=f"Concluída com sucesso no projeto '{project.project_id}'!",
            config=config.notifications
        )
    else:
        console.print(f"\n[yellow]⚠️  {name} encerrou com avisos ou pendências.[/yellow]")

    return success

def run_all_stages(project: Project, config: PipelineConfig, auto_confirm: bool = False):
    console.print(f"\n🚀 [bold green][EXECUTAR TUDO][/bold green] Iniciando pipeline sequencial para '[bold cyan]{project.project_id}[/bold cyan]'...")
    start_global = datetime.now()
    stage_results = []

    for st in range(1, 8):
        name, _ = STAGE_FUNCTIONS[st]
        if project.current_stage >= st:
            console.print(f"[dim]ℹ️  Etapa {st} já concluída anteriormente neste projeto. Pulando...[/dim]")
            stage_results.append((st, name, "Pulada (Já Concluída)", "--"))
            continue

        st_start = datetime.now()
        try:
            ok = execute_stage(
                st,
                project,
                config,
                auto_delete_sd=auto_confirm,
                auto_confirm_upload=auto_confirm,
                auto_confirm_cleanup=auto_confirm,
            )
        except KeyboardInterrupt:
            console.print(f"\n[bold yellow]🛑 Pipeline sequencial interrompido pelo usuário (Ctrl+C).[/bold yellow]")
            stage_results.append((st, name, "Interrompida", str(datetime.now() - st_start).split(".")[0]))
            break

        dur = str(datetime.now() - st_start).split(".")[0]
        status_label = "Concluída" if ok else "Pendente/Aviso"
        stage_results.append((st, name, status_label, dur))

        if not ok and st in (1, 2, 3, 4):
            console.print(f"\n[bold red]🛑 Interrompendo sequência pois a {name} não foi concluída.[/bold red]")
            break

        # Countdown pause of 180s between stages (except after final stage 7)
        if st < 7:
            next_name, _ = STAGE_FUNCTIONS[st + 1]
            act = countdown_prompt(f"Avançar para {next_name}", timeout_seconds=config.countdown_seconds)
            if act == "cancel":
                console.print("\n[yellow]🛑 Sequência interrompida pelo usuário no countdown.[/yellow]")
                break

    total_dur = str(datetime.now() - start_global).split(".")[0]
    table = Table(title=f"Resumo da Execução - Projeto {project.project_id}", border_style="bright_blue")
    table.add_column("Etapa", style="bold")
    table.add_column("Nome", style="white")
    table.add_column("Status", style="cyan")
    table.add_column("Duração", justify="right", style="green")

    for st_num, sname, sstat, sdur in stage_results:
        table.add_row(str(st_num), sname, sstat, sdur)

    console.print("\n")
    console.print(table)
    console.print(f"⏱️  Tempo total de execução: [bold]{total_dur}[/bold]\n")

def interactive_loop():
    config = load_config()

    # Auto-load latest project if available
    projs = list_projects()
    active_project: Project | None = load_project(projs[0]) if projs else None

    while True:
        try:
            clear_screen()
            choice = display_menu(config, active_project)

            if choice == "0":
                console.print("\n👋 [bold green]Encerrando. Até logo![/bold green]\n")
                break

            elif choice.upper() == "P":
                active_project = project_selection_menu(active_project)

            elif choice.upper() == "C":
                settings_menu(config)

            elif choice == "" or choice.upper() == "A":
                # ENTER or A: RUN ALL
                if not active_project:
                    active_project = project_selection_menu(active_project)
                    if not active_project:
                        continue
                clear_screen()
                run_all_stages(active_project, config)
                input("\nPressione ENTER para voltar ao menu...")

            elif choice in [str(i) for i in range(1, 8)]:
                st = int(choice)
                if not active_project:
                    console.print("\n[yellow]ℹ️  Nenhum projeto selecionado. Crie ou selecione um projeto primeiro.[/yellow]")
                    active_project = project_selection_menu(active_project)
                    if not active_project:
                        continue

                clear_screen()
                execute_stage(st, active_project, config)
                input("\nPressione ENTER para voltar ao menu...")
        except KeyboardInterrupt:
            console.print("\n\n👋 [bold green]Encerrando. Até logo![/bold green]\n")
            break

def main():
    parser = argparse.ArgumentParser(description="Fotos Backup Workflow - Pipeline em 7 Etapas por Projeto")
    subparsers = parser.add_subparsers(dest="command", help="Comandos disponíveis")

    # Command: run-all
    all_p = subparsers.add_parser("run-all", help="Executa as 7 etapas sequencialmente")
    all_p.add_argument("--project", "-p", help="Nome do projeto (cria novo se não existir)")
    all_p.add_argument("--source", "-s", help="Pasta de origem dos arquivos brutos")
    all_p.add_argument("--yes", "-y", action="store_true", help="Confirma automaticamente remoções do SD e SSD")

    # Command: stage
    st_p = subparsers.add_parser("stage", help="Executa uma etapa específica (1 a 7)")
    st_p.add_argument("number", type=int, choices=range(1, 8), help="Número da etapa (1 a 7)")
    st_p.add_argument("--project", "-p", required=True, help="Nome do projeto")
    st_p.add_argument("--source", "-s", help="Pasta de origem (necessária na etapa 1)")

    # Command: preflight
    subparsers.add_parser("preflight", help="Verifica integridade do ambiente e ferramentas")

    args = parser.parse_args()
    config = load_config()

    if not args.command:
        interactive_loop()
    elif args.command == "preflight":
        pf = check_preflight(config.destination_root)
        print(f"Python: {pf.python_version} ({'OK' if pf.python_ok else 'Desatualizado'})")
        print(f"Exiftool: {pf.exiftool_path}")
        print(f"FFprobe: {pf.ffprobe_path}")
        print(f"Destino Gravável: {pf.destination_writable} ({pf.free_disk_space_gb} GB livres)")
        print(f"Cartões Detectados: {pf.removable_drives}")
    elif args.command == "stage":
        proj = load_project(args.project)
        if not proj:
            if not args.source:
                print(f"[ERRO] Projeto '{args.project}' não existe. Forneça --source para criá-lo.")
                return
            proj = create_project(args.project, args.source)
        execute_stage(args.number, proj, config)
    elif args.command == "run-all":
        p_name = args.project or datetime.now().strftime("%Y-%m-%d_sessao_%H%M%S")
        proj = load_project(p_name)
        if not proj:
            src = args.source or "E:\\DCIM"
            proj = create_project(p_name, src)
        run_all_stages(proj, config, auto_confirm=args.yes)

if __name__ == "__main__":
    main()

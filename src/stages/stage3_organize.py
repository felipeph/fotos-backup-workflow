import sys
import shutil
from pathlib import Path
from datetime import datetime

from src.project import Project
from src.config import PipelineConfig
from src.storage import safe_copy_file, compute_sha256
from src.telemetry import create_item_progress, print_stage_header, print_stage_summary, console

def run_stage3(project: Project, config: PipelineConfig) -> bool:
    """
    Etapa 3: Execução da renomeação e organização de todos os arquivos,
    seguindo as especificações registradas no project_plan.json.
    """
    if project.current_stage < 2 or not project.items:
        console.print("[red][ERRO] Plano não encontrado ou não gerado. Execute a Etapa 2 primeiro.[/red]")
        return False

    log_dir = Path("logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"{project.project_id}_stage3_organize.log"

    dest_root = config.destination_path
    total = len(project.items)
    
    total_bytes = sum(it.file_size_bytes for it in project.items)
    print_stage_header("ETAPA 3: RENOMEAÇÃO E ORGANIZAÇÃO FÍSICA", total_items=total, total_bytes=total_bytes)
    start_time = datetime.now()

    success_count = 0
    with open(log_file, "a", encoding="utf-8") as log:
        log.write(f"=== INÍCIO ETAPA 3 (ORGANIZAÇÃO): {datetime.now().isoformat()} ===\n\n")

        with create_item_progress(unit="arqs/s") as progress:
            task_id = progress.add_task("[bold blue]Organização no SSD", total=total)

            for idx, it in enumerate(project.items, start=1):
                cur_fname = it.target_filename or Path(it.staging_path).name
                progress.update(task_id, filename=cur_fname)

                # Check if already organized in a previous run (Resume)
                if it.organized_path and Path(it.organized_path).exists():
                    success_count += 1
                    progress.update(task_id, advance=1)
                    log.write(f"[{idx}/{total}] RESUME-OK | {it.organized_path}\n")
                    continue

                src_p = Path(it.staging_path)
                if not src_p.exists():
                    log.write(f"[ERRO] Arquivo de staging não encontrado: {src_p}\n")
                    progress.update(task_id, advance=1)
                    continue

                target_dir = dest_root / it.relative_dest_dir
                res = safe_copy_file(src_p, target_dir, it.target_filename)

                if res.status in ("copied", "skipped_duplicate"):
                    it.organized_path = str(res.target_path.resolve())
                    success_count += 1
                    log.write(f"[{idx}/{total}] OK | {res.status} | {res.target_path}\n")

                    # Remove staging raw file now that it is safely in final organized destination
                    src_p.unlink(missing_ok=True)
                else:
                    log.write(f"[{idx}/{total}] ERRO | {res.error_message} | {src_p}\n")
                    console.print(f"\n[red]❌ Erro ao organizar {src_p.name}: {res.error_message}[/red]")

                progress.update(task_id, advance=1)

                # Incremental checkpointing every 25 files
                if idx % 25 == 0:
                    project.save()

    if success_count == total:
        project.current_stage = max(project.current_stage, 3)
    project.save()

    print_stage_summary(
        "Etapa 3 (Organização Física)",
        start_time,
        success=(success_count == total),
        items_done=success_count,
        bytes_done=total_bytes,
    )
    return success_count == total

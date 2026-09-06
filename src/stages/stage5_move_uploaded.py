import sys
import shutil
from pathlib import Path
from datetime import datetime

from src.project import Project
from src.config import PipelineConfig
from src.storage import safe_copy_file, compute_sha256
from src.telemetry import create_item_progress, print_stage_header, print_stage_summary, console

def run_stage5(project: Project, config: PipelineConfig) -> bool:
    """
    Etapa 5: Transferência dos arquivos cujo upload já ocorreu corretamente
    para a pasta UPLOADED, preservando a estrutura de pastas.
    """
    if project.current_stage < 4 or not project.items:
        console.print("[red][ERRO] Etapa de upload não concluída. Execute a Etapa 4 primeiro.[/red]")
        return False

    uploaded_candidates = [
        it for it in project.items
        if it.uploaded_at and not it.uploaded_path
    ]

    if not uploaded_candidates:
        console.print("\n[yellow]ℹ️  [ETAPA 5] Nenhuma foto pendente de transferência para a pasta UPLOADED.[/yellow]")
        project.current_stage = max(project.current_stage, 5)
        project.save()
        return True

    log_dir = Path("logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"{project.project_id}_stage5_move_uploaded.log"

    dest_uploaded_root = config.uploaded_path
    total = len(uploaded_candidates)
    total_bytes = sum(it.file_size_bytes for it in uploaded_candidates)

    print_stage_header("ETAPA 5: MOVER PARA UPLOADED", total_items=total, total_bytes=total_bytes)
    start_time = datetime.now()

    success_count = 0
    with open(log_file, "a", encoding="utf-8") as log:
        log.write(f"=== INÍCIO ETAPA 5 (MOVER PARA UPLOADED): {datetime.now().isoformat()} ===\n\n")

        with create_item_progress(unit="arqs/s") as progress:
            task_id = progress.add_task("[bold blue]Movendo para UPLOADED", total=total)

            for idx, it in enumerate(uploaded_candidates, start=1):
                # Resume check
                if it.uploaded_path and Path(it.uploaded_path).exists():
                    success_count += 1
                    progress.update(task_id, advance=1)
                    log.write(f"[{idx}/{total}] RESUME-OK | {it.uploaded_path}\n")
                    continue

                cur_p = Path(it.organized_path)
                if not cur_p.exists():
                    log.write(f"[{idx}/{total}] ARQUIVO NÃO ENCONTRADO: {cur_p}\n")
                    progress.update(task_id, advance=1)
                    continue

                target_dir = dest_uploaded_root / it.relative_dest_dir
                res = safe_copy_file(cur_p, target_dir, it.target_filename)

                if res.status in ("copied", "skipped_duplicate"):
                    it.uploaded_path = str(res.target_path.resolve())
                    cur_p.unlink(missing_ok=True)
                    success_count += 1
                    log.write(f"[{idx}/{total}] MOVIDO: {cur_p.name} -> {res.target_path}\n")
                else:
                    log.write(f"[{idx}/{total}] ERRO: {res.error_message} | {cur_p}\n")
                    console.print(f"\n[red]❌ Erro ao mover {cur_p.name}: {res.error_message}[/red]")

                progress.update(task_id, advance=1)

                if idx % 25 == 0:
                    project.save()

    if success_count == total:
        project.current_stage = max(project.current_stage, 5)
    project.save()

    print_stage_summary(
        "Etapa 5 (Mover para UPLOADED)",
        start_time,
        success=(success_count == total),
        items_done=success_count,
        bytes_done=total_bytes,
    )
    return success_count == total

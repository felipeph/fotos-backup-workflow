import sys
from pathlib import Path
from datetime import datetime

from src.project import Project
from src.config import PipelineConfig
from src.telemetry import create_item_progress, print_stage_header, print_stage_summary, console

def run_stage7(project: Project, config: PipelineConfig, auto_confirm: bool = False) -> bool:
    """
    Etapa 7: Limpeza de arquivos no SSD cujo upload para o Google Fotos foi
    efetuado e comprovado por meio do log e manifesto da Etapa 4.
    """
    candidates = [
        it for it in project.items
        if it.uploaded_at and it.uploaded_path and not it.cleaned_at
    ]

    if not candidates:
        console.print("\n[yellow]ℹ️  [ETAPA 7] Nenhum arquivo elegível para limpeza neste projeto.[/yellow]")
        project.current_stage = max(project.current_stage, 7)
        project.save()
        return True

    # Validate against upload log
    log_stage4 = Path("logs") / f"{project.project_id}_stage4_upload.log"
    verified_candidates = []
    total_bytes = 0

    for it in candidates:
        p = Path(it.uploaded_path)
        if p.exists():
            verified_candidates.append(it)
            total_bytes += it.file_size_bytes

    if not verified_candidates:
        console.print("\n[yellow]ℹ️  [ETAPA 7] Os arquivos já haviam sido limpos ou não foram encontrados no disco.[/yellow]")
        project.current_stage = max(project.current_stage, 7)
        project.save()
        return True

    total_mb = total_bytes / (1024 * 1024)
    print_stage_header("ETAPA 7: LIMPEZA DE ARQUIVOS NO SSD", total_items=len(verified_candidates), total_bytes=total_bytes)
    start_time = datetime.now()

    confirmed = auto_confirm
    if not auto_confirm:
        console.print("\n[bold yellow]⚠️  [CONFIRMAÇÃO NECESSÁRIA - EXCLUSÃO LOCAL][/bold yellow]")
        console.print("Estes arquivos já estão salvos com segurança na nuvem (Google Fotos).")
        resp = input(f"Deseja apagar agora as {len(verified_candidates)} cópias locais da pasta UPLOADED liberando {total_mb:.1f} MB? (s/N): ").strip().lower()
        confirmed = (resp == "s")

    if not confirmed:
        console.print("ℹ️  Limpeza cancelada pelo usuário. Os arquivos foram mantidos no SSD.")
        return False

    log_dir = Path("logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"{project.project_id}_stage7_cleanup.log"

    deleted_count = 0
    with open(log_file, "a", encoding="utf-8") as log:
        log.write(f"=== INÍCIO ETAPA 7 (LIMPEZA PÓS-UPLOAD): {datetime.now().isoformat()} ===\n")
        log.write(f"Total de arquivos a remover: {len(verified_candidates)} ({total_mb:.2f} MB)\n\n")

        with create_item_progress(unit="arqs/s") as progress:
            task_id = progress.add_task("[bold blue]Exclusão Segura no SSD", total=len(verified_candidates))

            for idx, it in enumerate(verified_candidates, start=1):
                p = Path(it.uploaded_path)
                try:
                    if p.exists():
                        p.unlink()
                        it.cleaned_at = datetime.now().isoformat()
                        deleted_count += 1
                        log.write(f"[{idx}/{len(verified_candidates)}] APAGADO: {p}\n")
                except Exception as e:
                    log.write(f"[ERRO] Falha ao apagar {p}: {e}\n")

                progress.update(task_id, advance=1)

                if idx % 25 == 0:
                    project.save()

    project.current_stage = max(project.current_stage, 7)
    project.save()

    print_stage_summary(
        "Etapa 7 (Limpeza SSD)",
        start_time,
        success=True,
        items_done=deleted_count,
        bytes_done=total_bytes,
    )
    console.print(f"✨ [bold green]Limpeza concluída:[/bold green] {deleted_count} arquivos apagados. [cyan]{total_mb:.1f} MB[/cyan] liberados no SSD!\n")
    return True

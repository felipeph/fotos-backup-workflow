import os
from pathlib import Path
from datetime import datetime

from src.project import Project
from src.config import PipelineConfig
from src.metadata_extractor import extract_metadata_batch, PHOTO_EXTENSIONS, VIDEO_EXTENSIONS
from src.classifier import classify_media_batch
from src.telemetry import create_item_progress, print_stage_header, print_stage_summary, console
from rich.table import Table

def run_stage2(project: Project, config: PipelineConfig) -> bool:
    """
    Etapa 2: Leitura de todos os arquivos no SSD e criação do plano de renomeação
    e organização em pastas, gravado em project_plan.json e em log detalhado.
    """
    staging_dir = config.staging_path / project.project_id / "raw"
    if not staging_dir.exists():
        console.print(f"[red][ERRO] Pasta de staging não encontrada: {staging_dir}. Execute a Etapa 1 primeiro.[/red]")
        return False

    valid_exts = PHOTO_EXTENSIONS | VIDEO_EXTENSIONS
    files = []
    for root, _, filenames in os.walk(staging_dir):
        for f in filenames:
            if f.startswith("."):
                continue
            p = Path(root) / f
            if p.suffix.lower() in valid_exts:
                files.append(p)

    if not files:
        console.print(f"[yellow][AVISO] Nenhum arquivo para planejar em {staging_dir}.[/yellow]")
        return False

    print_stage_header("ETAPA 2: CRIAÇÃO DO PLANO E CLASSIFICAÇÃO", total_items=len(files))
    start_time = datetime.now()

    with create_item_progress(unit="arqs/s") as progress:
        task_id = progress.add_task("[bold blue]Extração de Metadados", total=len(files))
        def on_progress(done, total):
            progress.update(task_id, completed=done)

        meta_list = extract_metadata_batch(files, progress_callback=on_progress)

    console.print("⚙️  [cyan]Classificando e agrupando mídias (Astro, GoPro, Vídeos, Rajadas, Avulsas)...[/cyan]")
    classified_items = classify_media_batch(meta_list, config)

    # Map of staging path -> ClassifiedItem
    classified_map = {str(c.metadata.file_path.resolve()): c for c in classified_items}

    log_dir = Path("logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"{project.project_id}_stage2_planning.log"

    cat_counts: dict[str, int] = {}
    with open(log_file, "a", encoding="utf-8") as log:
        log.write(f"=== INÍCIO ETAPA 2 (PLANO): {datetime.now().isoformat()} ===\n")
        log.write(f"Total de arquivos analisados: {len(classified_items)}\n\n")

        for it in project.items:
            # Find corresponding classified item
            c_item = classified_map.get(str(Path(it.staging_path).resolve()))
            if c_item:
                it.category = c_item.category
                it.relative_dest_dir = str(c_item.relative_dest_dir)
                it.target_filename = c_item.target_filename
                cat_counts[it.category] = cat_counts.get(it.category, 0) + 1

                log.write(f"[{it.category.upper()}] {Path(it.staging_path).name} -> {it.relative_dest_dir}/{it.target_filename}\n")

    # Display Rich summary table
    table = Table(title="Resumo do Planejamento por Categoria", border_style="cyan")
    table.add_column("Categoria", style="bold white")
    table.add_column("Quantidade", justify="right", style="green")
    table.add_column("Percentual", justify="right", style="yellow")

    total_classified = len(project.items)
    for cat, count in cat_counts.items():
        pct = (count / total_classified * 100) if total_classified > 0 else 0.0
        table.add_row(cat, f"{count:,}", f"{pct:.1f}%")

    console.print(table)

    project.current_stage = max(project.current_stage, 2)
    project.save()

    print_stage_summary("Etapa 2 (Criação do Plano JSON)", start_time, success=True, items_done=len(files))
    console.print(f"✅ Plano registrado com sucesso em: [bold green]{project.plan_file}[/bold green]")
    console.print(f"📋 Log detalhado registrado em:     [dim]{log_file}[/dim]\n")
    return True

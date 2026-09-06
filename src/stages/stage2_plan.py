import os
from pathlib import Path
from datetime import datetime

from src.project import Project
from src.config import PipelineConfig
from src.metadata_extractor import extract_metadata_batch, PHOTO_EXTENSIONS, VIDEO_EXTENSIONS
from src.classifier import classify_media_batch

def run_stage2(project: Project, config: PipelineConfig) -> bool:
    """
    Etapa 2: Leitura de todos os arquivos no SSD e criação do plano de renomeação
    e organização em pastas, gravado em project_plan.json e em log detalhado.
    """
    staging_dir = config.staging_path / project.project_id / "raw"
    if not staging_dir.exists():
        print(f"[ERRO] Pasta de staging não encontrada: {staging_dir}. Execute a Etapa 1 primeiro.")
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
        print(f"[AVISO] Nenhum arquivo para planejar em {staging_dir}.")
        return False

    print(f"\n📝 [ETAPA 2] Extraindo metadados e gerando plano de renomeação para {len(files)} arquivos...")
    meta_list = extract_metadata_batch(files)
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

    print(f"\n📊 Resumo do Planejamento:")
    for cat, count in cat_counts.items():
        print(f"   - {cat}: {count} arquivos")

    project.current_stage = 2
    project.save()

    print(f"\n✅ Plano registrado com sucesso em: {project.plan_file}")
    print(f"📋 Log detalhado registrado em:     {log_file}")
    return True

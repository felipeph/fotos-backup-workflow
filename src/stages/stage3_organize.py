import sys
import shutil
from pathlib import Path
from datetime import datetime

from src.project import Project
from src.config import PipelineConfig
from src.storage import safe_copy_file, compute_sha256

def run_stage3(project: Project, config: PipelineConfig) -> bool:
    """
    Etapa 3: Execução da renomeação e organização de todos os arquivos,
    seguindo as especificações registradas no project_plan.json.
    """
    if project.current_stage < 2 or not project.items:
        print("[ERRO] Plano não encontrado ou não gerado. Execute a Etapa 2 primeiro.")
        return False

    log_dir = Path("logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"{project.project_id}_stage3_organize.log"

    dest_root = config.destination_path
    total = len(project.items)
    print(f"\n🏷️  [ETAPA 3] Executando renomeação e organização física de {total} arquivos...")
    print(f"   Destino Raiz: {dest_root}")
    print(f"   Log:          {log_file}\n")

    success_count = 0
    with open(log_file, "a", encoding="utf-8") as log:
        log.write(f"=== INÍCIO ETAPA 3 (ORGANIZAÇÃO): {datetime.now().isoformat()} ===\n\n")

        for idx, it in enumerate(project.items, start=1):
            src_p = Path(it.staging_path)
            if not src_p.exists():
                # Already moved or missing
                if it.organized_path and Path(it.organized_path).exists():
                    success_count += 1
                    continue
                log.write(f"[ERRO] Arquivo de staging não encontrado: {src_p}\n")
                continue

            target_dir = dest_root / it.relative_dest_dir
            res = safe_copy_file(src_p, target_dir, it.target_filename)

            if res.status in ("copied", "skipped_duplicate"):
                it.organized_path = str(res.target_path.resolve())
                success_count += 1
                log.write(f"[{idx}/{total}] OK | {res.status} | {res.target_path}\n")
                sys.stdout.write(f"\r[{idx}/{total}] ✅ {res.target_path.name[:45]:<45}")
                sys.stdout.flush()

                # Remove staging raw file now that it is safely in final organized destination
                src_p.unlink(missing_ok=True)
            else:
                log.write(f"[{idx}/{total}] ERRO | {res.error_message} | {src_p}\n")
                print(f"\n❌ Erro ao organizar {src_p.name}: {res.error_message}")

    project.current_stage = 3
    project.save()

    print(f"\n\n✨ Organização física concluída: {success_count}/{total} arquivos organizados com sucesso!")
    return success_count == total

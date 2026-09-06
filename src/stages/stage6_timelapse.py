import sys
import os
import subprocess
from pathlib import Path
from datetime import datetime

from src.project import Project
from src.config import PipelineConfig

def run_stage6(project: Project, config: PipelineConfig) -> bool:
    """
    Etapa 6: Detecção dos arquivos de timelapse e integração direta
    com o timelapse_studio.py configurado no config.json.
    """
    tl_items = [it for it in project.items if it.category == "timelapse_gopro"]
    if not tl_items:
        print("\nℹ️  [ETAPA 6] Nenhuma captura de timelapse identificada neste projeto.")
        project.current_stage = max(project.current_stage, 6)
        project.save()
        return True

    # Identify unique timelapse directories
    tl_dirs = set()
    for it in tl_items:
        p = Path(it.organized_path or it.staging_path)
        if p.exists():
            tl_dirs.add(p.parent)

    tl_script = Path(config.timelapse_studio_path)
    if not tl_script.exists():
        print(f"\n⚠️  [ETAPA 6] Script do Timelapse Studio não encontrado em: {tl_script}")
        print("Configure o caminho correto em config.json ('timelapse_studio_path').")
        return False

    log_dir = Path("logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"{project.project_id}_stage6_timelapse.log"

    print(f"\n⏱️  [ETAPA 6] Foram identificadas {len(tl_dirs)} sessões de timelapse:")
    for d in tl_dirs:
        print(f"   📁 {d}")

    with open(log_file, "a", encoding="utf-8") as log:
        log.write(f"=== INÍCIO ETAPA 6 (TIMELAPSE STUDIO): {datetime.now().isoformat()} ===\n")
        log.write(f"Script: {tl_script}\n\n")

        for d in tl_dirs:
            print(f"\n🎬 Processando timelapse: {d.name} ...")
            cmd = [sys.executable, str(tl_script), "-i", str(d), "--run-all"]
            log.write(f"Executando: {' '.join(cmd)}\n")

            try:
                proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    bufsize=1
                )
                for line in proc.stdout:
                    sys.stdout.write(line)
                    sys.stdout.flush()
                    log.write(line)
                proc.wait()
                if proc.returncode == 0:
                    print(f"✅ Timelapse {d.name} renderizado com sucesso!")
                else:
                    print(f"⚠️  Timelapse {d.name} finalizou com código {proc.returncode}.")
            except Exception as e:
                log.write(f"ERRO ao executar timelapse: {e}\n")
                print(f"❌ Erro ao executar timelapse {d.name}: {e}")

    project.current_stage = 6
    project.save()
    return True

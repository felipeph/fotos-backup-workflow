import sys
import os
import subprocess
from pathlib import Path
from datetime import datetime

from src.project import Project
from src.config import PipelineConfig
from src.telemetry import print_stage_header, print_stage_summary, console

def run_stage6(project: Project, config: PipelineConfig) -> bool:
    """
    Etapa 6: Detecção dos arquivos de timelapse e integração direta
    com o timelapse_studio.py configurado no config.json.
    """
    tl_items = [it for it in project.items if it.category == "timelapse_gopro"]
    if not tl_items:
        console.print("\n[yellow]ℹ️  [ETAPA 6] Nenhuma captura de timelapse identificada neste projeto.[/yellow]")
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
        console.print(f"\n[yellow]⚠️  [ETAPA 6] Script do Timelapse Studio não encontrado em: {tl_script}[/yellow]")
        console.print("Configure o caminho correto em config.json ('timelapse_studio_path').")
        return False

    log_dir = Path("logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"{project.project_id}_stage6_timelapse.log"

    print_stage_header("ETAPA 6: TIMELAPSE STUDIO", total_items=len(tl_items))
    start_time = datetime.now()
    console.print(f"⏱️  Foram identificadas [bold]{len(tl_dirs)}[/bold] sessões de timelapse:")
    for d in tl_dirs:
        console.print(f"   📁 [cyan]{d}[/cyan]")

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

    project.current_stage = max(project.current_stage, 6)
    project.save()
    print_stage_summary("Etapa 6 (Timelapse Studio)", start_time, success=True, items_done=len(tl_dirs))
    return True

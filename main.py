import argparse
import sys
import os
import time
from pathlib import Path
from datetime import datetime

from src.config import load_config, PipelineConfig
from src.preflight import check_preflight, find_removable_drives
from src.metadata_extractor import extract_metadata_batch, PHOTO_EXTENSIONS, VIDEO_EXTENSIONS
from src.classifier import classify_media_batch
from src.storage import safe_copy_file
from src.notifier import notify_event, countdown_prompt
from src.google_photos import GooglePhotosManager
from src.reporter import AuditReporter
from src.tui import display_menu, settings_menu, clear_screen, print_banner

def find_media_files(source_dir: Path) -> list[Path]:
    valid_exts = PHOTO_EXTENSIONS | VIDEO_EXTENSIONS
    files = []
    for root, _, filenames in os.walk(source_dir):
        for f in filenames:
            if f.startswith("."):
                continue
            p = Path(root) / f
            if p.suffix.lower() in valid_exts:
                files.append(p)
    return files

def run_organize(source_dir: Path, config: PipelineConfig, is_standalone: bool = True) -> bool:
    print(f"\n🔍 [1/4] Escaneando arquivos em: {source_dir} ...")
    media_files = find_media_files(source_dir)
    if not media_files:
        print(f"[AVISO] Nenhum arquivo de foto ou vídeo encontrado em {source_dir}.")
        return False

    print(f"📦 Total de arquivos de mídia identificados: {len(media_files)}")
    start_time = time.time()

    # Step 2: Metadata
    print(f"\n📊 [2/4] Extraindo metadados EXIF e informações de mídia...")
    metadata_list = extract_metadata_batch(media_files)

    # Step 3: Classification
    print(f"\n🏷️  [3/4] Classificando em categorias e agrupando rajadas/avulsas...")
    classified_items = classify_media_batch(metadata_list, config)

    cat_counts: dict[str, int] = {}
    for item in classified_items:
        cat_counts[item.category] = cat_counts.get(item.category, 0) + 1

    print("\n📋 Resumo da Classificação:")
    for cat, count in cat_counts.items():
        print(f"   - {cat}: {count} arquivos")

    # Step 4: Secure Transfer
    print(f"\n💾 [4/4] Copiando arquivos com verificação SHA-256 para {config.destination_root}...")
    transfer_results = []
    dest_root = config.destination_path

    total = len(classified_items)
    for idx, item in enumerate(classified_items, start=1):
        target_dir = dest_root / item.relative_dest_dir
        res = safe_copy_file(item.metadata.file_path, target_dir, item.target_filename)
        transfer_results.append(res)

        status_icon = "✅" if res.status == "copied" else ("⏭️" if res.status == "skipped_duplicate" else "❌")
        sys.stdout.write(f"\r[{idx}/{total}] {status_icon} {item.target_filename[:45]:<45}")
        sys.stdout.flush()

    duration = time.time() - start_time
    print(f"\n\n✨ Transferência concluída em {duration:.1f} segundos!")

    # Step 5: Report & Notifications
    reporter = AuditReporter(Path("."))
    report_file = reporter.generate_report(source_dir, dest_root, classified_items, transfer_results, duration)
    print(f"📋 Relatório de auditoria gerado: {report_file}")

    copied_count = sum(1 for r in transfer_results if r.status == "copied")
    skipped_count = sum(1 for r in transfer_results if r.status == "skipped_duplicate")

    notify_event(
        title="Fotos Backup Workflow",
        message=f"Lote concluído! {copied_count} novos copiados, {skipped_count} duplicados pulados.",
        config=config.notifications
    )

    return True

def run_upload(config: PipelineConfig):
    gp_mgr = GooglePhotosManager(config.google_photos, config.biblioteca_path)
    gp_mgr.upload_pending_in_biblioteca(config.biblioteca_path)
    notify_event(
        title="Google Fotos",
        message="Sincronização da biblioteca concluída!",
        config=config.notifications
    )

def interactive_loop():
    config = load_config()

    while True:
        clear_screen()
        choice = display_menu(config)

        if choice == "0":
            print("\n👋 Encerrando. Até logo!")
            break

        elif choice == "1":
            clear_screen()
            print_banner()
            print("📥 INGESTÃO E ORGANIZAÇÃO DE FOTOS/VÍDEOS\n")
            
            drives = find_removable_drives()
            if drives:
                print(f"Cartões de memória detectados: {', '.join(drives)}")
                print(f"Sugestão: {drives[0]}DCIM")

            src_input = input("\nInforme a pasta de origem (ex: E:\\DCIM ou C:\\Fotos_Inbox): ").strip()
            if not src_input:
                continue

            source_path = Path(src_input)
            if not source_path.exists():
                print(f"❌ Caminho não existe: {source_path}")
                input("Pressione ENTER para voltar...")
                continue

            success = run_organize(source_path, config)
            if success and config.google_photos.auto_upload_after_countdown:
                next_action = countdown_prompt("Upload para o Google Fotos", timeout_seconds=config.countdown_seconds)
                if next_action in ("advance", "timeout"):
                    run_upload(config)

            input("\nPressione ENTER para voltar ao menu...")

        elif choice == "2":
            clear_screen()
            print_banner()
            print("☁️ UPLOAD PARA O GOOGLE FOTOS\n")
            run_upload(config)
            input("\nPressione ENTER para voltar ao menu...")

        elif choice == "3":
            clear_screen()
            print_banner()
            print("⏱️ COMPILAR TIMELAPSE DA GOPRO\n")
            if config.gopro_script_path and Path(config.gopro_script_path).exists():
                print(f"Executando script: {config.gopro_script_path} ...")
                os.system(f'python "{config.gopro_script_path}"')
            else:
                print("Nenhum script de timelapse configurado no config.json.")
                script_path = input("Informe o caminho do script (.py ou .bat): ").strip()
                if script_path and Path(script_path).exists():
                    config.gopro_script_path = script_path
                    from src.config import save_config
                    save_config(config)
                    os.system(f'python "{script_path}"')
            input("\nPressione ENTER para voltar ao menu...")

        elif choice == "4":
            clear_screen()
            print_banner()
            print("📋 ÚLTIMO RELATÓRIO DE AUDITORIA\n")
            rep_dir = Path("reports")
            if rep_dir.exists():
                reports = sorted(rep_dir.glob("audit_report_*.md"), reverse=True)
                if reports:
                    latest = reports[0]
                    print(f"Arquivo: {latest.name}\n")
                    print(latest.read_text(encoding="utf-8"))
                else:
                    print("Nenhum relatório encontrado ainda.")
            else:
                print("Pasta de relatórios não existe.")
            input("\nPressione ENTER para voltar ao menu...")

        elif choice == "5":
            settings_menu(config)

def main():
    parser = argparse.ArgumentParser(description="Fotos Backup Workflow - Resilient Media Pipeline")
    subparsers = parser.add_subparsers(dest="command", help="Comandos disponíveis")

    # Command: organize
    org_parser = subparsers.add_parser("organize", help="Ingere, classifica, renomeia e copia fotos/vídeos")
    org_parser.add_argument("--source", "-s", required=True, help="Pasta de origem (ex: E:\\DCIM)")

    # Command: upload
    subparsers.add_parser("upload", help="Envia fotos pendentes da biblioteca para o Google Fotos")

    # Command: run-all
    all_parser = subparsers.add_parser("run-all", help="Executa organização e upload com contagem regressiva")
    all_parser.add_argument("--source", "-s", required=True, help="Pasta de origem (ex: E:\\DCIM)")

    # Command: preflight
    subparsers.add_parser("preflight", help="Verifica integridade do ambiente e ferramentas")

    args = parser.parse_args()
    config = load_config()

    if not args.command:
        interactive_loop()
    elif args.command == "preflight":
        pf = check_preflight(config.destination_root)
        print(f"Python OK: {pf.python_ok} ({pf.python_version})")
        print(f"Exiftool: {pf.exiftool_path} ({'OK' if pf.exiftool_ok else 'NÃO ENCONTRADO'})")
        print(f"FFprobe: {pf.ffprobe_path} ({'OK' if pf.ffprobe_ok else 'NÃO ENCONTRADO'})")
        print(f"Destino Gravável: {pf.destination_writable} ({pf.free_disk_space_gb} GB livres)")
        print(f"Cartões Detectados: {pf.removable_drives}")
    elif args.command == "organize":
        run_organize(Path(args.source), config)
    elif args.command == "upload":
        run_upload(config)
    elif args.command == "run-all":
        success = run_organize(Path(args.source), config)
        if success:
            action = countdown_prompt("Upload para Google Fotos", timeout_seconds=config.countdown_seconds)
            if action in ("advance", "timeout"):
                run_upload(config)

if __name__ == "__main__":
    main()

import json
import time
from pathlib import Path
from datetime import datetime
from src.storage import TransferResult
from src.classifier import ClassifiedItem

class AuditReporter:
    def __init__(self, workspace_root: Path = Path(".")):
        self.workspace_root = workspace_root
        self.logs_dir = workspace_root / "logs"
        self.reports_dir = workspace_root / "reports"
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        self.history_file = self.logs_dir / "history.jsonl"

    def generate_report(
        self,
        source_dir: Path,
        destination_root: Path,
        classified_items: list[ClassifiedItem],
        transfer_results: list[TransferResult],
        duration_seconds: float,
    ) -> Path:
        now = datetime.now()
        timestamp_str = now.strftime("%Y%m%d_%H%M%S")
        report_file = self.reports_dir / f"audit_report_{timestamp_str}.md"

        copied = [r for r in transfer_results if r.status == "copied"]
        skipped = [r for r in transfer_results if r.status == "skipped_duplicate"]
        errors = [r for r in transfer_results if r.status == "error"]

        total_bytes = sum(r.file_size_bytes for r in copied)
        total_mb = total_bytes / (1024 * 1024)
        throughput_mb_s = (total_mb / duration_seconds) if duration_seconds > 0 else 0.0

        # Category counts
        cat_counts: dict[str, int] = {}
        for item in classified_items:
            cat_counts[item.category] = cat_counts.get(item.category, 0) + 1

        cat_names = {
            "astro_lua": "🌕 Astrofotografia (Lua RAW)",
            "timelapse_gopro": "⏱️ Timelapses (GoPro)",
            "rajada": "🦅 Rajadas Rápidas",
            "avulsa": "📷 Fotos Avulsas / Retratos",
            "video": "🎥 Vídeos (Câmeras)",
        }

        # Definition of Done (DoD) Reconciliation
        input_count = len(classified_items)
        output_count = len(copied) + len(skipped) + len(errors)
        dod_passed = (input_count == output_count and len(errors) == 0)

        # Build Markdown
        md = []
        md.append(f"# 📋 Relatório de Auditoria de Backup - {now.strftime('%d/%m/%Y %H:%M:%S')}\n")
        md.append("## 📌 Resumo Executivo\n")
        md.append(f"- **Origem:** `{source_dir}`")
        md.append(f"- **Destino:** `{destination_root}`")
        md.append(f"- **Duração:** `{duration_seconds:.1f}s`")
        md.append(f"- **Volume Transferido:** `{total_mb:.2f} MB` (`{throughput_mb_s:.2f} MB/s`)")
        md.append(f"- **Status Geral (DoD):** {'✅ APROVADO COM PERDA ZERO' if dod_passed else '⚠️ ATENÇÃO COM ERROS'}\n")

        md.append("## 📊 Reconciliação Matemática (Definition of Done)\n")
        md.append("| Métrica | Quantidade |")
        md.append("| :--- | :--- |")
        md.append(f"| **Arquivos Identificados na Origem** | `{input_count}` |")
        md.append(f"| **Arquivos Copiados (Novos com SHA-256)** | `{len(copied)}` |")
        md.append(f"| **Arquivos Já Existentes (Desduplicados)** | `{len(skipped)}` |")
        md.append(f"| **Erros de Transferência** | `{len(errors)}` |")
        md.append(f"| **Balanço Final** | `{'100% Reconciliado' if input_count == output_count else 'Inconsistente'}` |\n")

        md.append("## 🏷️ Separação por Categoria\n")
        md.append("| Categoria | Total de Arquivos |")
        md.append("| :--- | :--- |")
        for k, v in cat_counts.items():
            md.append(f"| {cat_names.get(k, k)} | `{v}` |")
        md.append("")

        if errors:
            md.append("## ⚠️ Erros Encontrados\n")
            for err in errors:
                md.append(f"- **Arquivo:** `{err.source_path}` - **Erro:** {err.error_message}")
            md.append("")

        report_content = "\n".join(md)
        report_file.write_text(report_content, encoding="utf-8")

        # Append to history.jsonl
        history_entry = {
            "timestamp": now.isoformat(),
            "source": str(source_dir),
            "destination": str(destination_root),
            "total_items": input_count,
            "copied": len(copied),
            "skipped": len(skipped),
            "errors": len(errors),
            "total_bytes": total_bytes,
            "duration_seconds": round(duration_seconds, 2),
            "throughput_mb_s": round(throughput_mb_s, 2),
            "categories": cat_counts,
        }
        with open(self.history_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(history_entry, ensure_ascii=False) + "\n")

        return report_file

from datetime import datetime, timedelta
from typing import Optional
from rich.console import Console
from rich.progress import (
    Progress,
    ProgressColumn,
    BarColumn,
    TextColumn,
    TimeRemainingColumn,
    TimeElapsedColumn,
    TransferSpeedColumn,
    DownloadColumn,
    TaskProgressColumn,
    MofNCompleteColumn,
    SpinnerColumn,
)
from rich.text import Text
from rich.panel import Panel
from rich.table import Table

console = Console()

class EstimatedEndTimeColumn(ProgressColumn):
    """Exibe o horário previsto de término no relógio do sistema (ex: Término: 19:45:10)."""
    
    def __init__(self, table_column=None):
        super().__init__(table_column=table_column)

    def render(self, task) -> Text:
        remaining = task.time_remaining
        if remaining is None:
            return Text("Término: --:--:--", style="dim")
        eta_time = datetime.now() + timedelta(seconds=int(remaining))
        return Text(f"Término: {eta_time.strftime('%H:%M:%S')}", style="cyan bold")

class SpeedPerSecondColumn(ProgressColumn):
    """Exibe a taxa em itens/segundo (ex: 24.5 arqs/s)."""
    
    def __init__(self, unit: str = "arqs/s", table_column=None):
        self.unit = unit
        super().__init__(table_column=table_column)

    def render(self, task) -> Text:
        speed = task.speed
        if speed is None:
            return Text(f"--.- {self.unit}", style="dim")
        return Text(f"{speed:.1f} {self.unit}", style="magenta")

class CurrentFileColumn(ProgressColumn):
    """Exibe o nome do arquivo atual que está sendo transferido ou processado com largura fixa anti-jitter."""
    
    def __init__(self, max_width: int = 26, table_column=None):
        self.max_width = max_width
        super().__init__(table_column=table_column)

    def render(self, task) -> Text:
        fn = task.fields.get("filename", "")
        if not fn:
            return Text(" " * (self.max_width + 2))
        if len(fn) > self.max_width:
            prefix_len = max(self.max_width - 8, 3)
            fn = f"{fn[:prefix_len]}...{fn[-5:]}"
        formatted = f"↳ {fn}"
        return Text(f"{formatted:<{self.max_width + 2}}", style="yellow")

class VerticalByteProgress(Progress):
    """Barra de progresso vertical para transferência de bytes e I/O (uma linha por informação)."""

    def __init__(self, bar_width: int = 25, *args, **kwargs):
        self.bar_col = BarColumn(bar_width=bar_width)
        super().__init__(*args, **kwargs)

    def get_renderables(self):
        for task in self.tasks:
            if not task.visible:
                continue
            fn = task.fields.get("filename", "")
            pct = f"{task.percentage:.1f}%" if task.percentage is not None else "--%"

            tot = task.total or 0
            comp = task.completed
            if tot >= 1024 ** 3:
                size_str = f"{comp / (1024 ** 3):.2f} GB / {tot / (1024 ** 3):.2f} GB"
            else:
                size_str = f"{comp / (1024 ** 2):.1f} MB / {tot / (1024 ** 2):.1f} MB"

            if task.speed:
                speed_str = f"{task.speed / (1024 * 1024):.1f} MB/s"
            else:
                speed_str = "--.- MB/s"

            elapsed_str = str(timedelta(seconds=int(task.elapsed or 0)))
            rem_sec = int(task.time_remaining) if task.time_remaining is not None else None
            rem_str = str(timedelta(seconds=rem_sec)) if rem_sec is not None else "--:--:--"
            eta_str = (datetime.now() + timedelta(seconds=rem_sec)).strftime("%H:%M:%S") if rem_sec is not None else "--:--:--"

            grid = Table.grid(padding=(0, 1))
            grid.add_column(style="dim", width=18)
            grid.add_column()

            grid.add_row("[bold blue]Operacao:[/bold blue]", f"[bold white]{task.description}[/bold white]")
            if fn:
                grid.add_row("Arquivo atual:", f"[yellow]{fn}[/yellow]")

            bar_cell = Table.grid(padding=(0, 1))
            bar_cell.add_column()
            bar_cell.add_column()
            bar_cell.add_row(self.bar_col(task), f"[bold white]{pct}[/bold white] ({size_str})")
            grid.add_row("Progresso:", bar_cell)

            grid.add_row("Velocidade:", f"[cyan]{speed_str}[/cyan]")
            grid.add_row("Tempo decorrido:", f"{elapsed_str}")
            grid.add_row("Tempo restante:", f"[magenta]{rem_str}[/magenta]")
            grid.add_row("Previsao fim:", f"[cyan bold]{eta_str}[/cyan bold]")
            yield grid


class VerticalItemProgress(Progress):
    """Barra de progresso vertical para contagem de arquivos e metadados (uma linha por informação)."""

    def __init__(self, unit: str = "arqs/s", bar_width: int = 25, *args, **kwargs):
        self.unit = unit
        self.bar_col = BarColumn(bar_width=bar_width)
        super().__init__(*args, **kwargs)

    def get_renderables(self):
        for task in self.tasks:
            if not task.visible:
                continue
            fn = task.fields.get("filename", "")
            pct = f"{task.percentage:.1f}%" if task.percentage is not None else "--%"
            tot = int(task.total or 0)
            comp = int(task.completed)
            count_str = f"{comp:,} / {tot:,} itens"

            if task.speed:
                speed_str = f"{task.speed:.1f} {self.unit}"
            else:
                speed_str = f"--.- {self.unit}"

            elapsed_str = str(timedelta(seconds=int(task.elapsed or 0)))
            rem_sec = int(task.time_remaining) if task.time_remaining is not None else None
            rem_str = str(timedelta(seconds=rem_sec)) if rem_sec is not None else "--:--:--"
            eta_str = (datetime.now() + timedelta(seconds=rem_sec)).strftime("%H:%M:%S") if rem_sec is not None else "--:--:--"

            grid = Table.grid(padding=(0, 1))
            grid.add_column(style="dim", width=18)
            grid.add_column()

            grid.add_row("[bold blue]Operacao:[/bold blue]", f"[bold white]{task.description}[/bold white]")
            if fn:
                grid.add_row("Arquivo atual:", f"[yellow]{fn}[/yellow]")

            bar_cell = Table.grid(padding=(0, 1))
            bar_cell.add_column()
            bar_cell.add_column()
            bar_cell.add_row(self.bar_col(task), f"[bold white]{pct}[/bold white] ({count_str})")
            grid.add_row("Progresso:", bar_cell)

            grid.add_row("Velocidade:", f"[magenta]{speed_str}[/magenta]")
            grid.add_row("Tempo decorrido:", f"{elapsed_str}")
            grid.add_row("Tempo restante:", f"[magenta]{rem_str}[/magenta]")
            grid.add_row("Previsao fim:", f"[cyan bold]{eta_str}[/cyan bold]")
            yield grid


def create_byte_progress() -> VerticalByteProgress:
    """Barra de progresso vertical para transferência de arquivos e I/O em bytes."""
    return VerticalByteProgress(console=console, transient=False)


def create_item_progress(unit: str = "arqs/s") -> VerticalItemProgress:
    """Barra de progresso vertical para contagem de arquivos e metadados."""
    return VerticalItemProgress(unit=unit, console=console, transient=False)


def print_stage_header(stage_name: str, total_items: int = 0, total_bytes: int = 0):
    """Exibe cabeçalho moderno e padronizado no início de cada etapa (linhas verticais empilhadas)."""
    now_str = datetime.now().strftime("%H:%M:%S")
    info_parts = [f"  • [bold green]Início:[/bold green]   {now_str}"]

    if total_items > 0:
        info_parts.append(f"  • [bold cyan]Arquivos:[/bold cyan] {total_items:,}")
    if total_bytes > 0:
        gb = total_bytes / (1024 ** 3)
        if gb >= 1.0:
            info_parts.append(f"  • [bold yellow]Volume:[/bold yellow]   {gb:.2f} GB")
        else:
            mb = total_bytes / (1024 ** 2)
            info_parts.append(f"  • [bold yellow]Volume:[/bold yellow]   {mb:.1f} MB")

    header_text = "\n".join(info_parts)
    console.print(Panel(
        f"[bold white]{stage_name}[/bold white]\n\n{header_text}",
        border_style="bright_blue",
        expand=False,
    ))


def print_stage_summary(stage_name: str, start_time: datetime, success: bool, items_done: int = 0, bytes_done: int = 0):
    """Exibe resumo no término da etapa com métricas dispostas verticalmente."""
    elapsed = datetime.now() - start_time
    total_sec = max(elapsed.total_seconds(), 0.001)

    m, s = divmod(int(total_sec), 60)
    h, m = divmod(m, 60)
    dur_str = f"{h:02d}h{m:02d}s" if h == 0 else f"{h:02d}h{m:02d}m{s:02d}s"

    details = [f"Duração: [bold]{dur_str}[/bold]"]
    if bytes_done > 0:
        avg_speed_mb = (bytes_done / (1024 * 1024)) / total_sec
        details.append(f"Média:   [bold cyan]{avg_speed_mb:.1f} MB/s[/bold cyan]")
    elif items_done > 0:
        avg_items_s = items_done / total_sec
        details.append(f"Média:   [bold magenta]{avg_items_s:.1f} arqs/s[/bold magenta]")

    status_icon = "✅" if success else "⚠️"
    status_style = "green" if success else "yellow"

    console.print(f"\n{status_icon} [{status_style}]{stage_name} finalizada![/{status_style}]")
    for d in details:
        console.print(f"   • {d}")
    console.print()

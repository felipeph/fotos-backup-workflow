# 📸 Fotos Backup Workflow - Resilient Media Pipeline 🚀

Pipeline automatizado, modular e resiliente em Python para ingestão, classificação inteligente, renomeação padronizada, organização cronológica e backup seguro de fotos e vídeos com garantia de **Perda Zero (Zero-Loss)**.

Projetado especialmente para fluxos mistos de câmeras dedicadas:
- **Canon PowerShot SX60 HS / SX50 HS**: Fotografia de pássaros (teleobjetiva máxima, rajadas rápidas), vídeos 1080p a 60fps, paisagens e astrofotografia da Lua em RAW (`.CR2`).
- **Canon EOS Rebel T6 (50mm f/1.8)**: Retratos e eventos sociais.
- **GoPro**: Sequências diárias de timelapses e vídeos dinâmicos.

---

## 🌟 Funcionalidades Principais

1. **Classificação Automática & Separação de Mídia**:
   - 🌕 **Astrofotografia da Lua**: Detecta arquivos RAW (`.CR2`) tirados com zoom teleobjetivo máximo na SX60/SX50 e isola em `Astrofotografia/Lua/ANO/MES/DIA/sessao_HH-mm-SS/` para stacking (AutoStakkert, Siril, PIPP, Registax).
   - ⏱️ **Timelapses GoPro**: Agrupa sequências diárias de fotos da GoPro em `Timelapses/GoPro/ANO/MES/DIA/timelapse_HH-mm-SS/` com atalho no menu para executar seu script de compilação/publicação.
   - 🦅 **Rajadas Rápidas (Pássaros & Ação)**: Agrupa disparos consecutivos com intervalo $\le 3\text{s}$ em `Biblioteca/ANO/MES/DIA/rajada_HH-mm-SS/`, facilitando escolher a melhor foto da série.
   - 📷 **Fotos Avulsas & Retratos**: Fotos isoladas (Canon T6 / paisagens) são organizadas em `Biblioteca/ANO/MES/DIA/avulsas/`.
   - 🎥 **Vídeos**: Vídeos das câmeras (incluindo 1080p 60fps) são organizados em `Biblioteca/ANO/MES/DIA/videos/`.

2. **Nomenclatura Compacto-Inteligente (~60 a 70 caracteres)**:
   - Fotos: `YYYY-MM-DD_HH-mm-SS_{Camera}_{Focal}_{Abertura}_{Velocidade}_{ISO}_{Original}.ext`
     - *Exemplo SX60:* `2026-09-06_14-25-30_SX60_1365mm_f6.5_1-1000s_ISO400_IMG9821.jpg`
     - *Exemplo T6:* `2026-09-06_18-40-12_T6_50mm_f1.8_1-200s_ISO800_IMG4512.jpg`
   - Vídeos: `YYYY-MM-DD_HH-mm-SS_{Camera}_{Resolucao}_{FPS}_{Duracao}_{Original}.ext`
     - *Exemplo:* `2026-09-06_15-10-00_SX60_1080p_60fps_01m45s_MVI9822.mp4`

3. **Garantia de Perda Zero (Zero-Loss) & Desduplicação**:
   - Cópia segura com cálculo e validação estrita de hash SHA-256 e tamanho de bytes antes e depois da cópia.
   - Pula automaticamente fotos já importadas sem reprocessamento.
   - **O cartão SD original nunca é alterado ou apagado** (a formatação é feita pelo usuário na própria câmera após checagem).

4. **Upload Integrado para o Google Fotos com Contagem Regressiva (180s)**:
   - Módulo OAuth2 padrão do Google com manifesto local (`.uploaded_manifest.json`) que previne reenvios.
   - Timer interativo após a organização:
     - `[ENTER]`: envia imediatamente.
     - `[P]`: pausa o fluxo para você curar/selecionar com calma as fotos das rajadas.
     - `[C]`: cancela o envio desta sessão.
     - **Auto-avanço unattended**: se rodar de madrugada ou desacompanhado, o timer esgota e envia automaticamente.

5. **Notificações Multicanal & Relatórios de Auditoria**:
   - Notificações Toast nativas no Windows e aviso sonoro (`winsound`).
   - Push móvel no aplicativo `ntfy.sh`.
   - Relatórios automáticos em Markdown na pasta `reports/` com balanço matemático (*Definition of Done*) e histórico acumulado em `logs/history.jsonl`.

---

## 🗂️ Estrutura da Biblioteca Gerada

```text
D:/Fotos_Organizadas/ (ou pasta configurada)
├── Biblioteca/
│   └── 2026/
│       └── 09/
│           └── 06/
│               ├── avulsas/
│               │   └── 2026-09-06_14-10-05_SX60_50mm_f4.0_1-500s_ISO100_IMG1001.jpg
│               ├── rajada_14-25-30/
│               │   ├── 2026-09-06_14-25-30_SX60_1365mm_f6.5_1-1000s_ISO400_IMG1002.jpg
│               │   └── 2026-09-06_14-25-31_SX60_1365mm_f6.5_1-1000s_ISO400_IMG1003.jpg
│               └── videos/
│                   └── 2026-09-06_15-10-00_SX60_1080p_60fps_01m45s_MVI1004.mp4
├── Astrofotografia/
│   └── Lua/
│       └── 2026/
│           └── 09/
│               └── 06/
│                   └── sessao_21-30-00/
│                       ├── 2026-09-06_21-30-00_SX60_1365mm_f6.5_1-250s_ISO200_IMG2001.cr2
│                       └── 2026-09-06_21-30-02_SX60_1365mm_f6.5_1-250s_ISO200_IMG2002.cr2
└── Timelapses/
    └── GoPro/
        └── 2026/
            └── 09/
                └── 06/
                    └── timelapse_08-00-00/
                        ├── 2026-09-06_08-00-00_GoPro_GOPR0001.jpg
                        └── 2026-09-06_08-00-05_GoPro_GOPR0002.jpg
```

---

## 🛠️ Requisitos de Sistema

- **Python**: 3.10 ou superior.
- **Exiftool**: Utilitário para leitura rápida de metadados EXIF (`exiftool.exe` no PATH ou em `C:\Windows\exiftool.exe`).
- **FFprobe**: Utilitário do pacote FFmpeg para análise técnica de vídeos (`ffprobe.exe` no PATH).

---

## 🚀 Instalação

1. Clone o repositório:
   ```bash
   git clone https://github.com/felipeph/fotos-backup-workflow.git
   cd fotos-backup-workflow
   ```

2. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```

3. Crie seu arquivo de configuração local a partir do modelo:
   ```bash
   copy config.example.json config.json
   ```
   *Edite `config.json` para indicar o seu disco de destino (`destination_root`) e o seu tópico do `ntfy_topic`.*

---

## 💻 Como Usar

### Opção 1: Menu Interativo no Terminal (Recomendado)
Dê um duplo clique no arquivo **`run_pipeline.bat`** ou execute:
```powershell
python main.py
```
Você verá o menu interativo:
```text
======================================================================
      📸 FOTOS BACKUP WORKFLOW - RESILIENT MEDIA PIPELINE 🚀
   Perda Zero | Astrofotografia | Timelapses | Google Fotos | Pássaros
======================================================================
[STATUS] Exiftool: ✅ OK | FFprobe: ✅ OK | Espaço Livre: 239 GB
[DESTINO] D:/Fotos_Organizadas
----------------------------------------------------------------------
 1. 📥 Ingerir e Organizar Fotos/Vídeos (Cartão SD ou Pasta)
 2. ☁️  Upload para o Google Fotos (Fotos da Biblioteca)
 3. ⏱️  Compilar Timelapse da GoPro (Chamar script existente)
 4. 📋 Visualizar Último Relatório de Auditoria
 5. ⚙️  Ajustar Configurações (Caminhos, Notificações, Timer)
 0. 🚪 Sair
----------------------------------------------------------------------
```

### Opção 2: Linha de Comando (CLI)
- **Organizar uma pasta ou cartão SD:**
  ```powershell
  python main.py organize --source "E:\DCIM"
  ```
- **Executar organização com contagem regressiva para upload no Google Fotos:**
  ```powershell
  python main.py run-all --source "E:\DCIM"
  ```
- **Upload manual de fotos pendentes da biblioteca:**
  ```powershell
  python main.py upload
  ```
- **Verificar ferramentas instaladas:**
  ```powershell
  python main.py preflight
  ```

---

## 🧪 Testes Automatizados

Para executar a suíte de testes unitários:
```powershell
python -m pytest tests/ -v
```

---

## 🔒 Segurança e Privacidade

Arquivos que contenham credenciais ou dados locais (`config.json`, `credentials.json`, `token.json`, `logs/`, `reports/`) estão estritamente ignorados pelo `.gitignore` para garantir que nenhum dado pessoal ou credencial de nuvem seja commitado no repositório.

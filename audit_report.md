# SageDLP Code Audit Report

## 1. Security Analysis (Bandit)

- **High Severity:** 1
- **Medium Severity:** 11
- **Low Severity:** 93

### High Severity Issues:
- **B602**: subprocess call with shell=True identified, security issue.
  - Location: `sage_dlp/core/sage_ffmpeg.py:400`

### Medium Severity Issues:
- **B103**: Chmod setting a permissive mask 0o755 on file (exe_path).
  - Location: `sage_dlp/core/sage_deno.py:48`
- **B103**: Chmod setting a permissive mask 0o755 on file (exe_path).
  - Location: `sage_dlp/core/sage_deno.py:199`
- **B310**: Audit url open for permitted schemes. Allowing use of file:/ or custom schemes is often unexpected.
  - Location: `sage_dlp/core/sage_llm_client.py:155`
- **B113**: Call to requests without timeout
  - Location: `sage_dlp/core/sage_utils.py:428`
- **B103**: Chmod setting a permissive mask 0o755 on file (temp_file).
  - Location: `sage_dlp/core/sage_utils.py:439`
- **B113**: Call to requests without timeout
  - Location: `sage_dlp/core/sage_yt_dlp.py:100`
- **B103**: Chmod setting a permissive mask 0o755 on file (exe_path).
  - Location: `sage_dlp/core/sage_yt_dlp.py:133`
- **B103**: Chmod setting a permissive mask 0o755 on file (exe_path).
  - Location: `sage_dlp/core/sage_yt_dlp.py:155`
- **B103**: Chmod setting a permissive mask 0o755 on file (yt_dlp_path).
  - Location: `sage_dlp/gui/sage_gui_dialogs/sage_dialogs_update.py:143`
- **B103**: Chmod setting a permissive mask 0o755 on file (yt_dlp_path).
  - Location: `sage_dlp/gui/sage_gui_dialogs/sage_dialogs_update.py:444`
- **B103**: Chmod setting a permissive mask 0o755 on file (yt_dlp_path).
  - Location: `sage_dlp/gui/sage_gui_dialogs/sage_dialogs_updater.py:605`

## 2. Code Quality (Pylint)

- **Errors:** 87
- **Warnings:** 394
- **Refactor:** 157
- **Convention:** 721

### Top Errors:
- **E0401**: Unable to import 'PySide6.QtWidgets' (67 occurrences)
- **E0602**: Undefined variable 'QLineEdit' (10 occurrences)
- **E0203**: Access to member '_deno_download_thread' before its definition line 737 (5 occurrences)
- **E1101**: Instance of 'Exception' has no 'code' member (2 occurrences)
- **E1129**: Context manager 'NoneType' doesn't implement __enter__ and __exit__. (1 occurrences)
- **E1135**: Value 'video_info' doesn't support membership test (1 occurrences)
- **E1121**: Too many positional arguments for function call (1 occurrences)

### Top Warnings:
- **W0718**: Catching too general exception Exception (140 occurrences)
- **W0212**: Access to a protected member _MEIPASS of a client class (63 occurrences)
- **W0611**: Unused QSizePolicy imported from PySide6.QtWidgets (61 occurrences)
- **W0642**: Invalid assignment to self in method (26 occurrences)
- **W0311**: Bad indentation. Found 21 spaces, expected 20 (23 occurrences)
- **W1510**: 'subprocess.run' used without explicitly defining the value for 'check'. (23 occurrences)
- **W0612**: Unused variable 'seg_idx' (11 occurrences)
- **W0621**: Redefining name 'ConfigManager' from outer scope (line 367) (8 occurrences)
- **W0613**: Unused argument 'force' (8 occurrences)
- **W1309**: Using an f-string that does not have any interpolated variables (7 occurrences)

## 3. Code Complexity (Radon)

### High Complexity Blocks (Score D, E, F):
- F 629:0 parse_yt_dlp_error - D
- M 201:4 SubtitlesProcessor.process_segments - F
- C 123:0 DownloadDenoThread - D
- M 139:4 DownloadDenoThread.run - D
- M 733:4 DownloadThread._parse_output_line - F
- M 243:4 DownloadThread._build_yt_dlp_command - F
- M 555:4 DownloadThread._run_direct_command - E
- M 69:4 RuleSegmenter._group_into_natural_units - D
- M 8:4 RuleSegmenter.process - D
- F 197:0 install_ffmpeg_windows - F
- M 436:4 UIMixin.toggle_analysis_dependent_controls - D
- M 105:4 AnalysisThread._analyze_url_with_subprocess - D
- M 305:4 FormatTableMixin._populate_format_table - F
- M 256:4 VideoInfoMixin.open_subtitle_dialog - D
- M 38:4 DownloadMixin.start_download - F
- M 66:4 CustomOptionsDialog.__init__ - D

# Zmiany

Format: [wersja] — co nowego z punktu widzenia nauczyciela.

## [3.1.9] — 2026-09-24

### 连接与投影页诊断

- 安卓端检查电脑 `/mobile` 页面是否包含“更多 → 连接与设备”功能；连接到旧版电脑服务时保留连接栏并明确提示升级，避免隐藏地址栏后无法更换服务器。
- 投影页连接状态接口不可用时显示重试与地址提示，不再留下空白页面。

## [3.1.8] — 2026-09-24

### 课堂扫码与投影

- 投影大屏增加“上一题”“下一题”，切题后自动开始新题；手机同步当前题目并自动开启后置摄像头扫码。
- 扫描时按手机当前全屏画面的上边缘读取卡片，横屏和竖屏均以画面上方的选项为准。
- 手机端结束作答后立即关闭本机摄像头并显示 A/B/C/D 作答人数；学生页显示姓名。下一题会重新启动摄像头。
- IP 地址、Wi-Fi 设置、摄像头开关和后置镜头选择移入“更多”，课堂和测验页不再占用顶部空间；页面导航支持按钮切换与左右滑动。

### 投影主题

- 投影画布改为浅色，新增题目默认使用浅色课堂主题；保留夜色、海蓝等深色选择。
- 原朱红中国风主题移除，宣纸、水墨和青瓷主题改为浅色；新增深绿色黑板与粉笔字主题。

## [3.1.7] — 2026-09-24

### 安卓教师端 Material 3 Expressive 页面

- 手机工作台主导航收敛为“课堂、测验、更多”，课堂页集中选择班级、控制题目、扫码和查看作答；测验加载后自动回到课堂。
- 名单维护、备用扫码、作答报告和高级选项折叠在“更多”，Word 导题保留在测验页的展开区域。
- 调整按钮、选项卡片、层级色和圆角，并按屏幕宽度在底部导航与侧边导航之间切换；尊重系统减少动态效果设置。
- 修复底部导航旧属性与现有三项入口不匹配导致的页面切换失效。

## [3.1.6] — 2026-09-24

### 安卓扫码结果

- 扫码页中央红色按钮改为结束本题并打开学生作答结果，停止收集答案时继续显示摄像头画面。
- 横屏时把结果面板停靠在右侧，默认展示学生作答状态；学生答案列在作答结束后显示。
- 安卓端增加后置镜头选择器，可选自动主摄或具体后置镜头；停止摄像头后可切换镜头。

## [3.1.5] — 2026-09-24

### 手机与投影端

- 手机开始扫码时默认显示全屏画面，图表和学生名单由教师主动打开。
- 手机后置摄像头上传前将图像旋转为当前屏幕方向；扫描按画面上方识别选项。
- 投影端学生名单保留滚动容器和行节点，只更新发生变化的学生状态，滚动时不再被刷新打断。
- 安卓桌面新增自适应 QuizScanner 图标，图形以答题卡、选项和扫描框为元素。

## [3.1.4] — 2026-09-24

### 安卓扫码画面

- 手机全屏扫描改为横竖屏自适应铺满画面；按摄像头传感器方向旋转每帧，预览方向与手机屏幕一致。
- 扫描按设备方向校正“朝上”的基准，横屏和竖屏对同一张答题卡得到相同答案。
- 手机摄像头只选择后置镜头；多镜头设备优先选择等效焦距接近标准主摄的镜头，缺少镜头参数时选择分辨率较高的后置镜头。

## [3.1.3] — 2026-09-24

### 优化

- 手机摄像头采集提升到约 6–7 帧/秒，电脑端只识别新画面，预览只发送新帧，减少同一 Wi-Fi 上的重复流量和识别队列；手机作答状态轮询缩短至约 250 毫秒。
- 手机后置摄像头预览固定使用正向画面，修复扫码镜像显示。
- 全屏学生面板改为固定区域内纵向滚动，题目显示区域保持尺寸；手机工作台和桌面教师端可设置揭晓正确答案时是否向大屏显示逐人答案。
- 题干字号与选项字号分开设置，默认加大选项文字；投影背景新增中国风朱红、水墨和青瓷配色。
- 电脑热点无法开启时，可改用电脑与手机连接同一路由器；桌面启动器增加地址和连接说明。

### Nowe

- Oddzielny wybór rozmiaru tekstu odpowiedzi od rozmiaru pytania oraz trzy chińskie warianty tła slajdu: czerwień, tusz i jadeit.

## [3.1.2] — 2026-09-24

### Nowe

- Telefonowy pulpit prowadzącego z widokiem skanowania na cały ekran. Podgląd kamery ma przełączane zakładki wykresu odpowiedzi oraz statusu uczniów, a dolny pasek steruje kamerą i widokiem listy.
- Rozpoczęcie pytania w aplikacji automatycznie uruchamia telefoniczny aparat, jeśli użytkownik przyznał uprawnienie. Przyciski końca pytania i przejścia dalej pozostają dostępne w widoku skanowania.

### 修改

- 手机教师工作台增加全屏扫码界面，按 Plickers 的操作方式提供图表、学生状态切换和底部摄像头控制。开始作答时自动进入全屏并启动手机摄像头；可在全屏中结束本题、继续下一题。
- 手机工作台增加“学生、结果、题库、设置”快捷导航，并提供题库和最近使用测验列表。

## [3.1.1] — 2026-09-24

### 新增

- 教师端可按题设置是否启用倒计时；无倒计时模式由教师手动结束作答。
- 教师可先选作答班级，并设置投影端在扫描时显示“已扫描”或学生答案。投影端作答前不展示名单；开始后只显示所选班级，结束后显示 A/B/C/D 统计和学生作答明细。

### Poprawki

- Serwer uruchamia się automatycznie po otwarciu launchera; launcher ponownie wykorzystuje tę samą wersję, a przed uruchomieniem przy wykryciu starszej wersji prosi o zamknięcie jej lub zmianę portu.
- Zapytanie Windows o adresy sieciowe działa bez wyskakującego okna konsoli. Dodano bezpośredni przycisk do ustawień mobilnego hotspotu.
- APK wyświetla czytelny ekran błędu po utracie połączenia, może otworzyć ustawienia Wi-Fi telefonu i ponawia połączenie po powrocie.
- Usunięto dźwięki tablicy i ustawienia dźwięku z panelu nauczyciela.

## [3.1.0] — 2026-08-02

### Nowe

- **Wzory LaTeX renderowane przez KaTeX** — wzór zamykasz w dolarach
  (`$\frac{1}{2}$`, `$\pi r^2$`, `$$\begin{cases}…\end{cases}$$`), a tablica
  i panel pokazują go złożonego jak w podręczniku. Podwójne dolary dają wzór
  wyśrodkowany w osobnej linii.
- **Sekcja LaTeX w przyborniku** — gotowe szablony: ułamek piętrowy,
  pierwiastek stopnia n, potęga i indeks, całka z granicami, suma, granica,
  symbol Newtona, kreska nad symbolem, wektor, układ równań, macierz.
  Szablony działają na zaznaczeniu.
- **Podgląd na żywo pod przybornikiem** — pokazuje edytowane właśnie pole
  dokładnie tak, jak zobaczą je uczniowie; błąd składni widać od razu.
- Przykładowy quiz ma teraz pytanie z ułamkami, żeby było co obejrzeć od razu
  po instalacji.

### Zmiany

- KaTeX leży w repozytorium (`quizscanner/web/vendor/katex`, ok. 600 kB,
  licencja MIT) i wchodzi do pliku `.exe` — **nic nie pobiera się z internetu**,
  aplikacja dalej działa w pełni offline.
- W raportach (PDF, Excel, CSV, HTML, TXT) wzory zapisywane są czytelnym
  tekstem: `$\frac{1}{2}$` → `(1)/(2)`, `$\sqrt[3]{27}$` → `³√(27)`. Pełny
  zapis LaTeX zostaje w eksporcie JSON.
- Szybkie sprawdzenie (`tools/selftest.py`) obejmuje dodatkowo zasoby KaTeX
  (razem z typem MIME czcionek) i zamianę wzorów na tekst.

## [3.0.0] — 2026-08-02

### Nowe

- **Przybornik matematyczny w edytorze** — paleta symboli w sześciu sekcjach
  (podstawowe, potęgi i ułamki, greka, zbiory i logika, geometria, analiza),
  szablony działające na zaznaczeniu (`√( )`, przedział, układ) oraz zamiana
  zaznaczonego fragmentu na indeks górny/dolny. Wzory to tekst Unicode, więc
  wyglądają tak samo w edytorze, na tablicy i w raporcie PDF.
- **Motyw ciemny jako domyślny + 6 kolejnych**: jasny, ocean, las, zachód
  słońca, cukierkowy i wysoki kontrast. Zmiana z panelu działa od razu również
  na tablicy — także gdy stoi na innym komputerze.
- **Dźwięki tablicy** — start pytania, odliczanie ostatnich pięciu sekund,
  koniec czasu, wynik i fanfara na podium. Generowane w przeglądarce (WebAudio),
  bez plików audio. Przełącznik i suwak głośności w panelu.
- **Raport po grze** — nowy przycisk **„📊 Raport"**: ranking, skuteczność
  każdego ucznia, odpowiedzi na każde pytanie, rozkład A/B/C/D i wskazanie
  najtrudniejszego pytania. Pobieranie w **PDF, Excelu (XLSX), CSV, HTML,
  JSON i TXT**.
- **Automatyczny zapis raportu** — po ostatnim pytaniu komplet HTML + CSV + JSON
  trafia sam do `data/raporty/`.
- **Automatyczna aktualizacja** — pasek z informacją o nowym wydaniu i pobranie
  jednym kliknięciem; w wersji `.exe` plik podmienia się przy zamykaniu programu.
  Sprawdzanie można wyłączyć.
- **FAQ** — [docs/FAQ.md](docs/FAQ.md) z odpowiedziami na pytania o karty,
  kamerę, wzory, raporty, prywatność i typowe kłopoty.
- **Szybkie sprawdzenie** `tools/selftest.py` — uruchamia aplikację bez kamery
  i przechodzi przez nią jak nauczyciel: strony, API, karty PDF, cały przebieg
  quizu, wszystkie formaty raportu i kompletność tłumaczeń PL/EN.

### Zmiany

- **Nowa struktura katalogów**: kod w pakiecie `quizscanner/`, dane użytkownika
  w `data/`, dokumentacja w `docs/`, skrypty w `scripts/`. Serwer uruchamia się
  teraz przez `python -m quizscanner` (dawniej `python app.py`).
- Dane nauczyciela (quizy, media, lista uczniów, raporty, ustawienia) siedzą
  w jednym folderze `data/` obok programu — łatwiej je skopiować i zarchiwizować.
- Eksport wyników przeniesiony ze skromnego `wyniki_<data>.csv` do pełnego
  raportu (stary przycisk „⬇ Eksport wyników" zastąpił „📊 Raport").
- Kontrola polskich znaków obsługuje wyjątki w linii (`polish-ok`), dzięki czemu
  nazwy funkcji trygonometrycznych nie są zgłaszane jako literówki.
- Numer wersji do budowania `.exe` czytany jest z `quizscanner/__init__.py`,
  więc nie da się wydać pliku z nieaktualnym numerem.

## [2.0.1]

- Naprawa narzędzia kontroli polskich znaków, pełne diakrytyki w repozytorium.

## [2.0.0]

- Języki PL/EN, tryb automatyczny, zdjęcia i filmy w pytaniach, telefon jako kamera.

## [1.3.0]

- Naprawa: skaner nie wykrywał większości kart (odbicie lustrzane).

## [1.2.0]

- Logo aplikacji, dopracowana strona repozytorium, numer wersji w nazwie `.exe`.

## [1.1.0]

- Pobieranie kart do druku (PDF) z poziomu aplikacji.

## [1.0.0]

- Pierwsze wydanie: system quizowy z odczytem kart ArUco z kamery,
  jednoplikowy `QuizScanner.exe`.

package cn.quizscanner.teacher

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Bundle
import android.provider.Settings
import android.view.WindowManager
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.viewModels
import androidx.compose.foundation.*
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.foundation.pager.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalConfiguration
import androidx.compose.ui.text.buildAnnotatedString
import androidx.compose.ui.text.SpanStyle
import androidx.compose.ui.text.withStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.camera.view.PreviewView
import androidx.core.content.ContextCompat
import androidx.core.view.WindowCompat
import androidx.core.view.WindowInsetsCompat
import androidx.core.view.WindowInsetsControllerCompat
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.compose.LocalLifecycleOwner
import kotlinx.coroutines.launch
import org.json.JSONObject
import org.opencv.android.OpenCVLoader

class NativeActivity: ComponentActivity() {
    private val model: TeacherModel by viewModels()
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        WindowCompat.setDecorFitsSystemWindows(window, false)
        if (!OpenCVLoader.initLocal()) model.cameraError = "卡片识别组件无法加载"
        setContent {
            @OptIn(ExperimentalMaterial3ExpressiveApi::class)
            MaterialExpressiveTheme(colorScheme = lightColorScheme(
                primary = Color(0xFF6553B3), onPrimary = Color.White,
                primaryContainer = Color(0xFFE9DDFF), onPrimaryContainer = Color(0xFF28164B),
                secondaryContainer = Color(0xFFDCEBE4), surface = Color(0xFFFCF8FF),
                background = Color(0xFFFCF8FF)
            )) { TeacherApp(model) }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun TeacherApp(model: TeacherModel) {
    val context = LocalContext.current
    val activity = context as ComponentActivity
    val pager = rememberPagerState(pageCount = { 3 })
    val scope = rememberCoroutineScope()
    var scanScreen by rememberSaveableState(false)
    var pairingScreen by rememberSaveableState(false)
    var lastAttempt by remember { mutableStateOf("") }
    var permission by remember { mutableStateOf(ContextCompat.checkSelfPermission(context, Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED) }
    val permissionLauncher = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { permission = it }
    LaunchedEffect(model.attempt, model.phase, model.connected, model.offline) {
        if (model.phase == "question" && (model.connected || model.offline) && model.attempt != lastAttempt) {
            lastAttempt = model.attempt; scanScreen = true
            if (!permission) permissionLauncher.launch(Manifest.permission.CAMERA)
        }
    }
    DisposableEffect(scanScreen) {
        val controller = WindowInsetsControllerCompat(activity.window, activity.window.decorView)
        if (scanScreen) {
            controller.systemBarsBehavior = WindowInsetsControllerCompat.BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE
            controller.hide(WindowInsetsCompat.Type.systemBars())
            activity.window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        } else { controller.show(WindowInsetsCompat.Type.systemBars()); activity.window.clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON) }
        onDispose { controller.show(WindowInsetsCompat.Type.systemBars()); activity.window.clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON) }
    }
    androidx.activity.compose.BackHandler(scanScreen) { scanScreen = false }
    if (pairingScreen) {
        androidx.activity.compose.BackHandler { pairingScreen = false }
        PairingScanner(model, permission, { permissionLauncher.launch(Manifest.permission.CAMERA) }, { pairingScreen = false })
        return
    }
    if (scanScreen) {
        ScanScreen(model, permission, { permissionLauncher.launch(Manifest.permission.CAMERA) }) { scanScreen = false }
        return
    }
    Scaffold(
        topBar = {
            Column(Modifier.statusBarsPadding().padding(horizontal = 24.dp, vertical = 16.dp)) {
                Text(listOf("课堂", "测验", "更多")[pager.currentPage], style = MaterialTheme.typography.headlineLarge, fontWeight = FontWeight.Bold)
                Text(if (model.offline) "离线课堂 · 本机保存" else if (model.connected) "已连接电脑 · 原生教师端" else "原生教师端 · 电脑尚未连接",
                    style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.primary)
            }
        },
        bottomBar = {
            NavigationBar {
                listOf("课堂", "测验", "更多").forEachIndexed { index, title ->
                    NavigationBarItem(selected = pager.currentPage == index,
                        onClick = { scope.launch { pager.animateScrollToPage(index) } },
                        icon = { Text(listOf("▦", "▤", "⋯")[index], fontSize = 24.sp) }, label = { Text(title) })
                }
            }
        }
    ) { padding ->
        HorizontalPager(pager, Modifier.padding(padding).fillMaxSize(), beyondViewportPageCount = 1) { page ->
            when (page) {
                0 -> ClassroomPage(model) { scanScreen = true; if (!permission) permissionLauncher.launch(Manifest.permission.CAMERA) }
                1 -> QuizPage(model)
                else -> MorePage(model) { pairingScreen = true; if (!permission) permissionLauncher.launch(Manifest.permission.CAMERA) }
            }
        }
    }
}

@Composable
fun <T> rememberSaveableState(initial: T): MutableState<T> = androidx.compose.runtime.saveable.rememberSaveable { mutableStateOf(initial) }

@Composable
fun ClassroomPage(model: TeacherModel, resume: () -> Unit) {
    var showMaterial by remember { mutableStateOf(false) }
    val state = model.state
    var chooseClass by remember { mutableStateOf(false) }
    LazyColumn(Modifier.fillMaxSize(), contentPadding = PaddingValues(20.dp), verticalArrangement = Arrangement.spacedBy(16.dp)) {
        item {
            Card(shape = RoundedCornerShape(28.dp), modifier = Modifier.fillMaxWidth()) {
                Column(Modifier.padding(24.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                    Text(state.optString("active_class").ifEmpty { "选择班级" }, style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
                    Text(state.optString("quiz_title", "先在测验中选择课堂内容"), style = MaterialTheme.typography.titleMedium)
                    OutlinedButton({ chooseClass = true }, enabled = !model.busy && model.phase != "question") { Text("选择班级") }
                }
            }
        }
        item {
            val q = state.optJSONObject("question")
            Text("第 ${state.optInt("index") + 1} 题 / 共 ${state.optInt("total")} 题", color = MaterialTheme.colorScheme.primary)
            if (!q?.optString("material").isNullOrBlank()) TextButton({ showMaterial = true }) { Text("查看阅读材料") }
            Text(styledText(q?.optString("text") ?: "连接后选择测验，或离线打开已缓存内容。"), style = MaterialTheme.typography.headlineSmall,
                modifier = Modifier.padding(vertical = 12.dp))
            q?.optJSONArray("answers")?.strings()?.forEachIndexed { i, answer ->
                Text("${"ABCD"[i]}  $answer", style = MaterialTheme.typography.titleLarge, modifier = Modifier.padding(vertical = 8.dp))
            }
        }
        item {
            Button(onClick = { if (model.phase == "question") resume() else model.command("start") },
                enabled = !model.busy && (model.connected || model.offline) && state.optInt("total") > 0,
                modifier = Modifier.fillMaxWidth().height(64.dp), shape = RoundedCornerShape(24.dp)) {
                Text(if (model.phase == "question") "返回全屏扫码" else "开始本题作答", fontSize = 20.sp)
            }
        }
        if (model.phase in listOf("ended", "reveal", "podium")) item { Results(model, false) }
        item { Text(model.notice, style = MaterialTheme.typography.bodyMedium) }
    }
    if (showMaterial) AlertDialog(onDismissRequest = { showMaterial = false }, title = { Text("阅读材料") },
        text = { Text(styledText(model.state.optJSONObject("question")?.optString("material").orEmpty()), Modifier.verticalScroll(rememberScrollState())) },
        confirmButton = { TextButton({ showMaterial = false }) { Text("返回题目") } })
    if (chooseClass) AlertDialog(onDismissRequest = { chooseClass = false }, title = { Text("选择作答班级") },
        text = { LazyColumn { items((if (model.offline) model.roster else model.state).optJSONArray("classes")?.strings().orEmpty()) { name ->
            TextButton({ model.selectClass(name); chooseClass = false }, Modifier.fillMaxWidth()) { Text(name, fontSize = 18.sp) }
        } } }, confirmButton = { TextButton({ chooseClass = false }) { Text("关闭") } })
}

@Composable
fun QuizPage(model: TeacherModel) {
    var chosen by remember { mutableStateOf<String?>(null) }
    val details = model.catalog.optJSONArray("details")?.objects().orEmpty()
    LazyColumn(contentPadding = PaddingValues(20.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        item { Text("选择测验开始课堂", style = MaterialTheme.typography.titleLarge) }
        if (details.isEmpty()) item { Text("暂无缓存测验。先在更多中连接电脑，同步内容后可离线使用。") }
        items(details) { detail ->
            Card(onClick = { chosen = detail.optString("name") }, shape = RoundedCornerShape(24.dp), modifier = Modifier.fillMaxWidth()) {
                Row(Modifier.padding(22.dp), verticalAlignment = Alignment.CenterVertically) {
                    Text(detail.optString("name"), style = MaterialTheme.typography.titleLarge, modifier = Modifier.weight(1f))
                    Text("${detail.optInt("question_count")} 题", color = MaterialTheme.colorScheme.primary)
                }
            }
        }
    }
    chosen?.let { name -> AlertDialog(onDismissRequest = { chosen = null }, title = { Text(name) },
        text = { Text("连接电脑时同步控制投影；离线使用会单独保存课堂记录。") },
        confirmButton = { TextButton({ model.loadQuiz(name); chosen = null }, enabled = model.connected) { Text("在电脑上开展") } },
        dismissButton = { TextButton({ model.loadQuiz(name, true); chosen = null }) { Text("离线使用") } }) }
}

@Composable
fun MorePage(model: TeacherModel, scanQr: () -> Unit) {
    val context = LocalContext.current
    val lenses = remember { runCatching { availableRearLenses(context) }.getOrDefault(emptyList()) }
    LazyColumn(Modifier.fillMaxSize().imePadding(), contentPadding = PaddingValues(20.dp), verticalArrangement = Arrangement.spacedBy(16.dp)) {
        item { Button(scanQr, Modifier.fillMaxWidth().height(60.dp), shape = RoundedCornerShape(24.dp)) { Text("扫一扫 · 连接电脑", fontSize = 19.sp) } }
        item {
            OutlinedTextField(value = model.address, onValueChange = { model.address = it }, label = { Text("电脑 IP 地址与端口") },
                placeholder = { Text("192.168.137.1:8012") }, singleLine = true, modifier = Modifier.fillMaxWidth())
        }
        item { Button({ model.connect() }, Modifier.fillMaxWidth(), enabled = !model.busy) { Text("连接并同步电脑") } }
        item { OutlinedTextField(value = model.pairCode, onValueChange = { model.pairCode = it.filter(Char::isDigit).take(6) },
            label = { Text("电脑上的六位配对码（首次手动连接时填写）") }, singleLine = true, modifier = Modifier.fillMaxWidth()) }
        item { Text(model.notice) }
        item {
            OutlinedButton({ context.startActivity(Intent(Settings.ACTION_WIFI_SETTINGS)) }, Modifier.fillMaxWidth()) { Text("打开 Wi-Fi 设置") }
            Text("可以连接电脑热点，也可以让两台设备连接同一路由器或手机热点。电脑无法开启热点时，无需强制使用电脑热点。", modifier = Modifier.padding(top = 8.dp))
        }
        item { Text("扫码镜头", style = MaterialTheme.typography.titleLarge) }
        item {
            Row(verticalAlignment = Alignment.CenterVertically) {
                RadioButton(model.cameraId.isEmpty(), { model.cameraId = ""; model.saveCamera() })
                Text("自动选择后置主摄像头")
            }
            lenses.forEach { (id, title) -> Row(verticalAlignment = Alignment.CenterVertically) {
                RadioButton(model.cameraId == id, { model.cameraId = id; model.saveCamera() }); Text(title)
            } }
        }
        item {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Switch(model.screenUp, { model.screenUp = it; model.saveCamera() })
                Text("按屏幕上方判读", Modifier.padding(start = 12.dp))
            }
            Text("默认按实际竖直方向判读，转动手机时保持选项一致。平放手机拍摄桌面卡片时，可选择按屏幕上方判读。", style = MaterialTheme.typography.bodyMedium)
        }
        item {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Switch(!model.settings.optBoolean("countdown_enabled", true), { model.setting("countdown_enabled", !it) })
                Text("课堂不限时", Modifier.padding(start = 12.dp))
            }
        }
        item { OutlinedButton({ model.restoreOffline() }, Modifier.fillMaxWidth()) { Text("恢复上次离线课堂") } }
        item { OutlinedButton({ model.uploadOffline() }, Modifier.fillMaxWidth(), enabled = model.connected && !model.busy) { Text("补传离线课堂记录") } }
        item { Text("QuizScanner 教师端 2.0.0\n原生界面 · 本地摄像头 · 本地卡片识别", color = MaterialTheme.colorScheme.primary) }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ScanScreen(model: TeacherModel, permission: Boolean, requestPermission: () -> Unit, leave: () -> Unit) {
    val context = LocalContext.current
    val owner = LocalLifecycleOwner.current
    var foreground by remember { mutableStateOf(owner.lifecycle.currentState.isAtLeast(Lifecycle.State.RESUMED)) }
    var drawer by remember { mutableStateOf("") }
    val state = model.state
    val question = state.optJSONObject("question")
    val active = model.phase == "question"
    val landscape = LocalConfiguration.current.screenWidthDp > LocalConfiguration.current.screenHeightDp
    val preview = remember { PreviewView(context).apply { scaleType = PreviewView.ScaleType.FILL_CENTER; implementationMode = PreviewView.ImplementationMode.COMPATIBLE } }
    val allowed = state.optJSONArray("live_students")?.objects().orEmpty().map { it.optInt("card_id", -1) }.toSet()
    DisposableEffect(owner) {
        val observer = LifecycleEventObserver { _, event ->
            if (event == Lifecycle.Event.ON_RESUME) foreground = true
            if (event == Lifecycle.Event.ON_PAUSE) foreground = false
        }
        owner.lifecycle.addObserver(observer)
        onDispose { owner.lifecycle.removeObserver(observer) }
    }
    DisposableEffect(model.attempt, active, permission, foreground, model.cameraId, model.screenUp, landscape) {
        val attempt = model.attempt
        val camera = if (active && permission && foreground) CardCamera(context, owner, preview, model.cameraId, model.screenUp, allowed,
            { answers -> model.detected(answers, attempt) }, { message -> model.cameraError = message }).also { model.clearCameraError(); it.start() } else null
        onDispose { camera?.close() }
    }
    LaunchedEffect(model.phase, model.attempt) {
        if (model.phase in listOf("ended", "reveal", "podium")) drawer = "graph"
        if (active) drawer = ""
    }
    Box(Modifier.fillMaxSize().background(Color(0xFF17141D))) {
        if (active && permission) AndroidView(factory = { preview }, modifier = Modifier.fillMaxSize())
        Column(Modifier.fillMaxSize().windowInsetsPadding(WindowInsets.displayCutout).padding(16.dp), verticalArrangement = Arrangement.SpaceBetween) {
            Column {
                Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                    FilledTonalButton(leave) { Text("‹ 返回") }
                    Spacer(Modifier.weight(1f))
                    Text(if (active) "正在作答" else "作答结果", color = Color.White, fontSize = 20.sp, fontWeight = FontWeight.Bold)
                    Spacer(Modifier.weight(1f))
                    Text("${state.optInt("answered")}/${state.optInt("roster_total")}", color = Color.White, fontSize = 28.sp, fontWeight = FontWeight.Bold)
                }
                Card(colors = CardDefaults.cardColors(containerColor = Color(0xD924202C)), shape = RoundedCornerShape(24.dp), modifier = Modifier.padding(top = 12.dp).fillMaxWidth()) {
                    Column(Modifier.padding(if (landscape) 12.dp else 18.dp)) {
                        Text("${state.optString("active_class")} · 第 ${state.optInt("index") + 1} / ${state.optInt("total")} 题 · ${if (!state.isNull("time_left")) "${kotlin.math.ceil(state.optDouble("time_left")).toInt()} 秒" else "不限时"}", color = Color(0xFFE4DDF2))
                        Text(styledText(question?.optString("text") ?: ""), color = Color.White, fontSize = if (landscape) 18.sp else 22.sp,
                            maxLines = if (landscape) 2 else 4, overflow = TextOverflow.Ellipsis)
                    }
                }
            }
            if (!permission) Button(requestPermission, Modifier.align(Alignment.CenterHorizontally)) { Text("允许使用摄像头") }
            if (model.cameraError.isNotBlank() && active) Text(model.cameraError, color = Color.White, modifier = Modifier.background(Color(0xD924202C)).padding(12.dp))
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceEvenly, verticalAlignment = Alignment.CenterVertically) {
                FilledTonalButton({ drawer = "graph" }) { Text("图表") }
                Button({ if (active) model.command("end") else drawer = "graph" },
                    colors = ButtonDefaults.buttonColors(containerColor = Color(0xFFE45466)),
                    modifier = Modifier.size(if (landscape) 72.dp else 88.dp), contentPadding = PaddingValues(0.dp), enabled = !model.busy) {
                    Text(if (active) "■" else "结果", fontSize = if (active) 30.sp else 18.sp)
                }
                FilledTonalButton({ drawer = "students" }) { Text("学生") }
            }
        }
        if (drawer.isNotEmpty()) ModalBottomSheet(onDismissRequest = { drawer = "" },
            sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)) {
            Column(Modifier.fillMaxWidth().heightIn(max = LocalConfiguration.current.screenHeightDp.dp * if (landscape) .86f else .78f).navigationBarsPadding().padding(horizontal = 20.dp)) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text(if (drawer == "students") "学生作答情况" else "各选项作答人数", style = MaterialTheme.typography.titleLarge, modifier = Modifier.weight(1f))
                    TextButton({ drawer = "" }) { Text("收起") }
                }
                Box(Modifier.weight(1f, fill = false)) {
                    if (drawer == "students") StudentGrid(model) else Results(model, true)
                }
                Row(Modifier.fillMaxWidth().padding(vertical = 8.dp), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    OutlinedButton({ model.command("prev_start") }, enabled = state.optInt("index") > 0 && !model.busy) { Text("上一题") }
                    Button({ if (active) model.command("end") else model.command("next_start") }, Modifier.weight(1f), enabled = !model.busy && model.phase != "podium") {
                        Text(if (active) "结束作答" else if (state.optInt("index") + 1 >= state.optInt("total")) "结束测验" else "下一题并扫码")
                    }
                }
            }
        }
    }
}

@Composable
fun StudentGrid(model: TeacherModel) {
    val live = model.state.optJSONArray("live_students")?.objects().orEmpty()
    LazyVerticalGrid(columns = GridCells.Adaptive(112.dp), contentPadding = PaddingValues(vertical = 8.dp),
        horizontalArrangement = Arrangement.spacedBy(8.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
        items(live) { student ->
            Surface(color = if (student.optBoolean("scanned")) MaterialTheme.colorScheme.secondaryContainer else MaterialTheme.colorScheme.surfaceContainerHigh,
                shape = RoundedCornerShape(16.dp)) {
                Column(Modifier.padding(12.dp)) {
                    Text(student.optString("name"), fontSize = 17.sp, fontWeight = FontWeight.Bold, maxLines = 2)
                    Text(if (student.optBoolean("scanned")) "答案 ${student.optString("answer")}" else "未作答", fontSize = 14.sp)
                }
            }
        }
    }
}

@Composable
fun Results(model: TeacherModel, scrolling: Boolean) {
    val state = model.state
    val question = state.optJSONObject("question")
    val live = state.optJSONArray("live_students")?.objects().orEmpty()
    val body: @Composable () -> Unit = {
        Text("${state.optInt("answered")} 人已作答", style = MaterialTheme.typography.titleLarge)
        for (i in 0..3) {
            val letter = "ABCD"[i].toString()
            val count = state.optJSONObject("distribution")?.optInt(letter) ?: 0
            Column(Modifier.padding(vertical = 12.dp)) {
                Row {
                    Text("$letter  ${question?.optJSONArray("answers")?.optString(i).orEmpty()}",
                        style = MaterialTheme.typography.titleMedium, modifier = Modifier.weight(1f))
                    Text(count.toString(), style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
                }
                LinearProgressIndicator(progress = { count.toFloat() / maxOf(1, state.optInt("roster_total")) }, Modifier.fillMaxWidth().padding(vertical = 8.dp))
                Text(live.filter { it.optString("answer") == letter }.joinToString("、") { it.optString("name") }.ifEmpty { "暂无学生" }, style = MaterialTheme.typography.bodyMedium)
            }
        }
        if (model.phase != "question") {
            Text("未作答：" + live.filter { !it.optBoolean("scanned") }.joinToString("、") { it.optString("name") }.ifEmpty { "无" })
            Row(verticalAlignment = Alignment.CenterVertically) {
                Checkbox(model.settings.optBoolean("show_student_answers_on_reveal", true), { model.setting("show_student_answers_on_reveal", it) })
                Text("公布时在大屏显示学生答案", style = MaterialTheme.typography.bodyMedium)
            }
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Button({ model.command("reveal") }, enabled = !model.busy && model.phase != "podium") { Text("公布正确答案") }
                OutlinedButton({ model.command("start") }, enabled = !model.busy && model.phase != "podium") { Text("重新作答") }
            }
            if (model.phase == "reveal" && question != null) Text("正确答案：${"ABCD".getOrNull(question.optInt("correct", -1)) ?: '—'}", fontSize = 20.sp)
        }
    }
    if (scrolling) Column(Modifier.fillMaxWidth().verticalScroll(rememberScrollState()).padding(bottom = 12.dp)) { body() }
    else Column(Modifier.fillMaxWidth()) { body() }
}

fun styledText(text: String) = buildAnnotatedString {
    val pattern = Regex("\\*\\*([^*]+)\\*\\*|==([^=]+)==")
    var position = 0
    for (match in pattern.findAll(text)) {
        append(text.substring(position, match.range.first))
        val bold = match.groupValues[1]
        withStyle(if (bold.isNotEmpty()) SpanStyle(fontWeight = FontWeight.Bold)
            else SpanStyle(background = Color(0xFFFFE9A8), color = Color(0xFF302A20))) {
            append(if (bold.isNotEmpty()) bold else match.groupValues[2])
        }
        position = match.range.last + 1
    }
    append(text.substring(position))
}

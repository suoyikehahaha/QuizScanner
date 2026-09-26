package cn.quizscanner.teacher

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalConfiguration
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.camera.view.PreviewView
import androidx.lifecycle.compose.LocalLifecycleOwner
import kotlinx.coroutines.launch
import kotlinx.coroutines.Dispatchers

@Composable
fun PairingScanner(model: TeacherModel, permission: Boolean, requestPermission: () -> Unit, close: () -> Unit) {
    val context = LocalContext.current
    val owner = LocalLifecycleOwner.current
    val scope = rememberCoroutineScope()
    val orientation = LocalConfiguration.current.orientation
    val preview = remember { PreviewView(context).apply { scaleType = PreviewView.ScaleType.FILL_CENTER; implementationMode = PreviewView.ImplementationMode.COMPATIBLE } }
    var accepted by remember { mutableStateOf(false) }
    DisposableEffect(permission, orientation) {
        val camera = if (permission) CardCamera(context, owner, preview, model.cameraId, true, emptySet(), {},
            { model.cameraError = it }, { payload ->
                scope.launch(Dispatchers.Main) {
                    if (!accepted && payload.startsWith("quizscanner://connect?")) {
                        accepted = true; close(); model.connectQr(payload)
                    }
                }
            }).also { it.start() } else null
        onDispose { camera?.close() }
    }
    Box(Modifier.fillMaxSize().background(Color.Black)) {
        if (permission) AndroidView(factory = { preview }, modifier = Modifier.fillMaxSize())
        Column(Modifier.fillMaxSize().safeDrawingPadding().padding(24.dp), verticalArrangement = Arrangement.SpaceBetween) {
            FilledTonalButton(close) { Text("返回") }
            Card { Column(Modifier.padding(20.dp)) {
                Text("扫描电脑连接二维码", fontSize = 22.sp)
                Text("电脑教师端点击“手机扫码连接”。请先让手机与电脑连接同一网络。")
                if (!permission) Button(requestPermission) { Text("允许使用摄像头") }
                if (model.cameraError.isNotEmpty()) Text(model.cameraError)
            } }
        }
    }
}

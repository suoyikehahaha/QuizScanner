package cn.quizscanner.teacher

import android.content.Context
import android.hardware.Sensor
import android.hardware.SensorEvent
import android.hardware.SensorEventListener
import android.hardware.SensorManager
import android.hardware.camera2.CameraCharacteristics
import android.hardware.camera2.CameraManager
import androidx.camera.camera2.interop.Camera2CameraInfo
import androidx.camera.core.*
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.camera.view.PreviewView
import androidx.core.content.ContextCompat
import androidx.lifecycle.LifecycleOwner
import org.opencv.core.*
import org.opencv.objdetect.*
import java.util.concurrent.Executors
import java.util.concurrent.atomic.AtomicBoolean
import kotlin.math.*

@androidx.annotation.OptIn(androidx.camera.camera2.interop.ExperimentalCamera2Interop::class)
class CardCamera(
    private val context: Context,
    private val lifecycle: LifecycleOwner,
    private val previewView: PreviewView,
    private val chosenId: String,
    private val useScreenUp: Boolean,
    private val allowed: Set<Int>,
    private val onDetected: (Map<Int, String>) -> Unit,
    private val onError: (String) -> Unit,
    private val onQr: ((String) -> Unit)? = null,
    private val onOverlay: (List<CardObservation>) -> Unit = {},
) : SensorEventListener {
    private val worker = Executors.newSingleThreadExecutor()
    private val sensors = context.getSystemService(Context.SENSOR_SERVICE) as SensorManager
    private val sensor = sensors.getDefaultSensor(Sensor.TYPE_GRAVITY) ?: sensors.getDefaultSensor(Sensor.TYPE_ACCELEROMETER)
    @Volatile private var gx = 0.0
    @Volatile private var gy = 9.8
    @Volatile private var closed = false
    private var provider: ProcessCameraProvider? = null
    private var preview: Preview? = null
    private var analysis: ImageAnalysis? = null
    private var camera: Camera? = null
    private var sensorOrientation = 90
    private val counts = mutableMapOf<Int, Pair<String, Int>>()
    private val sent = mutableMapOf<Int, String>()
    private var lastFrame = 0L
    private val overlayPending = AtomicBoolean(false)
    private val detector = ArucoDetector(Objdetect.getPredefinedDictionary(Objdetect.DICT_4X4_250), DetectorParameters().apply {
                set_cornerRefinementMethod(Objdetect.CORNER_REFINE_SUBPIX)
                set_errorCorrectionRate(0.35)
                set_minMarkerPerimeterRate(0.025)
            })

    fun start() {
        if (sensor != null) sensors.registerListener(this, sensor, SensorManager.SENSOR_DELAY_GAME)
        val future = ProcessCameraProvider.getInstance(context)
        future.addListener({
            if (closed) return@addListener
            try {
                val current = future.get(); provider = current
                val rear = current.availableCameraInfos.filter { it.lensFacing == CameraSelector.LENS_FACING_BACK }
                require(rear.isNotEmpty()) { "没有可用的后置摄像头" }
                require(chosenId.isEmpty() || rear.any { Camera2CameraInfo.from(it).cameraId == chosenId }) { "所选镜头无法用于实时分析，请改用主摄" }
                val selected = rear.firstOrNull { Camera2CameraInfo.from(it).cameraId == chosenId } ?: rear.first()
                val id = Camera2CameraInfo.from(selected).cameraId
                val manager = context.getSystemService(Context.CAMERA_SERVICE) as CameraManager
                sensorOrientation = manager.getCameraCharacteristics(id).get(CameraCharacteristics.SENSOR_ORIENTATION) ?: 90
                val selector = CameraSelector.Builder().addCameraFilter { infos -> infos.filter { Camera2CameraInfo.from(it).cameraId == id } }.build()
                val target = previewView.display?.rotation ?: 0
                preview = Preview.Builder().setTargetRotation(target).build().also { it.setSurfaceProvider(previewView.surfaceProvider) }
                analysis = ImageAnalysis.Builder().setTargetResolution(android.util.Size(1280, 720))
                    .setTargetRotation(target).setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST).build().also {
                        it.setAnalyzer(worker, ::analyze)
                    }
                camera = current.bindToLifecycle(lifecycle, selector, preview, analysis)
                previewView.setOnTouchListener { _, event ->
                    if (event.action == android.view.MotionEvent.ACTION_UP) {
                        val point = previewView.meteringPointFactory.createPoint(event.x, event.y)
                        camera?.cameraControl?.startFocusAndMetering(FocusMeteringAction.Builder(point).build())
                    }
                    true
                }
            } catch (error: Exception) { onError("摄像头无法启动：${error.message}，可在更多中选择其他镜头。") }
        }, ContextCompat.getMainExecutor(context))
    }

    private fun analyze(image: ImageProxy) {
        var gray: Mat? = null
        val corners = ArrayList<Mat>(); val ids = Mat()
        try {
            if (closed || System.currentTimeMillis() - lastFrame < 75) return
            lastFrame = System.currentTimeMillis()
            val plane = image.planes[0]
            val buffer = plane.buffer.duplicate()
            val bytes = ByteArray(image.width * image.height)
            for (y in 0 until image.height) for (x in 0 until image.width) {
                val offset = y * plane.rowStride + x * plane.pixelStride
                if (offset < buffer.limit()) bytes[y * image.width + x] = buffer.get(offset)
            }
            gray = Mat(image.height, image.width, CvType.CV_8UC1).also { it.put(0, 0, bytes) }
            if (onQr != null) {
                val source = com.google.zxing.PlanarYUVLuminanceSource(bytes, image.width, image.height, 0, 0, image.width, image.height, false)
                try {
                    val bitmap = com.google.zxing.BinaryBitmap(com.google.zxing.common.HybridBinarizer(source))
                    val result = com.google.zxing.MultiFormatReader().decode(bitmap,
                        mapOf(com.google.zxing.DecodeHintType.POSSIBLE_FORMATS to listOf(com.google.zxing.BarcodeFormat.QR_CODE)))
                    if (!closed) onQr.invoke(result.text)
                } catch (_: com.google.zxing.ReaderException) {}
                return
            }
            detector.detectMarkers(gray, corners, ids)
            // Camera analysis is in raw sensor coordinates. Gravity stays in the
            // device's natural coordinate system regardless of display rotation.
            val rawUp = if (useScreenUp || hypot(gx, gy) < 2.0) {
                rotate(0.0, -1.0, -image.imageInfo.rotationDegrees)
            } else rotate(gx, -gy, -sensorOrientation)
            val detections = mutableMapOf<Int, String>()
            val observations = mutableListOf<CardObservation>()
            val seen = mutableSetOf<Int>()
            for (i in 0 until ids.rows()) {
                val id = ids.get(i, 0)[0].toInt()
                if (id !in allowed) continue
                val marker = corners[i]
                var best = -Double.MAX_VALUE; var edge = 0
                for (j in 0..3) {
                    val a = marker.get(0, j); val b = marker.get(0, (j + 1) % 4)
                    val score = (a[0] + b[0]) * rawUp.first + (a[1] + b[1]) * rawUp.second
                    if (score > best) { best = score; edge = j }
                }
                val answer = "ABCD"[edge].toString(); seen.add(id)
                val previous = counts[id]
                val n = if (previous?.first == answer) previous.second + 1 else 1
                counts[id] = answer to n
                observations.add(CardObservation(id, answer, n >= 3,
                    (0..3).map { corner -> marker.get(0, corner).let { CardCorner(it[0].toFloat(), it[1].toFloat()) } }))
                if (n >= 3 && sent[id] != answer) { detections[id] = answer; sent[id] = answer }
            }
            counts.keys.retainAll(seen)
            if (!closed && detections.isNotEmpty()) onDetected(detections)
            updateOverlay(image, observations)
        } catch (error: Exception) {
            if (!closed) onError("识别失败：${error.message}")
        } finally { gray?.release(); ids.release(); corners.forEach { it.release() }; image.close() }
    }

    private fun updateOverlay(image: ImageProxy, observations: List<CardObservation>) {
        if (closed || !overlayPending.compareAndSet(false, true)) return
        // Map the raw analysis buffer through the sensor into PreviewView.
        // CameraX includes the actual preview rotation and FILL_CENTER crop;
        // this does not alter the answer's direction calculation.
        val bufferToSensor = android.graphics.Matrix()
        if (!image.imageInfo.sensorToBufferTransformMatrix.invert(bufferToSensor)) {
            overlayPending.set(false)
            return
        }
        val sensorPoints = observations.map { observation ->
            val points = observation.corners.flatMap { listOf(it.x, it.y) }.toFloatArray()
            bufferToSensor.mapPoints(points)
            observation to points
        }
        previewView.post {
            try {
                if (closed) return@post
                val sensorToView = previewView.sensorToViewTransform
                if (sensorToView == null || previewView.width == 0 || previewView.height == 0) {
                    onOverlay(emptyList())
                    return@post
                }
                onOverlay(sensorPoints.map { (observation, points) ->
                    sensorToView.mapPoints(points)
                    observation.copy(corners = (0..3).map { i ->
                        CardCorner(points[i * 2] / previewView.width, points[i * 2 + 1] / previewView.height)
                    })
                })
            } finally { overlayPending.set(false) }
        }
    }

    private fun rotate(x: Double, y: Double, degrees: Int): Pair<Double, Double> {
        val angle = Math.toRadians(degrees.toDouble())
        return (x * cos(angle) - y * sin(angle)) to (x * sin(angle) + y * cos(angle))
    }
    override fun onSensorChanged(event: SensorEvent) {
        val alpha = if (event.sensor.type == Sensor.TYPE_GRAVITY) 1.0 else 0.15
        gx += alpha * (event.values[0] - gx); gy += alpha * (event.values[1] - gy)
    }
    override fun onAccuracyChanged(sensor: Sensor?, accuracy: Int) {}
    fun close() {
        closed = true
        sensors.unregisterListener(this)
        analysis?.clearAnalyzer()
        val cases = listOfNotNull(preview, analysis).toTypedArray()
        if (cases.isNotEmpty()) provider?.unbind(*cases)
        worker.shutdown()
    }
}

fun availableRearLenses(context: Context): List<Pair<String, String>> {
    val manager = context.getSystemService(Context.CAMERA_SERVICE) as CameraManager
    return manager.cameraIdList.mapNotNull { id ->
        val info = manager.getCameraCharacteristics(id)
        if (info.get(CameraCharacteristics.LENS_FACING) != CameraCharacteristics.LENS_FACING_BACK) null
        else {
            val focal = info.get(CameraCharacteristics.LENS_INFO_AVAILABLE_FOCAL_LENGTHS)?.firstOrNull()
            id to "后置镜头 $id${focal?.let { " · ${"%.1f".format(it)} mm" } ?: ""}"
        }
    }
}

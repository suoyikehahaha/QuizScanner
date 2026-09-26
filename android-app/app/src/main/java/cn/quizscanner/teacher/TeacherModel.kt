package cn.quizscanner.teacher

import android.app.Application
import android.database.sqlite.SQLiteOpenHelper
import android.database.sqlite.SQLiteDatabase
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import androidx.compose.runtime.*
import kotlinx.coroutines.*
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import org.json.JSONArray
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URI
import java.net.URL
import java.util.UUID

fun JSONArray.objects(): List<JSONObject> = (0 until length()).mapNotNull { optJSONObject(it) }
fun JSONArray.strings(): List<String> = (0 until length()).map { optString(it) }

class ClassroomCache(app: Application): SQLiteOpenHelper(app, "classroom.db", null, 1) {
    override fun onCreate(db: SQLiteDatabase) {
        db.execSQL("CREATE TABLE cache (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        db.execSQL("CREATE TABLE events (id TEXT PRIMARY KEY, body TEXT NOT NULL)")
        db.execSQL("CREATE TABLE offline (id TEXT PRIMARY KEY, body TEXT NOT NULL)")
    }
    override fun onUpgrade(db: SQLiteDatabase, old: Int, new: Int) {}
    @Synchronized fun put(key: String, value: JSONObject) {
        writableDatabase.execSQL("INSERT OR REPLACE INTO cache VALUES (?,?)", arrayOf(key, value.toString()))
    }
    @Synchronized fun get(key: String): JSONObject? = readableDatabase.rawQuery("SELECT value FROM cache WHERE key=?", arrayOf(key)).use {
        if (it.moveToFirst()) JSONObject(it.getString(0)) else null
    }
    @Synchronized fun queue(table: String, id: String, body: JSONObject) {
        require(table == "events" || table == "offline")
        writableDatabase.execSQL("INSERT OR REPLACE INTO $table VALUES (?,?)", arrayOf(id, body.toString()))
    }
    @Synchronized fun rows(table: String): List<Pair<String, JSONObject>> {
        require(table == "events" || table == "offline")
        return readableDatabase.rawQuery("SELECT id,body FROM $table ORDER BY rowid", null).use { cursor ->
            buildList { while (cursor.moveToNext()) add(cursor.getString(0) to JSONObject(cursor.getString(1))) }
        }
    }
    @Synchronized fun remove(table: String, id: String) {
        require(table == "events" || table == "offline")
        writableDatabase.delete(table, "id=?", arrayOf(id))
    }
}

class TeacherModel(app: Application): AndroidViewModel(app) {
    private val cache = ClassroomCache(app)
    private val prefs = app.getSharedPreferences("native", 0)
    private val oldPrefs = app.getSharedPreferences("MainActivity", 0)
    var address by mutableStateOf(prefs.getString("server", oldPrefs.getString("server", "http://192.168.137.1:8012")) ?: "")
    var state by mutableStateOf(cache.get("state") ?: JSONObject())
        private set
    var roster by mutableStateOf(cache.get("roster") ?: JSONObject())
        private set
    var catalog by mutableStateOf(cache.get("catalog") ?: JSONObject())
        private set
    var settings by mutableStateOf(cache.get("settings") ?: JSONObject())
        private set
    var connected by mutableStateOf(false)
        private set
    var offline by mutableStateOf(false)
        private set
    var busy by mutableStateOf(false)
        private set
    var notice by mutableStateOf("在更多中连接电脑，也可打开已缓存的测验。")
        private set
    var cameraId by mutableStateOf(prefs.getString("camera_id", "") ?: "")
    var screenUp by mutableStateOf(prefs.getBoolean("screen_up", false))
    var cameraError by mutableStateOf("")
    var pairCode by mutableStateOf("")
    var recentScans by mutableStateOf(emptyList<RecentScan>())
        private set
    private var token = ""
    private var polling: Job? = null
    private var base = prefs.getString("base", "") ?: ""
    private val actions = Mutex()
    private var changeEpoch = 0
    private var ending = false
    val phase: String get() = state.optString("phase", "idle")
    val attempt: String get() = state.optString("attempt_id")

    private suspend fun request(path: String, body: JSONObject? = null): JSONObject = withContext(Dispatchers.IO) {
        val connection = URL(base + path).openConnection() as HttpURLConnection
        connection.connectTimeout = 3000
        connection.readTimeout = 4500
        connection.setRequestProperty("Accept", "application/json")
        if (token.isNotEmpty()) connection.setRequestProperty("X-Teacher-Token", token)
        try {
            if (body != null) {
                connection.requestMethod = "POST"
                connection.doOutput = true
                connection.setRequestProperty("Content-Type", "application/json; charset=utf-8")
                connection.outputStream.use { it.write(body.toString().toByteArray(Charsets.UTF_8)) }
            }
            val status = connection.responseCode
            val stream = if (status in 200..299) connection.inputStream else connection.errorStream
            val text = stream?.bufferedReader(Charsets.UTF_8)?.use { it.readText() } ?: ""
            val result = try { JSONObject(text) } catch (_: Exception) { JSONObject() }
            if (status !in 200..299 || result.optBoolean("ok", true) == false)
                throw IllegalStateException(result.optString("error", "电脑服务返回 HTTP $status"))
            result
        } finally { connection.disconnect() }
    }

    fun connect() {
        polling?.cancel()
        runAction {
            try {
                val input = address.trim().let { if (it.startsWith("http://") || it.startsWith("https://")) it else "http://$it" }
                val uri = URI(input)
                require(uri.scheme in listOf("http", "https")) { "地址协议无效" }
                require(!uri.host.isNullOrBlank() && uri.userInfo == null && uri.query == null) { "请输入电脑地址，例如 192.168.137.1:8012" }
                base = "${uri.scheme}://${uri.host}:${if (uri.port > 0) uri.port else 8012}"
                token = prefs.getString("token:$base", "") ?: ""
                val meta = request("/api/meta")
                require(meta.optInt("native_protocol") == 1) { "电脑端需要升级到 3.2.0 或更高版本。" }
                if (pairCode.isNotEmpty()) {
                    token = request("/api/native/pair", JSONObject().put("code", pairCode)).getString("token")
                    prefs.edit().putString("token:$base", token).apply()
                    pairCode = ""
                }
                address = base
                prefs.edit().putString("server", base).putString("base", base).apply()
                syncCatalog()
                state = request("/api/state?full=1&live=1")
                cache.put("state", state)
                offline = false
                connected = true
                notice = "已连接电脑 ${uri.host}"
                poll()
            } catch (cancel: CancellationException) { throw cancel
            } catch (error: Exception) {
                connected = false
                notice = "连接失败：${error.message}。请检查电脑服务、端口以及是否处于同一网络。"
            }
        }
    }

    fun connectQr(payload: String) {
        try {
            val uri = android.net.Uri.parse(payload)
            require(uri.scheme == "quizscanner" && uri.host == "connect") { "请扫描电脑 QuizScanner 的连接二维码" }
            address = uri.getQueryParameter("url") ?: error("二维码没有电脑地址")
            pairCode = uri.getQueryParameter("code") ?: error("二维码没有配对码")
            connect()
        } catch (error: Exception) { notice = error.message ?: "无法读取二维码" }
    }

    private suspend fun syncCatalog() {
        catalog = request("/api/quizzes"); cache.put("catalog", catalog)
        roster = request("/api/roster"); cache.put("roster", roster)
        settings = request("/api/settings"); cache.put("settings", settings)
        for (name in catalog.optJSONArray("quizzes")?.strings().orEmpty()) {
            val quiz = request("/api/quiz?name=" + java.net.URLEncoder.encode(name, "UTF-8"))
            cache.put("quiz:$name", quiz)
        }
    }

    private fun poll() {
        polling = viewModelScope.launch {
            while (isActive && !offline) {
                try {
                    val epoch = changeEpoch
                    val fresh = request("/api/native/sync?after=" + state.optLong("revision", -1))
                    if (epoch != changeEpoch) continue
                    if (fresh.optString("session_id") != state.optString("session_id") || fresh.optLong("revision") >= state.optLong("revision")) {
                        state = fresh; cache.put("state", fresh)
                        settings = JSONObject(settings.toString()).put("countdown_enabled", fresh.optBoolean("countdown_enabled", true))
                            .put("show_student_answers_on_reveal", fresh.optBoolean("show_student_answers_on_reveal", true))
                        val cachedClasses = roster.optJSONArray("classes")?.toString()
                        if (fresh.optJSONArray("classes")?.toString() != cachedClasses) {
                            roster = request("/api/roster"); cache.put("roster", roster)
                        }
                    }
                    connected = true
                    flushEvents()
                    delay(60)
                } catch (cancel: CancellationException) { throw cancel
                } catch (error: Exception) {
                    connected = false
                    notice = "连接中断，正在重连。已扫描答案保存在手机上。"
                    delay(1500)
                }
            }
        }
    }

    private suspend fun flushEvents() {
        for ((id, event) in cache.rows("events")) {
            if (event.optString("attempt_id") != attempt || event.optString("session_id") != state.optString("session_id")) {
                // Keep expired events locally for inspection; never move them into the new question.
                continue
            }
            request("/api/native/answers", event)
            cache.remove("events", id)
        }
    }

    fun command(action: String) = runAction {
        val closes = action in listOf("end", "reveal", "next_start", "prev_start")
        ending = closes
        try {
            if (offline) localCommand(action) else {
                if (closes && phase == "question") flushEvents()
                val body = JSONObject().put("action", action).put("input_source", "native").put("command_id", UUID.randomUUID().toString())
                if (attempt.isNotBlank() && attempt != "null") body.put("expected_attempt", attempt)
                state = request("/api/control", body).getJSONObject("state")
                cache.put("state", state)
            }
        } finally { ending = false }
    }

    fun selectClass(name: String) = runAction {
        if (offline) {
            require(phase != "question") { "请先结束当前题目" }
            state = JSONObject(state.toString()).put("active_class", name).put("phase", "idle")
                .put("session_id", UUID.randomUUID().toString().replace("-", "")).put("history", JSONArray())
            rebuildLocal()
        } else {
            request("/api/roster/class", JSONObject().put("class_name", name))
            state = request("/api/state?full=1&live=1")
        }
    }

    fun loadQuiz(name: String, local: Boolean = false) = runAction {
        if (local) {
            polling?.cancel(); connected = false; offline = true
            val quiz = cache.get("quiz:$name") ?: error("此测验尚未同步到手机")
            state = JSONObject().put("quiz_name", name).put("quiz_title", quiz.optString("title"))
                .put("session_id", UUID.randomUUID().toString().replace("-", ""))
                .put("active_class", roster.optString("active_class")).put("phase", "idle")
                .put("index", 0).put("total", quiz.getJSONArray("questions").length()).put("history", JSONArray())
            rebuildLocal(); notice = "离线课堂已就绪，记录可在更多中补传。"
        } else {
            require(connected) { "请先连接电脑，或选择离线使用" }
            state = request("/api/load", JSONObject().put("name", name)).getJSONObject("state")
        }
    }

    fun setting(key: String, value: Boolean) = runAction {
        settings = JSONObject(settings.toString()).put(key, value)
        if (!offline) request("/api/settings", JSONObject().put(key, value))
        cache.put("settings", settings)
    }

    fun saveCamera() { prefs.edit().putString("camera_id", cameraId).putBoolean("screen_up", screenUp).apply() }
    fun clearCameraError() { cameraError = "" }

    fun detected(answers: Map<Int, String>, capturedAttempt: String) {
        viewModelScope.launch {
            if (ending || capturedAttempt != attempt || phase != "question" || answers.isEmpty()) return@launch
            for ((cardId, answer) in answers) {
                recentScans = (listOf(RecentScan(cardId, answer, capturedAttempt)) +
                    recentScans.filter { it.attempt == capturedAttempt && it.cardId != cardId }).take(3)
            }
            val body = JSONObject().put("session_id", state.optString("session_id")).put("class_name", state.optString("active_class"))
                .put("attempt_id", attempt).put("event_id", UUID.randomUUID().toString())
                .put("captured_at", System.currentTimeMillis()).put("answers", JSONObject(answers.mapKeys { it.key.toString() }))
            if (offline) {
                val updated = JSONObject(state.toString())
                val live = updated.optJSONArray("live_students") ?: JSONArray()
                for (student in live.objects()) answers[student.optInt("card_id")]?.let {
                    student.put("answer", it).put("scanned", true)
                }
                state = updated
                rebuildLocal(false)
            } else {
                cache.queue("events", body.getString("event_id"), body)
                try { flushEvents() } catch (_: Exception) { notice = "答案已保存在手机，连接恢复后补传。" }
            }
        }
    }

    private fun localCommand(action: String) {
        var updated = JSONObject(state.toString())
        val total = updated.optInt("total")
        if (action == "end" || action == "reveal" || action.endsWith("_start")) {
            if (phase == "question") {
                val history = updated.optJSONArray("history") ?: JSONArray()
                history.put(JSONObject().put("index", updated.optInt("index")).put("answers", JSONObject().apply {
                    for (student in updated.optJSONArray("live_students")?.objects().orEmpty())
                        if (student.optBoolean("scanned")) put(student.optInt("card_id").toString(), student.optString("answer"))
                }))
                updated.put("history", history).put("phase", "ended")
            }
            if (action == "reveal") updated.put("phase", "reveal")
        }
        if (action.endsWith("_start")) {
            val index = updated.optInt("index") + if (action == "prev_start") -1 else 1
            updated.put("index", index.coerceAtLeast(0)).put("phase", if (index >= total) "podium" else "idle")
        }
        state = updated
        if (action == "start" || action.endsWith("_start") && phase != "podium") {
            require(localRoster().isNotEmpty()) { "请先选择有学生的班级" }
            state = JSONObject(state.toString()).put("phase", "question").put("attempt_id", UUID.randomUUID().toString())
            rebuildLocal(true)
        } else rebuildLocal(false)
    }

    private fun localRoster() = roster.optJSONArray("students")?.objects().orEmpty()
        .filter { it.optString("class_name") == state.optString("active_class") }

    private fun rebuildLocal(reset: Boolean = true) {
        val updated = JSONObject(state.toString())
        val quiz = cache.get("quiz:" + updated.optString("quiz_name")) ?: return
        val question = quiz.getJSONArray("questions").optJSONObject(updated.optInt("index"))
        updated.put("question", question ?: JSONObject()).put("roster_total", localRoster().size)
        if (reset) updated.put("live_students", JSONArray(localRoster().map { JSONObject(it.toString()).put("scanned", false) }))
        val distribution = JSONObject().apply { "ABCD".forEach { put(it.toString(), 0) } }
        var scanned = 0
        for (student in updated.optJSONArray("live_students")?.objects().orEmpty()) if (student.optBoolean("scanned")) {
            val answer = student.optString("answer"); distribution.put(answer, distribution.optInt(answer) + 1); scanned++
        }
        updated.put("distribution", distribution).put("answered", scanned).put("time_left", JSONObject.NULL)
        state = updated
        cache.queue("offline", updated.getString("session_id"), JSONObject().put("id", updated.getString("session_id"))
            .put("class_name", updated.optString("active_class")).put("quiz_name", updated.optString("quiz_name"))
            .put("quiz", quiz).put("roster", JSONArray(localRoster())).put("history", updated.optJSONArray("history") ?: JSONArray()))
        cache.put("offline_state", updated)
    }

    fun restoreOffline() = runAction {
        val saved = cache.get("offline_state") ?: error("尚无离线课堂记录")
        polling?.cancel(); offline = true; connected = false; state = saved
    }

    fun uploadOffline() = runAction {
        require(connected && !offline) { "请先连接电脑" }
        var count = 0
        for ((id, record) in cache.rows("offline")) {
            if (record.optJSONArray("history")?.length() == 0) continue
            request("/api/native/import", record); cache.remove("offline", id); count++
        }
        notice = "已补传 $count 个离线课堂，报告保存在电脑端。"
    }

    private fun runAction(action: suspend () -> Unit) {
        viewModelScope.launch {
            actions.withLock {
                busy = true
                changeEpoch++
                try { action() } catch (cancel: CancellationException) { throw cancel
                } catch (error: Exception) { notice = error.message ?: "操作失败" }
                finally { busy = false }
            }
        }
    }
    override fun onCleared() { polling?.cancel(); cache.close(); super.onCleared() }
}

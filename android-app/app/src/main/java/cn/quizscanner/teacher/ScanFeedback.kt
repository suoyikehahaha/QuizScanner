package cn.quizscanner.teacher

data class CardCorner(val x: Float, val y: Float)
data class CardObservation(val cardId: Int, val answer: String, val stable: Boolean, val corners: List<CardCorner>)
data class RecentScan(val cardId: Int, val answer: String, val attempt: String)
enum class ScanReceipt { READING, RECOGNIZED, SUBMITTED, OFFLINE }

fun scanReceipt(stable: Boolean, answer: String, savedAnswer: String?, scanned: Boolean, offline: Boolean): ScanReceipt {
    if (!stable) return ScanReceipt.READING
    if (scanned && savedAnswer == answer) return if (offline) ScanReceipt.OFFLINE else ScanReceipt.SUBMITTED
    return ScanReceipt.RECOGNIZED
}

fun scanReceiptText(receipt: ScanReceipt): String = when (receipt) {
    ScanReceipt.READING -> "识别中"
    ScanReceipt.RECOGNIZED -> "已识别，待提交"
    ScanReceipt.SUBMITTED -> "已提交"
    ScanReceipt.OFFLINE -> "离线已记录"
}

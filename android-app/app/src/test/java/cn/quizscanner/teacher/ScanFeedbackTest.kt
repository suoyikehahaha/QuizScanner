package cn.quizscanner.teacher

import org.junit.Assert.assertEquals
import org.junit.Test

class ScanFeedbackTest {
    @Test fun unstableCardIsStillBeingRead() {
        assertEquals(ScanReceipt.READING, scanReceipt(false,"A","A",true,false))
    }
    @Test fun stableAnswerWaitsForComputerConfirmation() {
        assertEquals(ScanReceipt.RECOGNIZED, scanReceipt(true,"A",null,false,false))
    }
    @Test fun changingAnswerDoesNotReusePreviousReceipt() {
        assertEquals(ScanReceipt.RECOGNIZED, scanReceipt(true,"B","A",true,false))
    }
    @Test fun matchingComputerAnswerIsSubmitted() {
        assertEquals(ScanReceipt.SUBMITTED, scanReceipt(true,"A","A",true,false))
    }
    @Test fun offlineRecordingIsNotComputerSubmission() {
        assertEquals(ScanReceipt.OFFLINE, scanReceipt(true,"A","A",true,true))
    }
}

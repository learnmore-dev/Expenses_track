package com.lmt.telecallersync

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.telephony.TelephonyManager

class CallReceiver : BroadcastReceiver() {

    companion object {
        var lastState = TelephonyManager.CALL_STATE_IDLE
        var isIncoming = false
        var savedNumber: String? = null
        var callStartTime: Long = 0
    }

    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action == Intent.ACTION_NEW_OUTGOING_CALL) {
            savedNumber = intent.extras?.getString("android.intent.extra.PHONE_NUMBER")
        } else {
            val stateStr = intent.extras?.getString(TelephonyManager.EXTRA_STATE)
            val number = intent.extras?.getString(TelephonyManager.EXTRA_INCOMING_NUMBER)

            if (stateStr == null) return

            var state = TelephonyManager.CALL_STATE_IDLE
            if (stateStr == TelephonyManager.EXTRA_STATE_RINGING) {
                state = TelephonyManager.CALL_STATE_RINGING
            } else if (stateStr == TelephonyManager.EXTRA_STATE_OFFHOOK) {
                state = TelephonyManager.CALL_STATE_OFFHOOK
            }

            onCallStateChanged(context, state, number)
        }
    }

    private fun onCallStateChanged(context: Context, state: Int, number: String?) {
        if (lastState == state) return

        when (state) {
            TelephonyManager.CALL_STATE_RINGING -> {
                isIncoming = true
                savedNumber = number
            }
            TelephonyManager.CALL_STATE_OFFHOOK -> {
                callStartTime = System.currentTimeMillis()
                val intent = Intent(context, AudioRecorderService::class.java).apply {
                    putExtra("action", "START")
                    putExtra("number", savedNumber ?: "Unknown")
                    putExtra("call_type", if (isIncoming) "INCOMING" else "OUTGOING")
                }
                context.startService(intent)
            }
            TelephonyManager.CALL_STATE_IDLE -> {
                if (lastState == TelephonyManager.CALL_STATE_OFFHOOK) {
                    val durationSeconds = ((System.currentTimeMillis() - callStartTime) / 1000).toInt()
                    val intent = Intent(context, AudioRecorderService::class.java).apply {
                        putExtra("action", "STOP")
                        putExtra("number", savedNumber ?: "Unknown")
                        putExtra("duration", durationSeconds)
                        putExtra("call_type", if (isIncoming) "INCOMING" else "OUTGOING")
                    }
                    context.startService(intent)
                } else if (lastState == TelephonyManager.CALL_STATE_RINGING) {
                    // Missed Call!
                    val intent = Intent(context, AudioRecorderService::class.java).apply {
                        putExtra("action", "MISSED")
                        putExtra("number", savedNumber ?: "Unknown")
                        putExtra("duration", 0)
                        putExtra("call_type", "MISSED")
                    }
                    context.startService(intent)
                }
                isIncoming = false
            }
        }
        lastState = state
    }
}

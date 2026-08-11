package com.lmt.telecallersync

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.provider.CallLog
import android.telephony.TelephonyManager
import androidx.core.content.ContextCompat

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

        if (!number.isNullOrEmpty()) {
            savedNumber = number
        }

        when (state) {
            TelephonyManager.CALL_STATE_RINGING -> {
                isIncoming = true
                if (!number.isNullOrEmpty()) savedNumber = number
            }
            TelephonyManager.CALL_STATE_OFFHOOK -> {
                callStartTime = System.currentTimeMillis()
                val targetNumber = savedNumber ?: getLatestCallLogNumber(context) ?: "Unknown Number"
                val serviceIntent = Intent(context, AudioRecorderService::class.java).apply {
                    putExtra("action", "START")
                    putExtra("number", targetNumber)
                    putExtra("call_type", if (isIncoming) "INCOMING" else "OUTGOING")
                }
                try {
                    ContextCompat.startForegroundService(context, serviceIntent)
                } catch (e: Exception) {
                    context.startService(serviceIntent)
                }
            }
            TelephonyManager.CALL_STATE_IDLE -> {
                val targetNumber = savedNumber ?: getLatestCallLogNumber(context) ?: "Unknown Number"
                if (lastState == TelephonyManager.CALL_STATE_OFFHOOK) {
                    val durationSeconds = ((System.currentTimeMillis() - callStartTime) / 1000).toInt()
                    val serviceIntent = Intent(context, AudioRecorderService::class.java).apply {
                        putExtra("action", "STOP")
                        putExtra("number", targetNumber)
                        putExtra("duration", durationSeconds)
                        putExtra("call_type", if (isIncoming) "INCOMING" else "OUTGOING")
                    }
                    try {
                        ContextCompat.startForegroundService(context, serviceIntent)
                    } catch (e: Exception) {
                        context.startService(serviceIntent)
                    }
                } else if (lastState == TelephonyManager.CALL_STATE_RINGING) {
                    val serviceIntent = Intent(context, AudioRecorderService::class.java).apply {
                        putExtra("action", "MISSED")
                        putExtra("number", targetNumber)
                        putExtra("duration", 0)
                        putExtra("call_type", "MISSED")
                    }
                    try {
                        ContextCompat.startForegroundService(context, serviceIntent)
                    } catch (e: Exception) {
                        context.startService(serviceIntent)
                    }
                }
                isIncoming = false
                savedNumber = null
            }
        }
        lastState = state
    }

    private fun getLatestCallLogNumber(context: Context): String? {
        try {
            val cursor = context.contentResolver.query(
                CallLog.Calls.CONTENT_URI,
                arrayOf(CallLog.Calls.NUMBER),
                null,
                null,
                "${CallLog.Calls.DATE} DESC"
            )
            cursor?.use {
                if (it.moveToFirst()) {
                    return it.getString(it.getColumnIndexOrThrow(CallLog.Calls.NUMBER))
                }
            }
        } catch (e: Exception) {
            e.printStackTrace()
        }
        return null
    }
}

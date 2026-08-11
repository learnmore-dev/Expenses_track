package com.lmt.telecallersync

import android.app.Service
import android.content.Context
import android.content.Intent
import android.media.MediaRecorder
import android.os.IBinder
import java.io.File

class AudioRecorderService : Service() {

    private var mediaRecorder: MediaRecorder? = null
    private var audioFile: File? = null

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        val action = intent?.getStringExtra("action") ?: return START_NOT_STICKY
        val number = intent.getStringExtra("number") ?: "Unknown"
        val callType = intent.getStringExtra("call_type") ?: "OUTGOING"
        val duration = intent.getIntExtra("duration", 0)

        when (action) {
            "START" -> startRecording()
            "STOP" -> {
                stopRecording()
                uploadAudio(number, callType, duration)
            }
            "MISSED" -> {
                uploadMissedCall(number)
            }
        }
        return START_NOT_STICKY
    }

    private fun startRecording() {
        try {
            val dir = File(externalCacheDir, "recordings")
            if (!dir.exists()) dir.mkdirs()

            audioFile = File(dir, "rec_${System.currentTimeMillis()}.m4a")

            mediaRecorder = MediaRecorder().apply {
                // Use MIC source for maximum compatibility across Android 10, 11, 12, 13, 14
                try {
                    setAudioSource(MediaRecorder.AudioSource.MIC)
                } catch (e: Exception) {
                    setAudioSource(MediaRecorder.AudioSource.VOICE_COMMUNICATION)
                }
                setOutputFormat(MediaRecorder.OutputFormat.MPEG_4)
                setAudioEncoder(MediaRecorder.AudioEncoder.AAC)
                setAudioSamplingRate(44100)
                setAudioEncodingBitRate(96000)
                setOutputFile(audioFile!!.absolutePath)
                prepare()
                start()
            }
        } catch (e: Exception) {
            e.printStackTrace()
        }
    }

    private fun stopRecording() {
        try {
            mediaRecorder?.stop()
            mediaRecorder?.release()
            mediaRecorder = null
        } catch (e: Exception) {
            e.printStackTrace()
        }
    }

    private fun uploadAudio(number: String, callType: String, duration: Int) {
        val prefs = getSharedPreferences("LMTSyncPrefs", Context.MODE_PRIVATE)
        val baseUrl = prefs.getString("server_url", "http://192.168.1.27:8000") ?: "http://192.168.1.27:8000"
        val username = prefs.getString("username", "Abhishek") ?: "Abhishek"

        if (audioFile != null && audioFile!!.exists()) {
            UploaderWorker.enqueueUpload(
                context = this,
                serverUrl = "$baseUrl/api/upload-call-recording/",
                username = username,
                number = number,
                callType = callType,
                durationSeconds = duration,
                filePath = audioFile!!.absolutePath
            )
        }
    }

    private fun uploadMissedCall(number: String) {
        val prefs = getSharedPreferences("LMTSyncPrefs", Context.MODE_PRIVATE)
        val baseUrl = prefs.getString("server_url", "http://192.168.1.27:8000") ?: "http://192.168.1.27:8000"
        val username = prefs.getString("username", "Abhishek") ?: "Abhishek"

        UploaderWorker.enqueueMissedCall(
            context = this,
            serverUrl = "$baseUrl/api/upload-call-recording/",
                username = username,
                number = number
        )
    }
}

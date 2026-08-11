package com.lmt.telecallersync

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Context
import android.content.Intent
import android.media.AudioManager
import android.media.MediaRecorder
import android.os.Build
import android.os.IBinder
import androidx.core.app.NotificationCompat
import java.io.File

class AudioRecorderService : Service() {

    private var mediaRecorder: MediaRecorder? = null
    private var audioFile: File? = null
    private var audioManager: AudioManager? = null
    private var originalAudioMode: Int = AudioManager.MODE_NORMAL

    companion object {
        private const val CHANNEL_ID = "LMT_CALL_SYNC_CHANNEL"
        private const val NOTIF_ID = 999
    }

    override fun onCreate() {
        super.onCreate()
        audioManager = getSystemService(Context.AUDIO_SERVICE) as AudioManager
        createNotificationChannel()
        startForeground(NOTIF_ID, createNotification("Monitoring Phone Call Sync..."))
    }

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

            // Standard MP3 extension for WhatsApp and VLC compatibility
            audioFile = File(dir, "rec_${System.currentTimeMillis()}.mp3")

            // Enable in-call audio routing in AudioManager to bypass hardware mic lock
            try {
                if (audioManager != null) {
                    originalAudioMode = audioManager!!.mode
                    audioManager!!.mode = AudioManager.MODE_IN_CALL
                }
            } catch (e: Exception) {
                e.printStackTrace()
            }

            val audioSources = intArrayOf(
                MediaRecorder.AudioSource.VOICE_COMMUNICATION, // Dual-way VoIP / Call stream
                MediaRecorder.AudioSource.MIC,
                MediaRecorder.AudioSource.VOICE_RECOGNITION,
                MediaRecorder.AudioSource.CAMCORDER,
                MediaRecorder.AudioSource.DEFAULT
            )

            for (source in audioSources) {
                try {
                    mediaRecorder = MediaRecorder().apply {
                        setAudioSource(source)
                        setOutputFormat(MediaRecorder.OutputFormat.MPEG_4)
                        setAudioEncoder(MediaRecorder.AudioEncoder.AAC)
                        setAudioSamplingRate(44100)
                        setAudioEncodingBitRate(128000)
                        setOutputFile(audioFile!!.absolutePath)
                        prepare()
                        start()
                    }
                    println("Successfully started MediaRecorder with audio source: $source")
                    break
                } catch (e: Exception) {
                    e.printStackTrace()
                    mediaRecorder?.release()
                    mediaRecorder = null
                }
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
        } finally {
            try {
                if (audioManager != null) {
                    audioManager!!.mode = originalAudioMode
                }
            } catch (e: Exception) {
                e.printStackTrace()
            }
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

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                "Phone Call Sync Service",
                NotificationManager.IMPORTANCE_LOW
            )
            val manager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
            manager.createNotificationChannel(channel)
        }
    }

    private fun createNotification(contentText: String): Notification {
        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("LMT Telecaller Sync")
            .setContentText(contentText)
            .setSmallIcon(android.R.drawable.ic_menu_call)
            .setPriority(NotificationCompat.PRIORITY_LOW)
            .setOngoing(true)
            .build()
    }
}

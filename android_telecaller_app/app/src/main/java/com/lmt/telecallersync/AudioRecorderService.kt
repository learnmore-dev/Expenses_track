package com.lmt.telecallersync

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Context
import android.content.Intent
import android.media.AudioFormat
import android.media.AudioManager
import android.media.AudioRecord
import android.media.MediaRecorder
import android.os.Build
import android.os.IBinder
import androidx.core.app.NotificationCompat
import java.io.File
import java.io.FileOutputStream
import java.io.RandomAccessFile

class AudioRecorderService : Service() {

    private var audioRecord: AudioRecord? = null
    private var isRecording = false
    private var recordingThread: Thread? = null
    private var wavFile: File? = null
    private var audioManager: AudioManager? = null

    companion object {
        private const val CHANNEL_ID = "LMT_CALL_SYNC_CHANNEL"
        private const val NOTIF_ID = 999
        private const val SAMPLE_RATE = 44100
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
            "START" -> startWavRecording()
            "STOP" -> {
                stopWavRecording()
                uploadAudio(number, callType, duration)
            }
            "MISSED" -> {
                uploadMissedCall(number)
            }
        }
        return START_NOT_STICKY
    }

    private fun startWavRecording() {
        if (isRecording) return

        val dir = File(externalCacheDir, "recordings")
        if (!dir.exists()) dir.mkdirs()

        wavFile = File(dir, "rec_${System.currentTimeMillis()}.wav")

        val channelConfig = AudioFormat.CHANNEL_IN_MONO
        val audioFormat = AudioFormat.ENCODING_PCM_16BIT
        val minBufferSize = AudioRecord.getMinBufferSize(SAMPLE_RATE, channelConfig, audioFormat)
        val bufferSize = Math.max(minBufferSize, 8192)

        try {
            if (audioManager != null) {
                audioManager!!.mode = AudioManager.MODE_IN_CALL
                audioManager!!.isSpeakerphoneOn = true
            }
        } catch (e: Exception) {
            e.printStackTrace()
        }

        val sources = intArrayOf(
            MediaRecorder.AudioSource.MIC,
            MediaRecorder.AudioSource.VOICE_RECOGNITION,
            MediaRecorder.AudioSource.VOICE_COMMUNICATION,
            MediaRecorder.AudioSource.CAMCORDER,
            MediaRecorder.AudioSource.DEFAULT
        )

        for (source in sources) {
            try {
                val record = AudioRecord(source, SAMPLE_RATE, channelConfig, audioFormat, bufferSize)
                if (record.state == AudioRecord.STATE_INITIALIZED) {
                    audioRecord = record
                    println("AudioRecord initialized successfully with source: $source")
                    break
                }
            } catch (e: Exception) {
                e.printStackTrace()
            }
        }

        if (audioRecord == null) return

        isRecording = true
        audioRecord?.startRecording()

        recordingThread = Thread {
            writeAudioDataToWavFile(bufferSize)
        }
        recordingThread?.start()
    }

    private fun writeAudioDataToWavFile(bufferSize: Int) {
        val data = ByteArray(bufferSize)
        var os: FileOutputStream? = null

        try {
            os = FileOutputStream(wavFile)
            writeWavHeader(os, 0, 0, SAMPLE_RATE, 1, 16)

            var totalAudioLen = 0L

            while (isRecording) {
                val read = audioRecord?.read(data, 0, data.size) ?: 0
                if (read > 0) {
                    os.write(data, 0, read)
                    totalAudioLen += read
                }
            }

            os.close()
            os = null

            if (wavFile != null && wavFile!!.exists()) {
                updateWavHeader(wavFile!!, totalAudioLen)
            }
        } catch (e: Exception) {
            e.printStackTrace()
        } finally {
            try {
                os?.close()
            } catch (e: Exception) {
                e.printStackTrace()
            }
        }
    }

    private fun stopWavRecording() {
        if (!isRecording) return

        isRecording = false
        try {
            audioRecord?.stop()
            audioRecord?.release()
            audioRecord = null
            recordingThread?.join(1000)
        } catch (e: Exception) {
            e.printStackTrace()
        } finally {
            try {
                if (audioManager != null) {
                    audioManager!!.isSpeakerphoneOn = false
                    audioManager!!.mode = AudioManager.MODE_NORMAL
                }
            } catch (e: Exception) {
                e.printStackTrace()
            }
        }
    }

    private fun writeWavHeader(
        out: FileOutputStream,
        totalAudioLen: Long,
        totalDataLen: Long,
        longSampleRate: Int,
        channels: Int,
        byteRate: Int
    ) {
        val header = ByteArray(44)
        val bitsPerSample = 16
        val sampleRate = longSampleRate.toLong()
        val calculatedByteRate = (sampleRate * channels * bitsPerSample / 8)

        header[0] = 'R'.code.toByte()
        header[1] = 'I'.code.toByte()
        header[2] = 'F'.code.toByte()
        header[3] = 'F'.code.toByte()
        header[4] = (totalDataLen and 0xffL).toByte()
        header[5] = (totalDataLen shr 8 and 0xffL).toByte()
        header[6] = (totalDataLen shr 16 and 0xffL).toByte()
        header[7] = (totalDataLen shr 24 and 0xffL).toByte()
        header[8] = 'W'.code.toByte()
        header[9] = 'A'.code.toByte()
        header[10] = 'V'.code.toByte()
        header[11] = 'E'.code.toByte()
        header[12] = 'f'.code.toByte()
        header[13] = 'm'.code.toByte()
        header[14] = 't'.code.toByte()
        header[15] = ' '.code.toByte()
        header[16] = 16
        header[17] = 0
        header[18] = 0
        header[19] = 0
        header[20] = 1
        header[21] = 0
        header[22] = channels.toByte()
        header[23] = 0
        header[24] = (sampleRate and 0xffL).toByte()
        header[25] = (sampleRate shr 8 and 0xffL).toByte()
        header[26] = (sampleRate shr 16 and 0xffL).toByte()
        header[27] = (sampleRate shr 24 and 0xffL).toByte()
        header[28] = (calculatedByteRate and 0xffL).toByte()
        header[29] = (calculatedByteRate shr 8 and 0xffL).toByte()
        header[30] = (calculatedByteRate shr 16 and 0xffL).toByte()
        header[31] = (calculatedByteRate shr 24 and 0xffL).toByte()
        header[32] = (channels * bitsPerSample / 8).toByte()
        header[33] = 0
        header[34] = bitsPerSample.toByte()
        header[35] = 0
        header[36] = 'd'.code.toByte()
        header[37] = 'a'.code.toByte()
        header[38] = 't'.code.toByte()
        header[39] = 'a'.code.toByte()
        header[40] = (totalAudioLen and 0xffL).toByte()
        header[41] = (totalAudioLen shr 8 and 0xffL).toByte()
        header[42] = (totalAudioLen shr 16 and 0xffL).toByte()
        header[43] = (totalAudioLen shr 24 and 0xffL).toByte()

        out.write(header, 0, 44)
    }

    private fun updateWavHeader(wavFile: File, totalAudioLen: Long) {
        val totalDataLen = totalAudioLen + 36
        val sampleRate = SAMPLE_RATE.toLong()
        val channels = 1
        val bitsPerSample = 16
        val calculatedByteRate = (sampleRate * channels * bitsPerSample / 8)

        val header = ByteArray(44)
        header[0] = 'R'.code.toByte()
        header[1] = 'I'.code.toByte()
        header[2] = 'F'.code.toByte()
        header[3] = 'F'.code.toByte()
        header[4] = (totalDataLen and 0xffL).toByte()
        header[5] = (totalDataLen shr 8 and 0xffL).toByte()
        header[6] = (totalDataLen shr 16 and 0xffL).toByte()
        header[7] = (totalDataLen shr 24 and 0xffL).toByte()
        header[8] = 'W'.code.toByte()
        header[9] = 'A'.code.toByte()
        header[10] = 'V'.code.toByte()
        header[11] = 'E'.code.toByte()
        header[12] = 'f'.code.toByte()
        header[13] = 'm'.code.toByte()
        header[14] = 't'.code.toByte()
        header[15] = ' '.code.toByte()
        header[16] = 16
        header[17] = 0
        header[18] = 0
        header[19] = 0
        header[20] = 1
        header[21] = 0
        header[22] = channels.toByte()
        header[23] = 0
        header[24] = (sampleRate and 0xffL).toByte()
        header[25] = (sampleRate shr 8 and 0xffL).toByte()
        header[26] = (sampleRate shr 16 and 0xffL).toByte()
        header[27] = (sampleRate shr 24 and 0xffL).toByte()
        header[28] = (calculatedByteRate and 0xffL).toByte()
        header[29] = (calculatedByteRate shr 8 and 0xffL).toByte()
        header[30] = (calculatedByteRate shr 16 and 0xffL).toByte()
        header[31] = (calculatedByteRate shr 24 and 0xffL).toByte()
        header[32] = (channels * bitsPerSample / 8).toByte()
        header[33] = 0
        header[34] = bitsPerSample.toByte()
        header[35] = 0
        header[36] = 'd'.code.toByte()
        header[37] = 'a'.code.toByte()
        header[38] = 't'.code.toByte()
        header[39] = 'a'.code.toByte()
        header[40] = (totalAudioLen and 0xffL).toByte()
        header[41] = (totalAudioLen shr 8 and 0xffL).toByte()
        header[42] = (totalAudioLen shr 16 and 0xffL).toByte()
        header[43] = (totalAudioLen shr 24 and 0xffL).toByte()

        var raf: RandomAccessFile? = null
        try {
            raf = RandomAccessFile(wavFile, "rw")
            raf.seek(0)
            raf.write(header)
        } catch (e: Exception) {
            e.printStackTrace()
        } finally {
            try {
                raf?.close()
            } catch (e: Exception) {
                e.printStackTrace()
            }
        }
    }

    private fun uploadAudio(number: String, callType: String, duration: Int) {
        val prefs = getSharedPreferences("LMTSyncPrefs", Context.MODE_PRIVATE)
        val baseUrl = prefs.getString("server_url", "http://192.168.1.27:8000") ?: "http://192.168.1.27:8000"
        val username = prefs.getString("username", "Abhishek") ?: "Abhishek"

        if (wavFile != null && wavFile!!.exists()) {
            UploaderWorker.enqueueUpload(
                context = this,
                serverUrl = "$baseUrl/api/upload-call-recording/",
                username = username,
                number = number,
                callType = callType,
                durationSeconds = duration,
                filePath = wavFile!!.absolutePath
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

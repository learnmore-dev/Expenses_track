package com.lmt.telecallersync

import android.content.Context
import okhttp3.*
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import java.io.File
import java.io.IOException

object UploaderWorker {

    fun enqueueUpload(
        context: Context,
        serverUrl: String,
        username: String,
        number: String,
        callType: String,
        durationSeconds: Int,
        filePath: String
    ) {
        val file = File(filePath)
        if (!file.exists()) return

        val client = OkHttpClient()

        val mimeType = if (file.name.endsWith(".mp3")) "audio/mpeg" else "audio/mp4"

        val requestBody = MultipartBody.Builder()
            .setType(MultipartBody.FORM)
            .addFormDataPart("telecaller_username", username)
            .addFormDataPart("phone_number", number)
            .addFormDataPart("call_type", callType)
            .addFormDataPart("duration_seconds", durationSeconds.toString())
            .addFormDataPart(
                "audio_file", file.name,
                RequestBody.create(mimeType.toMediaTypeOrNull(), file)
            )
            .build()

        val request = Request.Builder()
            .url(serverUrl)
            .post(requestBody)
            .build()

        client.newCall(request).enqueue(object : Callback {
            override fun onFailure(call: Call, e: IOException) {
                e.printStackTrace()
            }

            override fun onResponse(call: Call, response: Response) {
                if (response.isSuccessful) {
                    println("Upload Success: ${response.body?.string()}")
                    file.delete() // Delete temporary audio file after successful sync
                }
            }
        })
    }

    fun enqueueMissedCall(
        context: Context,
        serverUrl: String,
        username: String,
        number: String
    ) {
        val client = OkHttpClient()

        val requestBody = MultipartBody.Builder()
            .setType(MultipartBody.FORM)
            .addFormDataPart("telecaller_username", username)
            .addFormDataPart("phone_number", number)
            .addFormDataPart("call_type", "MISSED")
            .addFormDataPart("duration_seconds", "0")
            .build()

        val request = Request.Builder()
            .url(serverUrl)
            .post(requestBody)
            .build()

        client.newCall(request).enqueue(object : Callback {
            override fun onFailure(call: Call, e: IOException) {
                e.printStackTrace()
            }

            override fun onResponse(call: Call, response: Response) {
                if (response.isSuccessful) {
                    println("Missed Call Logged Successfully")
                }
            }
        })
    }
}

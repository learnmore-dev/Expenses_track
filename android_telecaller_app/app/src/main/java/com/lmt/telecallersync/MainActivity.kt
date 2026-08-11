package com.lmt.telecallersync

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.os.Bundle
import android.widget.Button
import android.widget.EditText
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat

class MainActivity : AppCompatActivity() {

    private lateinit var etServerUrl: EditText
    private lateinit var etUsername: EditText
    private lateinit var btnSave: Button

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        etServerUrl = findViewById(R.id.etServerUrl)
        etUsername = findViewById(R.id.etUsername)
        btnSave = findViewById(R.id.btnSave)

        val prefs = getSharedPreferences("LMTSyncPrefs", Context.MODE_PRIVATE)
        etServerUrl.setText(prefs.getString("server_url", "http://192.168.1.15:8000"))
        etUsername.setText(prefs.getString("username", "Abhishek"))

        requestPermissionsIfRequired()

        btnSave.setOnClickListener {
            val url = etServerUrl.text.toString().trim()
            val user = etUsername.text.toString().trim()

            if (url.isEmpty() || user.isEmpty()) {
                Toast.makeText(this, "Please enter both Server URL and Username", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }

            prefs.edit()
                .putString("server_url", url)
                .putString("username", user)
                .apply()

            Toast.makeText(this, "Settings Saved! Background Silent Sync Active.", Toast.LENGTH_LONG).show()
            finish()
        }
    }

    private fun requestPermissionsIfRequired() {
        val permissions = arrayOf(
            Manifest.permission.RECORD_AUDIO,
            Manifest.permission.READ_PHONE_STATE,
            Manifest.permission.READ_CALL_LOG,
            Manifest.permission.WRITE_EXTERNAL_STORAGE,
            Manifest.permission.READ_EXTERNAL_STORAGE
        )

        val needed = permissions.filter {
            ContextCompat.checkSelfPermission(this, it) != PackageManager.PERMISSION_GRANTED
        }

        if (needed.isNotEmpty()) {
            ActivityCompat.requestPermissions(this, needed.toTypedArray(), 101)
        }
    }
}

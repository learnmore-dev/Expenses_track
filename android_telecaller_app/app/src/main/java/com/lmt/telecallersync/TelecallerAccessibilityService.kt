package com.lmt.telecallersync

import android.accessibilityservice.AccessibilityService
import android.view.accessibility.AccessibilityEvent

class TelecallerAccessibilityService : AccessibilityService() {

    override fun onAccessibilityEvent(event: AccessibilityEvent?) {
        // Event processing for call state detection if needed
    }

    override fun onInterrupt() {}

    override fun onServiceConnected() {
        super.onServiceConnected()
        println("LMT Telecaller Accessibility Service Connected Successfully!")
    }
}

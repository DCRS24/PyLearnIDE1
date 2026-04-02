package com.pylearn.ide

import android.annotation.SuppressLint
import android.os.Bundle
import android.webkit.JavascriptInterface
import android.webkit.WebView
import android.webkit.WebViewClient
import android.webkit.WebChromeClient
import androidx.appcompat.app.AppCompatActivity
import com.chaquo.python.Python
import com.chaquo.python.android.AndroidPlatform
import org.json.JSONObject

class MainActivity : AppCompatActivity() {

    private lateinit var webView: WebView

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // ── Start Chaquopy Python runtime ──────────────────────────
        if (!Python.isStarted()) {
            Python.start(AndroidPlatform(this))
        }

        setContentView(R.layout.activity_main)
        webView = findViewById(R.id.webview)

        // ── WebView config ─────────────────────────────────────────
        webView.settings.apply {
            javaScriptEnabled = true
            domStorageEnabled = true
            allowFileAccessFromFileURLs = true
            allowUniversalAccessFromFileURLs = true
            databaseEnabled = true
            loadWithOverviewMode = true
            useWideViewPort = true
            setSupportZoom(false)
            builtInZoomControls = false
        }

        // ── Inject Python bridge into JS ───────────────────────────
        webView.addJavascriptInterface(PythonBridge(), "AndroidPython")

        webView.webViewClient = object : WebViewClient() {
            override fun onPageFinished(view: WebView, url: String) {
                // Tell the JS app that native Python is available
                webView.evaluateJavascript("window.__NATIVE_PYTHON__ = true;", null)
            }
        }

        webView.webChromeClient = WebChromeClient()

        // ── Load the app from assets ───────────────────────────────
        webView.loadUrl("file:///android_asset/www/index.html")
    }

    override fun onBackPressed() {
        if (webView.canGoBack()) webView.goBack()
        else super.onBackPressed()
    }

    // ── Python Bridge: called from JavaScript ─────────────────────
    inner class PythonBridge {

        private val py = Python.getInstance()
        private val runner by lazy { py.getModule("pylearn_runner") }

        /** Run Python code, return JSON {output, errors, success} */
        @JavascriptInterface
        fun runCode(code: String): String {
            return try {
                runner.callAttr("run_code", code).toString()
            } catch (e: Exception) {
                """{"output":"","errors":"${e.message?.replace("\"","'")}","success":false}"""
            }
        }

        /** pip install a package, return JSON {success, output, error} */
        @JavascriptInterface
        fun pipInstall(packageName: String): String {
            return try {
                runner.callAttr("pip_install", packageName).toString()
            } catch (e: Exception) {
                """{"success":false,"output":"","error":"${e.message?.replace("\"","'")}"}"""
            }
        }

        /** pip install multiple packages space-separated */
        @JavascriptInterface
        fun pipInstallMultiple(packages: String): String {
            return try {
                runner.callAttr("pip_install_multiple", packages).toString()
            } catch (e: Exception) {
                """{"success":false,"output":"","error":"${e.message?.replace("\"","'")}"}"""
            }
        }

        /** List installed packages, return JSON array */
        @JavascriptInterface
        fun pipList(): String {
            return try {
                runner.callAttr("pip_list").toString()
            } catch (e: Exception) {
                "[]"
            }
        }

        /** Get Python version string */
        @JavascriptInterface
        fun pythonVersion(): String {
            return try {
                runner.callAttr("python_version").toString()
            } catch (e: Exception) {
                "Python 3.12 (Chaquopy)"
            }
        }

        /** Check if a package is importable */
        @JavascriptInterface
        fun canImport(packageName: String): String {
            return try {
                runner.callAttr("can_import", packageName).toString()
            } catch (e: Exception) {
                "false"
            }
        }

        /** Run pygame demo (renders to surface, captures as PNG base64) */
        @JavascriptInterface
        fun runPygameCode(code: String): String {
            return try {
                runner.callAttr("run_pygame_headless", code).toString()
            } catch (e: Exception) {
                """{"output":"","errors":"${e.message?.replace("\"","'")}","success":false}"""
            }
        }
    }
}

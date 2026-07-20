package com.calibreweb.reader.data

import android.content.Context
import okhttp3.Credentials

/**
 * Persists the Calibre-Web server connection details.
 *
 * Note: credentials are stored in SharedPreferences (app-private storage). For a
 * hardened build you would swap this for EncryptedSharedPreferences; it is kept
 * plain here to avoid the extra dependency and its Keystore edge cases.
 */
class SettingsStore(context: Context) {

    private val prefs = context.getSharedPreferences("calibre_settings", Context.MODE_PRIVATE)

    var serverUrl: String
        get() = prefs.getString(KEY_URL, "").orEmpty()
        set(value) = prefs.edit().putString(KEY_URL, normalizeUrl(value)).apply()

    var username: String
        get() = prefs.getString(KEY_USER, "").orEmpty()
        set(value) = prefs.edit().putString(KEY_USER, value.trim()).apply()

    var password: String
        get() = prefs.getString(KEY_PASS, "").orEmpty()
        set(value) = prefs.edit().putString(KEY_PASS, value).apply()

    /** Android KeyChain alias for the optional client certificate used by mTLS. */
    var clientCertificateAlias: String
        get() = prefs.getString(KEY_CLIENT_CERT_ALIAS, "").orEmpty()
        set(value) = prefs.edit().putString(KEY_CLIENT_CERT_ALIAS, value).apply()

    val isConfigured: Boolean
        get() = serverUrl.isNotBlank()

    /** HTTP Basic auth header value, or null when no username is set. */
    fun basicAuthHeader(): String? =
        if (username.isBlank()) null else Credentials.basic(username, password)

    /** Server URL guaranteed to end without a trailing slash. */
    fun baseUrl(): String = serverUrl.trimEnd('/')

    companion object {
        private const val KEY_URL = "server_url"
        private const val KEY_USER = "username"
        private const val KEY_PASS = "password"
        private const val KEY_CLIENT_CERT_ALIAS = "client_certificate_alias"

        fun normalizeUrl(raw: String): String {
            var url = raw.trim()
            if (url.isEmpty()) return url
            if (!url.startsWith("http://") && !url.startsWith("https://")) {
                url = "http://$url"
            }
            return url.trimEnd('/')
        }
    }
}

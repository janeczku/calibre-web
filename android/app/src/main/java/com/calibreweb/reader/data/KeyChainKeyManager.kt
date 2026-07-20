package com.calibreweb.reader.data

import android.content.Context
import android.security.KeyChain
import java.net.Socket
import java.security.Principal
import java.security.PrivateKey
import java.security.cert.X509Certificate
import javax.net.ssl.X509KeyManager

class KeyChainKeyManager(
    private val context: Context,
    private val aliasProvider: () -> String?,
) : X509KeyManager {
    private fun alias(): String? = aliasProvider()?.takeIf { it.isNotBlank() }

    override fun chooseClientAlias(
        keyType: Array<out String>?,
        issuers: Array<out Principal>?,
        socket: Socket?,
    ): String? = alias()

    override fun getCertificateChain(alias: String?): Array<X509Certificate>? {
        val selectedAlias = alias ?: alias() ?: return null
        return KeyChain.getCertificateChain(context, selectedAlias)
    }

    override fun getPrivateKey(alias: String?): PrivateKey? {
        val selectedAlias = alias ?: alias() ?: return null
        return KeyChain.getPrivateKey(context, selectedAlias)
    }

    override fun getClientAliases(keyType: String?, issuers: Array<out Principal>?): Array<String>? =
        alias()?.let { arrayOf(it) }

    override fun chooseServerAlias(keyType: String?, issuers: Array<out Principal>?, socket: Socket?): String? = null

    override fun getServerAliases(keyType: String?, issuers: Array<out Principal>?): Array<String>? = null
}

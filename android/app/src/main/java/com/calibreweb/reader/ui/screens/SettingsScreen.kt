package com.calibreweb.reader.ui.screens

import android.app.Activity
import android.security.KeyChain
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import com.calibreweb.reader.ui.rememberApp
import kotlinx.coroutines.launch

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SettingsScreen(onSaved: () -> Unit) {
    val app = rememberApp()
    val context = LocalContext.current
    val scope = rememberCoroutineScope()

    var url by remember { mutableStateOf(app.settings.serverUrl) }
    var user by remember { mutableStateOf(app.settings.username) }
    var pass by remember { mutableStateOf(app.settings.password) }
    var clientCertificateAlias by remember { mutableStateOf(app.settings.clientCertificateAlias) }
    var status by remember { mutableStateOf<String?>(null) }
    var isError by remember { mutableStateOf(false) }
    var testing by remember { mutableStateOf(false) }

    Scaffold(
        topBar = { TopAppBar(title = { Text("Server Settings") }) },
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(16.dp)
                .verticalScroll(rememberScrollState()),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Text(
                "Connect to your Calibre-Web server. The app uses the OPDS " +
                    "catalog, so make sure OPDS is enabled for your account.",
                style = MaterialTheme.typography.bodyMedium,
            )
            OutlinedTextField(
                value = url,
                onValueChange = { url = it; status = null },
                label = { Text("Server URL") },
                placeholder = { Text("http://192.168.1.10:8083") },
                singleLine = true,
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Uri),
                modifier = Modifier.fillMaxWidth(),
            )
            OutlinedTextField(
                value = user,
                onValueChange = { user = it; status = null },
                label = { Text("Username") },
                singleLine = true,
                modifier = Modifier.fillMaxWidth(),
            )
            OutlinedTextField(
                value = pass,
                onValueChange = { pass = it; status = null },
                label = { Text("Password") },
                singleLine = true,
                visualTransformation = PasswordVisualTransformation(),
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Password),
                modifier = Modifier.fillMaxWidth(),
            )

            Text(
                "Optional mTLS: install a client certificate in Android settings, " +
                    "then select it here. The chosen KeyChain certificate is used for all HTTPS OPDS, cover, and download requests.",
                style = MaterialTheme.typography.bodyMedium,
            )
            OutlinedTextField(
                value = clientCertificateAlias.ifBlank { "No client certificate selected" },
                onValueChange = {},
                label = { Text("mTLS client certificate") },
                singleLine = true,
                readOnly = true,
                modifier = Modifier.fillMaxWidth(),
            )
            OutlinedButton(
                onClick = {
                    KeyChain.choosePrivateKeyAlias(
                        context as Activity,
                        { alias ->
                            if (alias != null) {
                                app.settings.clientCertificateAlias = alias
                                clientCertificateAlias = alias
                                status = "Selected client certificate: $alias"
                                isError = false
                            }
                        },
                        null,
                        null,
                        null,
                        -1,
                        clientCertificateAlias.ifBlank { null },
                    )
                },
                modifier = Modifier.fillMaxWidth(),
            ) {
                Text(if (clientCertificateAlias.isBlank()) "Select client certificate" else "Change client certificate")
            }
            OutlinedButton(
                onClick = {
                    app.settings.clientCertificateAlias = ""
                    clientCertificateAlias = ""
                    status = "Client certificate cleared."
                    isError = false
                },
                enabled = clientCertificateAlias.isNotBlank(),
                modifier = Modifier.fillMaxWidth(),
            ) {
                Text("Clear client certificate")
            }

            Button(
                onClick = {
                    app.settings.serverUrl = url
                    app.settings.username = user
                    app.settings.password = pass
                    url = app.settings.serverUrl // reflect normalization
                    testing = true
                    status = null
                    scope.launch {
                        val result = app.opdsClient.testConnection()
                        testing = false
                        result.onSuccess {
                            isError = false
                            status = "Connected successfully."
                            onSaved()
                        }.onFailure {
                            isError = true
                            status = it.message ?: "Connection failed"
                        }
                    }
                },
                enabled = !testing && url.isNotBlank(),
                modifier = Modifier.fillMaxWidth(),
            ) {
                if (testing) {
                    CircularProgressIndicator(
                        modifier = Modifier
                            .size(18.dp)
                            .padding(end = 4.dp),
                        strokeWidth = 2.dp,
                    )
                }
                Text(if (testing) "Testing…" else "Save & Connect")
            }

            status?.let {
                Text(
                    it,
                    color = if (isError) MaterialTheme.colorScheme.error
                    else MaterialTheme.colorScheme.primary,
                    style = MaterialTheme.typography.bodyMedium,
                )
            }
        }
    }
}

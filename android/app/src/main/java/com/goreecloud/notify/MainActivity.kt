package com.goreecloud.notify

import android.Manifest
import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import com.goreecloud.ui.material3.GoreeCloudExpressiveTheme
import kotlinx.coroutines.delay
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val manager = getSystemService(NotificationManager::class.java)
        manager.createNotificationChannel(
            NotificationChannel("notify_topics", "Topic activity", NotificationManager.IMPORTANCE_DEFAULT)
        )
        setContent {
            GoreeCloudExpressiveTheme {
                NotifyScreen(onNewMessage = { topic ->
                    if (Build.VERSION.SDK_INT < 33 ||
                        ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS)
                            == PackageManager.PERMISSION_GRANTED
                    ) {
                        val notice = Notification.Builder(this, "notify_topics")
                            .setSmallIcon(android.R.drawable.ic_dialog_info)
                            .setContentTitle("GoreeCloud Notify")
                            .setContentText("New notification in #$topic")
                            .setAutoCancel(true)
                            .build()
                        manager.notify(System.currentTimeMillis().toInt(), notice)
                    }
                })
            }
        }
    }
}

@Composable
private fun NotifyScreen(onNewMessage: (String) -> Unit) {
    var server by remember { mutableStateOf("") }
    var token by remember { mutableStateOf("") }
    var topic by remember { mutableStateOf("general") }
    var title by remember { mutableStateOf("") }
    var body by remember { mutableStateOf("") }
    var priority by remember { mutableIntStateOf(3) }
    var status by remember { mutableStateOf("Connect to your private notification server") }
    var messages by remember { mutableStateOf<List<Notice>>(emptyList()) }
    var sending by remember { mutableStateOf(false) }
    val scope = rememberCoroutineScope()
    val context = androidx.compose.ui.platform.LocalContext.current
    val permissionLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { granted ->
        status = if (granted) "Notification permission enabled" else "In-app notifications only"
    }
    val ready = server.startsWith("https://") &&
        token.length >= 32 && Regex("^[A-Za-z0-9_-]{1,64}$").matches(topic)

    LaunchedEffect(server, token, topic, ready) {
        if (!ready) {
            messages = emptyList()
            return@LaunchedEffect
        }
        var initial = true
        var lastId: String? = null
        while (isActive) {
            runCatching { NotifyApi.history(server, token, topic) }
                .onSuccess { updated ->
                    if (!initial && updated.isNotEmpty() && updated.first().id != lastId) {
                        onNewMessage(topic) // preview suppressed by design
                    }
                    initial = false
                    lastId = updated.firstOrNull()?.id
                    messages = updated
                    status = "Connected to #$topic"
                }
                .onFailure { status = "Connection problem: " + (it.message ?: "Unknown error") }
            delay(15_000) // foreground-only polling; background push is not implemented
        }
    }

    Scaffold(
        topBar = { Surface(tonalElevation = 2.dp) {
            Column(Modifier.fillMaxWidth().padding(20.dp)) {
                Text("GoreeCloud Notify", style = MaterialTheme.typography.headlineMedium)
                Text("Private notifications", style = MaterialTheme.typography.bodySmall)
            }
        } },
        bottomBar = { Surface {
            Text(
                text = status,
                modifier = Modifier.fillMaxWidth().padding(12.dp),
                style = MaterialTheme.typography.bodySmall
            )
        } }
    ) { padding ->
        Column(
            Modifier.fillMaxSize().padding(padding).verticalScroll(rememberScrollState())
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            Text("Connection", style = MaterialTheme.typography.titleLarge)
            OutlinedTextField(
                value = server, onValueChange = { server = it },
                label = { Text("HTTPS server URL") },
                placeholder = { Text("https://notify.example.com") },
                modifier = Modifier.fillMaxWidth(), singleLine = true
            )
            OutlinedTextField(
                value = token, onValueChange = { token = it },
                label = { Text("API token (memory only)") },
                visualTransformation = PasswordVisualTransformation(),
                modifier = Modifier.fillMaxWidth(), singleLine = true
            )
            OutlinedTextField(
                value = topic, onValueChange = { topic = it },
                label = { Text("Topic") },
                modifier = Modifier.fillMaxWidth(), singleLine = true
            )
            OutlinedButton(onClick = {
                if (Build.VERSION.SDK_INT >= 33) {
                    permissionLauncher.launch(Manifest.permission.POST_NOTIFICATIONS)
                } else status = "Notifications enabled"
            }) { Text("Allow in-app alerts") }

            HorizontalDivider()
            Text("Publish", style = MaterialTheme.typography.titleLarge)
            OutlinedTextField(
                value = title, onValueChange = { title = it.take(160) },
                label = { Text("Title (optional)") }, modifier = Modifier.fillMaxWidth()
            )
            OutlinedTextField(
                value = body, onValueChange = { body = it.take(4096) },
                label = { Text("Message") }, minLines = 3, modifier = Modifier.fillMaxWidth()
            )
            Text("Priority: $priority", style = MaterialTheme.typography.bodyMedium)
            Slider(value = priority.toFloat(), onValueChange = { priority = it.toInt() },
                valueRange = 1f..5f, steps = 3)
            Button(
                enabled = ready && body.isNotBlank() && !sending,
                modifier = Modifier.fillMaxWidth(),
                onClick = {
                    sending = true
                    scope.launch {
                        runCatching { NotifyApi.publish(server, token, topic, title, body, priority) }
                            .onSuccess { body = ""; title = ""; status = "Published to #$topic" }
                            .onFailure { status = "Publish failed: " + (it.message ?: "Unknown error") }
                        sending = false
                    }
                }
            ) { Text(if (sending) "Publishing…" else "Publish notification") }

            HorizontalDivider()
            Text("Inbox · ${messages.size} recent", style = MaterialTheme.typography.titleLarge)
            if (!ready) {
                Text("Enter an HTTPS server, API token and topic.")
            } else if (messages.isEmpty()) {
                Text("No messages yet.")
            } else {
                messages.forEach { notice ->
                    ElevatedCard(Modifier.fillMaxWidth()) {
                        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                            Text("Priority ${notice.priority}", style = MaterialTheme.typography.labelMedium)
                            if (notice.title.isNotBlank()) {
                                Text(notice.title, style = MaterialTheme.typography.titleMedium)
                            }
                            Text(notice.body, style = MaterialTheme.typography.bodyMedium)
                            Text(notice.createdAt, style = MaterialTheme.typography.labelSmall)
                        }
                    }
                }
            }
        }
    }
}

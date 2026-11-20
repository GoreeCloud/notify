package com.goreecloud.notify

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL

data class Notice(
    val id: String,
    val title: String,
    val body: String,
    val priority: Int,
    val createdAt: String
)

object NotifyApi {
    private val topicPattern = Regex("^[a-zA-Z0-9_-]{1,64}$")

    private fun connect(
        server: String,
        token: String,
        topic: String,
        suffix: String,
        method: String
    ): HttpURLConnection {
        require(token.length >= 32) { "Enter a server token of at least 32 characters" }
        require(topicPattern.matches(topic)) { "Topic may only contain letters, numbers, - or _" }
        val base = URL(server.trimEnd('/'))
        require(base.protocol == "https" && base.host.isNotBlank() && base.userInfo == null &&
            (base.path.isEmpty() || base.path == "/") && base.query == null && base.ref == null) {
            "Use an HTTPS server origin without a path, query or credentials"
        }
        val url = URL(base.toString().trimEnd('/') + "/api/v1/topics/$topic/$suffix")
        return (url.openConnection() as HttpURLConnection).apply {
            requestMethod = method
            connectTimeout = 10_000
            readTimeout = 10_000
            useCaches = false
            setRequestProperty("Authorization", "Bearer $token")
            setRequestProperty("Accept", "application/json")
        }
    }

    suspend fun history(server: String, token: String, topic: String): List<Notice> =
        withContext(Dispatchers.IO) {
            val connection = connect(server, token, topic, "messages?limit=50", "GET")
            try {
                val code = connection.responseCode
                require(code == 200) { "History request failed (HTTP $code)" }
                val response = connection.inputStream.bufferedReader().use { it.readText() }
                val messages = JSONObject(response).getJSONArray("messages")
                (0 until messages.length()).map { index ->
                    val item = messages.getJSONObject(index)
                    Notice(
                        id = item.getString("id"),
                        title = item.optString("title"),
                        body = item.getString("body"),
                        priority = item.optInt("priority", 3),
                        createdAt = item.optString("created_at")
                    )
                }
            } finally {
                connection.disconnect()
            }
        }

    suspend fun publish(
        server: String,
        token: String,
        topic: String,
        title: String,
        body: String,
        priority: Int
    ) = withContext(Dispatchers.IO) {
        require(body.isNotBlank() && body.length <= 4096) { "Enter a message up to 4096 characters" }
        require(title.length <= 160 && priority in 1..5) { "Invalid title or priority" }
        val connection = connect(server, token, topic, "messages", "POST")
        try {
            connection.doOutput = true
            connection.setRequestProperty("Content-Type", "application/json")
            val payload = JSONObject()
                .put("title", title)
                .put("body", body)
                .put("priority", priority)
                .toString()
            connection.outputStream.bufferedWriter().use { it.write(payload) }
            val code = connection.responseCode
            require(code == 201) { "Publish request failed (HTTP $code)" }
        } finally {
            connection.disconnect()
        }
    }
}

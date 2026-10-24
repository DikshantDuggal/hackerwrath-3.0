package com.edgerunners.scamcheck.ui.screens

import androidx.compose.foundation.layout.safeDrawingPadding
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.heading
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.edgerunners.scamcheck.AppUiState
import com.edgerunners.scamcheck.BuildConfig
import com.edgerunners.scamcheck.R
import com.edgerunners.scamcheck.SignInError
import com.edgerunners.scamcheck.ui.spell.Blob
import com.edgerunners.scamcheck.ui.spell.Body
import com.edgerunners.scamcheck.ui.spell.Display
import com.edgerunners.scamcheck.ui.spell.GlowBackground
import com.edgerunners.scamcheck.ui.spell.GuardianBlob
import com.edgerunners.scamcheck.ui.spell.SpellButton
import com.edgerunners.scamcheck.ui.spell.guardianBrush
import com.edgerunners.scamcheck.ui.theme.Spell

// Sign-in, in the Spellbreaker look. Every other screen lives in ui/spell.

@Composable
fun SignInScreen(state: AppUiState, onSignIn: (String, String) -> Unit) {
    val c = Spell.colors
    var username by rememberSaveable { mutableStateOf("") }
    var password by rememberSaveable { mutableStateOf("") }
    val ready = !state.signingIn && username.isNotBlank() && password.isNotBlank()
    Box(Modifier.fillMaxSize().background(c.bg)) {
        GlowBackground(c.glow, Modifier.fillMaxSize())
        Column(
            Modifier.fillMaxSize().safeDrawingPadding().verticalScroll(rememberScrollState()).padding(horizontal = 22.dp, vertical = 48.dp),
            verticalArrangement = Arrangement.spacedBy(18.dp),
        ) {
            GuardianBlob(Blob.Cookie, Modifier.size(88.dp), radius = 74f, fill = guardianBrush(), breathe = true, highlight = 0.5f)
            Display(stringResource(R.string.app_name), 24f)
            Display(stringResource(R.string.signin_title), 42f, lineHeight = 0.98f, modifier = Modifier.semantics { heading() })
            Body(stringResource(R.string.signin_subtitle), 16.sp, lineHeight = 1.5f)
            OutlinedTextField(
                value = username,
                onValueChange = { username = it },
                label = { Text(stringResource(R.string.signin_username)) },
                singleLine = true,
                textStyle = TextStyle(fontSize = 18.sp),
                keyboardOptions = KeyboardOptions(imeAction = ImeAction.Next),
                modifier = Modifier.fillMaxWidth(),
            )
            OutlinedTextField(
                value = password,
                onValueChange = { password = it },
                label = { Text(stringResource(R.string.signin_password)) },
                singleLine = true,
                textStyle = TextStyle(fontSize = 18.sp),
                visualTransformation = PasswordVisualTransformation(),
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Password, imeAction = ImeAction.Done),
                modifier = Modifier.fillMaxWidth(),
            )
            state.signInError?.let { error ->
                val message = when (error) {
                    SignInError.BadCredentials -> R.string.signin_error_credentials
                    SignInError.TooManyAttempts -> R.string.signin_error_rate
                    SignInError.Network -> R.string.signin_error_network
                }
                Body(stringResource(message), 15.sp, color = c.end, modifier = Modifier.semantics { liveRegion = LiveRegionMode.Polite })
            }
            SpellButton(
                stringResource(R.string.signin_button),
                { if (ready) onSignIn(username, password) },
                Modifier.fillMaxWidth(),
                background = if (ready) c.accent else c.off,
                content = if (ready) c.onAccent else c.faint,
            )
            SpellButton(
                "Enter Demo Mode (Offline)",
                { onSignIn("demo-user", "demo") },
                Modifier.fillMaxWidth(),
                background = c.card,
                content = c.ink,
            )
            Body(stringResource(R.string.signin_server, BuildConfig.API_BASE_URL), 13.sp, color = c.faint)
        }
    }
}

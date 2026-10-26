package com.edgerunners.scamcheck.ui.spell

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.outlined.Backspace
import androidx.compose.material.icons.automirrored.outlined.Logout
import androidx.compose.material.icons.outlined.Call
import androidx.compose.material.icons.outlined.LocalOffer
import androidx.compose.material.icons.outlined.PlayArrow
import androidx.compose.material.icons.outlined.Shield
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.LiveRegionMode
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.liveRegion
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.em
import androidx.compose.ui.unit.sp
import com.edgerunners.scamcheck.R
import com.edgerunners.scamcheck.model.AppLanguage
import com.edgerunners.scamcheck.model.DemoScenario
import androidx.compose.material.icons.filled.Clear
import androidx.compose.material.icons.outlined.CheckCircle
import androidx.compose.material.icons.outlined.ErrorOutline
import androidx.compose.material.icons.outlined.Refresh
import androidx.compose.material3.IconButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import com.edgerunners.scamcheck.data.SystemStatusDto
import com.edgerunners.scamcheck.data.MessageAnalysisDto
import com.edgerunners.scamcheck.ui.theme.Spell

// ---------- Settings ----------

@Composable
fun SettingsSheet(
    visible: Boolean,
    language: AppLanguage,
    onLanguage: (AppLanguage) -> Unit,
    expecting: Boolean,
    onExpecting: (Boolean) -> Unit,
    demoEnabled: Boolean,
    onPractice: () -> Unit,
    onCircle: () -> Unit,
    onDemo: () -> Unit,
    onSignOut: () -> Unit,
    onDismiss: () -> Unit,
) {
    val c = Spell.colors
    SpellSheet(visible, stringResource(R.string.sb_settings), onDismiss) {
        Display(stringResource(R.string.sb_settings), 26f)
        Eyebrow(stringResource(R.string.sb_warnings_in), color = c.faint)
        val languages = listOf(AppLanguage.English, AppLanguage.Hindi, AppLanguage.Punjabi)
        Segmented(
            listOf(stringResource(R.string.sb_lang_native_en), stringResource(R.string.sb_lang_native_hi), stringResource(R.string.sb_lang_native_pa)),
            selected = languages.indexOf(language).coerceAtLeast(0),
            onSelect = { onLanguage(languages[it]) },
            height = 52,
        )
        SpellRow(
            stringResource(R.string.sb_feel),
            subtitle = stringResource(R.string.sb_feel_sub),
            onClick = onPractice,
            leading = { IconTile(c.tert) { HapBars(Modifier.width(26.dp), barHeight = 8.dp, gap = 3.dp) } },
        )
        SpellRow(
            stringResource(R.string.home_expecting),
            subtitle = stringResource(if (expecting) R.string.sb_sell_on else R.string.sb_sell_off),
            toggle = expecting to onExpecting,
            leading = { IconTile(c.tert) { Icon(Icons.Outlined.LocalOffer, contentDescription = null, tint = c.onTert, modifier = Modifier.size(22.dp)) } },
            trailing = { SpellSwitch(expecting) },
        )
        SpellRow(
            stringResource(R.string.sb_your_circle),
            subtitle = stringResource(R.string.sb_circle_row_sub, DemoPeople.trusted.name),
            onClick = onCircle,
            leading = {
                IconTile(c.accentC) {
                    Text(DemoPeople.trusted.name.take(1), style = TextStyle(fontSize = 18.sp, fontWeight = FontWeight.Black), color = c.onAccentC)
                }
            },
        )
        if (demoEnabled) {
            Eyebrow(stringResource(R.string.sb_for_demos), color = c.faint, modifier = Modifier.padding(top = 4.dp))
            SpellRow(
                stringResource(R.string.sb_demo_calls),
                subtitle = stringResource(R.string.sb_demo_calls_sub),
                onClick = onDemo,
                leading = { IconTile(c.surface2) { Icon(Icons.Outlined.PlayArrow, contentDescription = null, tint = c.ink, modifier = Modifier.size(20.dp)) } },
            )
        }
        SpellRow(
            stringResource(R.string.home_sign_out),
            onClick = onSignOut,
            leading = { IconTile(c.surface2) { Icon(Icons.AutoMirrored.Outlined.Logout, contentDescription = null, tint = c.ink, modifier = Modifier.size(20.dp)) } },
        )
    }
}

// ---------- Demo calls ----------

@Composable
fun DemoSheet(visible: Boolean, failed: Boolean, onStart: (DemoScenario) -> Unit, onDismiss: () -> Unit) {
    val c = Spell.colors
    SpellSheet(visible, stringResource(R.string.sb_demo_calls), onDismiss) {
        Display(stringResource(R.string.sb_demo_calls), 26f)
        Body(stringResource(R.string.sb_demo_scripted), 14.sp, color = c.faint)
        DemoRow(stringResource(R.string.sb_mark_qr), c.badgeQr, stringResource(R.string.sb_demo_qr_title), stringResource(R.string.sb_demo_qr_sub)) { onStart(DemoScenario.QrScan) }
        DemoRow(stringResource(R.string.sb_mark_otp), c.badgeOtp, stringResource(R.string.sb_demo_otp_title), stringResource(R.string.sb_demo_otp_sub)) { onStart(DemoScenario.Otp) }
        DemoRow(stringResource(R.string.sb_mark_calm), c.badgeCalm, stringResource(R.string.sb_demo_calm_title), stringResource(R.string.sb_demo_calm_sub)) { onStart(DemoScenario.Harmless) }
        DemoRow(stringResource(R.string.sb_mark_unavailable), c.badgeCalm, stringResource(R.string.sb_demo_unavailable_title), stringResource(R.string.sb_demo_unavailable_sub)) { onStart(DemoScenario.Unavailable) }
        if (failed) {
            Body(stringResource(R.string.home_demo_failed), 14.sp, color = c.end, modifier = Modifier.semantics { liveRegion = LiveRegionMode.Polite })
        }
        Text(stringResource(R.string.sb_demo_shortcut), style = TextStyle(fontSize = 12.sp), color = c.faint, textAlign = TextAlign.Center, modifier = Modifier.fillMaxWidth())
    }
}

@Composable
private fun DemoRow(mark: String, badge: Pair<Color, Color>, title: String, subtitle: String, onClick: () -> Unit) {
    SpellRow(
        title,
        subtitle = subtitle,
        onClick = onClick,
        leading = { IconTile(badge.first) { Text(mark, style = TextStyle(fontSize = 12.sp, fontWeight = FontWeight.Black), color = badge.second) } },
    )
}

// ---------- Already paid or shared a code? ----------

/** The four recovery steps, in order. */
enum class RecoveryStep { Helpline, ReportOnline, Bank, Tell }

@Composable
fun RecoverySheet(visible: Boolean, onStep: (RecoveryStep) -> Unit, onDismiss: () -> Unit) {
    val c = Spell.colors
    SpellSheet(visible, stringResource(R.string.sb_help_title), onDismiss) {
        Display(stringResource(R.string.sb_help_title), 26f, lineHeight = 1.1f)
        Body(stringResource(R.string.sb_recovery_sub), 14.sp, color = c.faint)
        val steps = listOf(
            Triple(RecoveryStep.Helpline, R.string.sb_step_helpline, R.string.sb_step_call),
            Triple(RecoveryStep.ReportOnline, R.string.sb_step_report, R.string.sb_step_open),
            Triple(RecoveryStep.Bank, R.string.sb_step_bank, null),
            Triple(RecoveryStep.Tell, R.string.sb_step_tell, R.string.sb_step_send),
        )
        steps.forEachIndexed { i, (step, text, cta) ->
            Row(
                Modifier.fillMaxWidth().clip(RoundedCornerShape(22.dp)).background(c.card).border(1.dp, c.line, RoundedCornerShape(22.dp))
                    .press({ onStep(step) }).padding(horizontal = 16.dp, vertical = 14.dp),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(14.dp),
            ) {
                IconTile(c.accent, size = 36.dp, radius = 12.dp) {
                    Text((i + 1).toString(), style = TextStyle(fontSize = 16.sp, fontWeight = FontWeight.Black), color = c.onAccent)
                }
                Text(stringResource(text), style = TextStyle(fontSize = 16.sp, lineHeight = 21.sp, fontWeight = FontWeight.Bold), color = c.ink, modifier = Modifier.weight(1f))
                if (cta != null) Text(stringResource(cta), style = TextStyle(fontSize = 14.sp, fontWeight = FontWeight.ExtraBold), color = c.accent)
            }
        }
    }
}

// ---------- Keypad ----------

private val keys = listOf("1" to "", "2" to "ABC", "3" to "DEF", "4" to "GHI", "5" to "JKL", "6" to "MNO", "7" to "PQRS", "8" to "TUV", "9" to "WXYZ", "*" to "", "0" to "+", "#" to "")

@Composable
fun KeypadSheet(visible: Boolean, dial: String, onDigit: (String) -> Unit, onDelete: () -> Unit, onCall: () -> Unit, onDismiss: () -> Unit) {
    val c = Spell.colors
    SpellSheet(visible, stringResource(R.string.sb_keypad), onDismiss) {
        Display(dial.ifEmpty { " " }, 34f, lineHeight = 1.2f, align = TextAlign.Center, modifier = Modifier.fillMaxWidth().heightIn(min = 44.dp))
        val match = DemoPeople.matchNumber(dial)
        Text(
            when {
                dial.isEmpty() -> stringResource(R.string.sb_keypad_hint)
                match != null -> match.name
                else -> stringResource(R.string.sb_not_in_contacts)
            },
            style = TextStyle(fontSize = 13.sp),
            color = c.faint,
            textAlign = TextAlign.Center,
            modifier = Modifier.fillMaxWidth().heightIn(min = 18.dp),
        )
        Column(Modifier.padding(horizontal = 14.dp, vertical = 4.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            keys.chunked(3).forEach { row ->
                Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                    row.forEach { (digit, letters) ->
                        Column(
                            Modifier.weight(1f).heightIn(min = 60.dp).clip(RoundedCornerShape(22.dp)).background(c.card).border(1.dp, c.line, RoundedCornerShape(22.dp))
                                .press({ onDigit(digit) }, label = digit).semantics(mergeDescendants = true) { contentDescription = digit },
                            horizontalAlignment = Alignment.CenterHorizontally,
                            verticalArrangement = Arrangement.Center,
                        ) {
                            Display(digit, 26f, color = c.ink, lineHeight = 1f)
                            Text(letters, style = TextStyle(fontSize = 10.sp, letterSpacing = 0.16.em), color = c.faint, modifier = Modifier.heightIn(min = 12.dp))
                        }
                    }
                }
            }
        }
        Row(Modifier.fillMaxWidth().padding(horizontal = 14.dp), verticalAlignment = Alignment.CenterVertically) {
            Box(Modifier.weight(1f))
            Box(Modifier.weight(1f), contentAlignment = Alignment.Center) {
                Box(
                    Modifier.size(72.dp).clip(RoundedCornerShape(26.dp)).background(c.accent).press(onCall, label = stringResource(R.string.sb_call)),
                    contentAlignment = Alignment.Center,
                ) { Icon(Icons.Outlined.Call, contentDescription = stringResource(R.string.sb_call), tint = c.onAccent, modifier = Modifier.size(28.dp)) }
            }
            Box(Modifier.weight(1f), contentAlignment = Alignment.Center) {
                Box(Modifier.size(52.dp).clip(RoundedCornerShape(18.dp)).press(onDelete, label = stringResource(R.string.sb_delete)), contentAlignment = Alignment.Center) {
                    Icon(Icons.AutoMirrored.Outlined.Backspace, contentDescription = stringResource(R.string.sb_delete), tint = c.faint, modifier = Modifier.size(26.dp))
                }
            }
        }
    }
}

// ---------- One contact ----------

@Composable
fun ContactSheet(visible: Boolean, contactId: String?, onCall: () -> Unit, onCircle: (DemoContact) -> Unit, onDismiss: () -> Unit) {
    val c = Spell.colors
    // Keep showing the last contact while the sheet slides away.
    val holder = remember { arrayOfNulls<DemoContact>(1) }
    DemoPeople.byId(contactId)?.let { holder[0] = it }
    val p = holder[0]
    SpellSheet(visible, p?.name.orEmpty(), onDismiss) {
        if (p == null) return@SpellSheet
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(14.dp), modifier = Modifier.padding(top = 4.dp)) {
            Bubble(p.name.take(1), 64.dp, fontSize = 28.sp)
            Column(verticalArrangement = Arrangement.spacedBy(3.dp)) {
                Display(p.name, 26f, lineHeight = 1.1f)
                Text(p.number, style = TextStyle(fontSize = 14.sp), color = c.faint)
            }
        }
        if (p.onApp) {
            Row(
                Modifier.clip(RoundedCornerShape(999.dp)).background(c.accentC).padding(horizontal = 12.dp, vertical = 6.dp),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(6.dp),
            ) {
                Icon(Icons.Outlined.Shield, contentDescription = null, tint = c.onAccentC, modifier = Modifier.size(14.dp))
                Text(stringResource(R.string.sb_uses_app_badge), style = TextStyle(fontSize = 13.sp, fontWeight = FontWeight.Bold), color = c.onAccentC)
            }
        }
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            SpellButton(stringResource(R.string.sb_call), onCall, Modifier.weight(1f), height = 56.dp, radius = 20.dp, fontSize = 16.sp)
            SpellButton(
                stringResource(if (p.circle != null) R.string.sb_open_circle else R.string.sb_add_to_circle),
                { onCircle(p) },
                Modifier.weight(1f),
                background = c.surface2, content = c.ink, height = 56.dp, radius = 20.dp, fontSize = 16.sp,
            )
        }
        Body(
            if (p.circle != null) stringResource(R.string.sb_circle_note_in, stringResource(p.circle)) else stringResource(R.string.sb_circle_note_add),
            13.sp,
            color = c.faint,
        )
    }
}


// ---------- Diagnostics & Live Status ----------

@Composable
fun DiagnosticsSheet(
    visible: Boolean,
    status: SystemStatusDto?,
    onRefresh: () -> Unit,
    onDismiss: () -> Unit,
) {
    val c = Spell.colors
    SpellSheet(visible, "System Diagnostics", onDismiss) {
        Row(
            Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Display("System Diagnostics", 26f)
            IconButton(onClick = onRefresh) {
                Icon(Icons.Outlined.Refresh, contentDescription = "Refresh Status", tint = c.accent)
            }
        }
        Body("Live component health and pipeline configuration:", 14.sp, color = c.faint)

        val isOnline = status?.backendOnline ?: false
        DiagnosticRow(
            title = "Backend Service",
            detail = if (isOnline) "${status?.service ?: "Online"} v${status?.version ?: "1.0.0"}" else "Connecting to 10.0.2.2:8000...",
            ok = isOnline,
        )

        val tgConfigured = status?.telegramConfigured ?: false
        val tgStatus = status?.telegramStatus ?: "DISCONNECTED"
        DiagnosticRow(
            title = "Telegram Bot Integration",
            detail = if (tgConfigured) "Status: $tgStatus | Bot: @EdgingToRunner_bot" else "Not configured",
            ok = tgConfigured,
        )

        val sttOk = status?.sttWorking ?: false
        DiagnosticRow(
            title = "Speech-to-Text Pipeline",
            detail = if (sttOk) "Sarvam AI Saaras:v3 (Multilingual STT)" else "Inactive",
            ok = sttOk,
        )

        val rulesOk = status?.rulesEngineWorking ?: false
        DiagnosticRow(
            title = "Rules Engine",
            detail = if (rulesOk) "Active (10 Multilingual Negation Rules)" else "Inactive",
            ok = rulesOk,
        )

        val icfdOk = status?.icfdModelWorking ?: false
        DiagnosticRow(
            title = "ICFD Model",
            detail = if (icfdOk) "31k Production Calibrated Classifier Active" else "Fallback Mode",
            ok = icfdOk,
        )

        Row(
            Modifier.fillMaxWidth().padding(top = 8.dp),
            horizontalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            Box(
                Modifier.weight(1f).clip(RoundedCornerShape(16.dp)).background(c.card).border(1.dp, c.line, RoundedCornerShape(16.dp)).padding(12.dp),
            ) {
                Column {
                    Text("Messages Analyzed", style = TextStyle(fontSize = 12.sp), color = c.faint)
                    Display((status?.totalMessagesAnalyzed ?: 0).toString(), 28f)
                }
            }
            Box(
                Modifier.weight(1f).clip(RoundedCornerShape(16.dp)).background(c.card).border(1.dp, c.line, RoundedCornerShape(16.dp)).padding(12.dp),
            ) {
                Column {
                    Text("Alerts Dispatched", style = TextStyle(fontSize = 12.sp), color = c.faint)
                    Display((status?.activeAlertsCount ?: 0).toString(), 28f)
                }
            }
        }
    }
}

@Composable
private fun DiagnosticRow(title: String, detail: String, ok: Boolean) {
    val c = Spell.colors
    Row(
        Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(16.dp))
            .background(c.card)
            .border(1.dp, c.line, RoundedCornerShape(16.dp))
            .padding(horizontal = 14.dp, vertical = 10.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        IconTile(if (ok) c.accentC else c.surface2, size = 32.dp, radius = 10.dp) {
            Icon(
                if (ok) Icons.Outlined.CheckCircle else Icons.Outlined.ErrorOutline,
                contentDescription = null,
                tint = if (ok) c.accent else c.end,
                modifier = Modifier.size(18.dp),
            )
        }
        Column(Modifier.weight(1f)) {
            Text(title, style = TextStyle(fontSize = 14.sp, fontWeight = FontWeight.Bold), color = c.ink)
            Text(detail, style = TextStyle(fontSize = 12.sp), color = c.faint)
        }
    }
}

// ---------- Message / Transcript Scanner ----------

@Composable
fun MessageAnalyzerSheet(
    visible: Boolean,
    analyzing: Boolean,
    lastResult: MessageAnalysisDto?,
    onAnalyze: (String) -> Unit,
    onDismiss: () -> Unit,
) {
    val c = Spell.colors
    var text by remember { mutableStateOf("") }

    SpellSheet(visible, "Message Scanner", onDismiss) {
        Display("Message Scanner", 26f)
        Body("Scan SMS, Telegram texts, or call transcripts in English, Hindi, Punjabi, or Hinglish:", 13.sp, color = c.faint)

        Row(
            Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(6.dp),
        ) {
            SampleChip("Hinglish", "Aapka SBI account suspend ho gaya hai turant APK download karke KYC update karein") { text = it }
            SampleChip("Hindi", "सीबीआई और दिल्ली पुलिस की तरफ से डिजिटल अरेस्ट वारंट जारी हुआ है, तुरंत पेनल्टी भरें।") { text = it }
            SampleChip("Punjabi", "ਤੁਹਾਡਾ ਕੈਨੇਡਾ ਵੀਜ਼ਾ ਰੱਦ ਹੋ ਗਿਆ ਹੈ, ਤੁਰੰਤ ਪੈਸੇ ਟਰਾਂਸਫਰ ਕਰੋ ਨਹੀਂ ਤਾਂ ਗ੍ਰਿਫਤਾਰੀ ਹੋਵੇਗੀ।") { text = it }
            SampleChip("Safe", "कृपया ध्यान दें, बैंक कभी भी आपसे पासवर्ड या ओटीपी नहीं मांगता। किसी को भी अपनी निजी जानकारी न दें।") { text = it }
        }

        OutlinedTextField(
            value = text,
            onValueChange = { text = it },
            placeholder = { Text("Type with laptop keyboard or paste text here...", fontSize = 14.sp) },
            minLines = 3,
            maxLines = 6,
            textStyle = TextStyle(fontSize = 15.sp, color = c.ink),
            trailingIcon = {
                if (text.isNotEmpty()) {
                    IconButton(onClick = { text = "" }) {
                        Icon(Icons.Default.Clear, contentDescription = "Clear text")
                    }
                }
            },
            modifier = Modifier.fillMaxWidth(),
        )

        SpellButton(
            if (analyzing) "Analyzing with EdgeRunner AI..." else "Scan & Analyze Risk",
            onClick = { if (text.isNotBlank() && !analyzing) onAnalyze(text) },
            Modifier.fillMaxWidth(),
            background = if (text.isNotBlank() && !analyzing) c.accent else c.off,
            content = if (text.isNotBlank() && !analyzing) c.onAccent else c.faint,
        )

        lastResult?.let { res ->
            Column(
                Modifier
                    .fillMaxWidth()
                    .clip(RoundedCornerShape(18.dp))
                    .background(c.card)
                    .border(1.dp, c.line, RoundedCornerShape(18.dp))
                    .padding(14.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                Row(
                    Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Row(
                        Modifier.clip(RoundedCornerShape(8.dp)).background(c.surface2).padding(horizontal = 8.dp, vertical = 4.dp),
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(4.dp),
                    ) {
                        Text(
                            "${res.detectedLanguage} (${res.detectedScript})",
                            style = TextStyle(fontSize = 11.sp, fontWeight = FontWeight.Bold),
                            color = c.ink,
                        )
                    }

                    val badgeColor = when (res.riskLevel) {
                        "CRITICAL" -> c.end to c.onAccent
                        "HIGH" -> c.end to c.onAccent
                        "MEDIUM" -> c.warn to c.ink
                        else -> c.accent to c.onAccent
                    }
                    Box(
                        Modifier.clip(RoundedCornerShape(8.dp)).background(badgeColor.first).padding(horizontal = 10.dp, vertical = 4.dp),
                    ) {
                        Text(
                            "${res.riskLevel} (${res.riskScore.toInt()}%)",
                            style = TextStyle(fontSize = 11.sp, fontWeight = FontWeight.Black),
                            color = badgeColor.second,
                        )
                    }
                }

                if (res.protectiveAdvice) {
                    Box(
                        Modifier.fillMaxWidth().clip(RoundedCornerShape(8.dp)).background(c.accentC).padding(8.dp),
                    ) {
                        Text(
                            "🛡️ Legitimate Security Reminder: Warns not to share credentials",
                            style = TextStyle(fontSize = 12.sp, fontWeight = FontWeight.Bold),
                            color = c.onAccentC,
                        )
                    }
                }

                Text(res.headline, style = TextStyle(fontSize = 14.sp, fontWeight = FontWeight.Bold), color = c.ink)
                Text(res.safeAction, style = TextStyle(fontSize = 12.sp, lineHeight = 16.sp), color = c.faint)

                if (res.signals.isNotEmpty()) {
                    Column(verticalArrangement = Arrangement.spacedBy(2.dp), modifier = Modifier.padding(top = 4.dp)) {
                        Text("Signals Detected:", style = TextStyle(fontSize = 11.sp, fontWeight = FontWeight.ExtraBold), color = c.head)
                        res.signals.forEach { sig ->
                            Text("• $sig", style = TextStyle(fontSize = 11.sp), color = c.faint)
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun SampleChip(label: String, prompt: String, onSelect: (String) -> Unit) {
    val c = Spell.colors
    Box(
        Modifier
            .clip(RoundedCornerShape(12.dp))
            .background(c.surface2)
            .border(1.dp, c.line, RoundedCornerShape(12.dp))
            .press({ onSelect(prompt) })
            .padding(horizontal = 8.dp, vertical = 6.dp),
    ) {
        Text(label, style = TextStyle(fontSize = 11.sp, fontWeight = FontWeight.Bold), color = c.ink)
    }
}

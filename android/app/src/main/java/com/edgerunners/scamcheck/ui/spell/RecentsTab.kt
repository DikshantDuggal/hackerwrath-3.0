package com.edgerunners.scamcheck.ui.spell

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.expandVertically
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.shrinkVertically
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.selection.selectable
import androidx.compose.foundation.selection.selectableGroup
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.Lock
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.stateDescription
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.edgerunners.scamcheck.R
import com.edgerunners.scamcheck.alert.CallOutcome
import com.edgerunners.scamcheck.alert.CallRecord
import com.edgerunners.scamcheck.model.RequestType
import com.edgerunners.scamcheck.ui.theme.Spell
import java.util.Calendar
import java.util.Locale

/** A two-way segmented choice: the chosen side is a pill, the other a soft square. */
@Composable
fun Segmented(options: List<String>, selected: Int, onSelect: (Int) -> Unit, modifier: Modifier = Modifier, height: Int = 46) {
    val c = Spell.colors
    Row(modifier.fillMaxWidth().selectableGroup(), horizontalArrangement = Arrangement.spacedBy(4.dp)) {
        options.forEachIndexed { i, label ->
            val on = i == selected
            val shape = RoundedCornerShape(if (on) 26.dp else 10.dp)
            Box(
                Modifier
                    .weight(1f)
                    .heightIn(min = height.dp)
                    .clip(shape)
                    .background(if (on) c.accent else c.card)
                    .then(if (on) Modifier else Modifier.border(1.dp, c.line, shape))
                    .selectable(selected = on, role = Role.RadioButton, onClick = { onSelect(i) }),
                contentAlignment = Alignment.Center,
            ) {
                Text(label, style = TextStyle(fontSize = 15.sp, fontWeight = FontWeight.Bold), color = if (on) c.onAccent else c.muted)
            }
        }
    }
}

/** Recents: a timeline of calls; each warning tells its own story when opened. */
@Composable
fun RecentsTab(
    history: List<CallRecord>,
    nowMs: Long,
    onlyWarnings: Boolean,
    onFilter: (Boolean) -> Unit,
    openCallId: String?,
    onToggleOpen: (String) -> Unit,
    onReport: (CallRecord) -> Unit,
    onNotBuilt: () -> Unit,
    onOpenRecovery: () -> Unit,
) {
    val c = Spell.colors
    val locale = appLocale()
    Column(verticalArrangement = Arrangement.spacedBy(14.dp)) {
        Segmented(
            listOf(stringResource(R.string.sb_filter_all), stringResource(R.string.sb_filter_warn)),
            selected = if (onlyWarnings) 1 else 0,
            onSelect = { onFilter(it == 1) },
        )

        val shown = history.filter { !onlyWarnings || it.warned }
        if (shown.isEmpty()) {
            Body(stringResource(R.string.sb_rec_empty), 15.sp, color = c.faint, modifier = Modifier.padding(vertical = 18.dp, horizontal = 2.dp))
        }
        val groups = shown.groupBy { dayGroup(it.endedAtMs, nowMs) }
        Column {
            groups.forEach { (group, items) ->
                Eyebrow(groupLabel(group, items.first().endedAtMs, locale), color = c.faint, modifier = Modifier.padding(start = 40.dp, top = 12.dp, bottom = 6.dp))
                items.forEach { record ->
                    RecentRow(
                        record = record,
                        open = record.warned && record.callId == openCallId,
                        locale = locale,
                        onToggle = { if (record.warned) onToggleOpen(record.callId) },
                        onReport = { onReport(record) },
                        onNotBuilt = onNotBuilt,
                        onOpenRecovery = onOpenRecovery,
                    )
                }
            }
        }

        Row(Modifier.padding(start = 4.dp, end = 4.dp, top = 6.dp), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            Icon(Icons.Outlined.Lock, contentDescription = null, tint = c.faint, modifier = Modifier.size(18.dp))
            Body(stringResource(R.string.sb_rec_privacy), 13.sp, color = c.faint, lineHeight = 1.4f)
        }
    }
}

/** 0 today, 1 yesterday, 2 or more: that many days ago. */
private fun dayGroup(atMs: Long, nowMs: Long): Int {
    val day = Calendar.getInstance().apply { timeInMillis = atMs }
    val now = Calendar.getInstance().apply { timeInMillis = nowMs }
    var diff = 0
    while (diff < 400 && (day.get(Calendar.YEAR) != now.get(Calendar.YEAR) || day.get(Calendar.DAY_OF_YEAR) != now.get(Calendar.DAY_OF_YEAR))) {
        now.add(Calendar.DAY_OF_YEAR, -1)
        diff++
    }
    return diff
}

@Composable
private fun groupLabel(group: Int, atMs: Long, locale: Locale): String = when (group) {
    0 -> stringResource(R.string.sb_today)
    1 -> stringResource(R.string.sb_group_yesterday)
    in 2..6 -> java.text.SimpleDateFormat("EEEE", locale).format(java.util.Date(atMs))
    else -> java.text.SimpleDateFormat("d MMM", locale).format(java.util.Date(atMs))
}

@Composable
fun askedLabel(type: RequestType?): String = stringResource(
    when (type) {
        RequestType.OtpShare -> R.string.sb_rec_asked_otp
        RequestType.PinReceive -> R.string.sb_rec_asked_pin
        else -> R.string.sb_rec_asked_qr
    }
)

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun RecentRow(
    record: CallRecord,
    open: Boolean,
    locale: Locale,
    onToggle: () -> Unit,
    onReport: () -> Unit,
    onNotBuilt: () -> Unit,
    onOpenRecovery: () -> Unit,
) {
    val c = Spell.colors
    val warn = record.warned
    val length = clock(record.lengthSeconds)
    val line = when (record.outcome) {
        CallOutcome.Stopped -> stringResource(R.string.sb_rec_hung_up, askedLabel(record.type))
        CallOutcome.Kept -> stringResource(R.string.sb_rec_kept, askedLabel(record.type))
        CallOutcome.CallerLeft -> stringResource(R.string.sb_rec_caller_left, askedLabel(record.type))
        CallOutcome.Calm -> stringResource(R.string.sb_rec_calm, length)
        CallOutcome.Off -> stringResource(R.string.sb_rec_off, length)
    }
    val who = record.number.ifEmpty { stringResource(R.string.unknown_number) } +
        if (record.demo) " · " + stringResource(R.string.sb_demo_tag) else ""
    val expanded = stringResource(R.string.sb_expanded)
    val collapsed = stringResource(R.string.sb_collapsed)
    Row(Modifier.fillMaxWidth().heightInIntrinsic()) {
        // The rail and its node
        Box(Modifier.width(28.dp).fillMaxHeight(), contentAlignment = Alignment.TopCenter) {
            Box(Modifier.width(2.dp).fillMaxHeight().background(c.line))
            GuardianBlob(
                if (warn) Blob.Burst else Blob.Cookie,
                Modifier.padding(top = if (warn) 10.dp else 15.dp).size(if (warn) 26.dp else 16.dp),
                radius = 80f,
                color = if (warn) c.end else c.accentC,
                stroke = if (warn) null else c.ringc,
                strokeUnits = 12f,
            )
        }
        Column(Modifier.weight(1f).padding(start = 12.dp, bottom = 6.dp)) {
            Column(
                Modifier
                    .fillMaxWidth()
                    .then(
                        if (warn) {
                            Modifier.press(onToggle).semantics { stateDescription = if (open) expanded else collapsed }
                        } else {
                            Modifier
                        }
                    )
                    .padding(vertical = 10.dp),
                verticalArrangement = Arrangement.spacedBy(5.dp),
            ) {
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.Bottom) {
                    Text(who, style = TextStyle(fontSize = 16.sp, fontWeight = FontWeight.ExtraBold), color = c.ink, maxLines = 1, overflow = TextOverflow.Ellipsis, modifier = Modifier.weight(1f, fill = false))
                    Text(clockTime(record.endedAtMs, locale), style = TextStyle(fontSize = 12.sp), color = c.faint, modifier = Modifier.padding(start = 8.dp))
                }
                Text(
                    line,
                    style = TextStyle(fontSize = 14.sp, lineHeight = 19.6.sp, fontWeight = if (warn) FontWeight.SemiBold else FontWeight.Normal),
                    color = if (warn) c.head else c.faint,
                )
                if (warn) {
                    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp), modifier = Modifier.padding(top = 2.dp)) {
                        Box(Modifier.weight(1f).height(4.dp).clip(RoundedCornerShape(2.dp)).background(c.surface2)) {
                            Box(Modifier.fillMaxWidth(fuseFraction(record)).height(4.dp).clip(RoundedCornerShape(2.dp)).background(c.end))
                        }
                        Text(
                            when (record.outcome) {
                                CallOutcome.Kept -> stringResource(R.string.sb_rec_kept_short)
                                CallOutcome.CallerLeft -> stringResource(R.string.sb_rec_secs_caller, record.secondsToEnd.toInt())
                                else -> stringResource(R.string.sb_rec_secs, record.secondsToEnd.toInt())
                            },
                            style = TextStyle(fontSize = 12.sp, fontWeight = FontWeight.ExtraBold),
                            color = c.head,
                        )
                    }
                }
            }
            AnimatedVisibility(open, enter = fadeIn() + expandVertically(), exit = fadeOut() + shrinkVertically()) {
                Column(
                    Modifier.padding(bottom = 8.dp).fillMaxWidth().clip(RoundedCornerShape(22.dp)).background(c.surface2).padding(14.dp),
                    verticalArrangement = Arrangement.spacedBy(10.dp),
                ) {
                    Body(
                        stringResource(
                            when (record.type) {
                                RequestType.OtpShare -> R.string.sb_rec_detail_otp
                                RequestType.PinReceive -> R.string.sb_rec_detail_pin
                                else -> R.string.sb_rec_detail_qr
                            }
                        ),
                        15.sp,
                        color = c.head,
                        weight = FontWeight.Bold,
                    )
                    Body(stringResource(if (record.type == RequestType.OtpShare) R.string.sb_truth_otp else R.string.sb_truth_receive), 14.sp)
                    FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        SpellButton(stringResource(R.string.sb_report), onReport, background = c.end, content = c.onEnd, height = 40.dp, radius = 14.dp, fontSize = 14.sp)
                        SpellButton(stringResource(R.string.sb_block), onNotBuilt, background = c.card, content = c.ink, border = c.line, height = 40.dp, radius = 14.dp, fontSize = 14.sp)
                        SpellButton(stringResource(R.string.sb_tell, DemoPeople.trusted.name), onNotBuilt, background = c.card, content = c.ink, border = c.line, height = 40.dp, radius = 14.dp, fontSize = 14.sp)
                    }
                    Text(
                        stringResource(R.string.sb_help_link),
                        style = TextStyle(fontSize = 14.sp, fontWeight = FontWeight.Bold),
                        color = c.accent,
                        modifier = Modifier.press(onOpenRecovery).padding(vertical = 2.dp),
                    )
                }
            }
        }
    }
}

/** Lets the timeline rail stretch to the row's height. */
private fun Modifier.heightInIntrinsic(): Modifier = this.then(Modifier.height(androidx.compose.foundation.layout.IntrinsicSize.Min))

/** "4:32" */
fun clock(seconds: Long): String = "%d:%02d".format(seconds / 60, seconds % 60)

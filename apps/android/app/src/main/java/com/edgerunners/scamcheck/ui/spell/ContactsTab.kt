package com.edgerunners.scamcheck.ui.spell

import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.ChevronLeft
import androidx.compose.material.icons.outlined.Lock
import androidx.compose.material.icons.outlined.Search
import androidx.compose.material.icons.outlined.Shield
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.scale
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.PathEffect
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.drawscope.rotate
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.clearAndSetSemantics
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.selected
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.edgerunners.scamcheck.R
import com.edgerunners.scamcheck.ui.giveSpec
import com.edgerunners.scamcheck.ui.theme.Spell
import kotlin.math.PI
import kotlin.math.cos
import kotlin.math.sin

// DEMO-FAKE: Contacts and Your circle show sample people (DemoPeople). Nothing here reads the
// phone's contacts or reaches a backend; every action says so with a toast.

/** Contacts: the phone's contacts, with your circle pinned on top. */
@Composable
fun ContactsTab(
    query: String,
    onQuery: (String) -> Unit,
    onOpenCircle: (String) -> Unit,
    onOpenContact: (String) -> Unit,
) {
    val c = Spell.colors
    Column(verticalArrangement = Arrangement.spacedBy(16.dp)) {
        SearchField(query, onQuery)

        if (query.isBlank()) {
            Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.Bottom) {
                    Eyebrow(stringResource(R.string.sb_your_circle), color = c.faint)
                    Text(
                        stringResource(R.string.sb_see_circle),
                        style = TextStyle(fontSize = 13.sp, fontWeight = FontWeight.ExtraBold),
                        color = c.accent,
                        modifier = Modifier.press({ onOpenCircle(DemoPeople.PROTECTED_ID) }),
                    )
                }
                Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                    CircleStripItem(DemoPeople.protectedPerson.name, "M", c.accentC, c.onAccentC, badge = true) { onOpenCircle(DemoPeople.PROTECTED_ID) }
                    CircleStripItem(DemoPeople.trusted.name, "A", c.tert, c.onTert, badge = false) { onOpenCircle(DemoPeople.TRUSTED_ID) }
                    CircleStripItem(stringResource(R.string.sb_add), "+", c.bg, c.faint, badge = false, add = true) { onOpenCircle(CircleSel.AddOut) }
                }
            }
        }

        val groups = DemoPeople.search(query)
        Column {
            groups.forEach { (letter, people) ->
                Display(letter.toString(), 20f, color = c.accent, lineHeight = 1f, modifier = Modifier.padding(start = 2.dp, top = 12.dp, bottom = 6.dp))
                people.forEach { p ->
                    val tone = toneFor(p)
                    Row(
                        Modifier.fillMaxWidth().press({ onOpenContact(p.id) }).padding(vertical = 8.dp),
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(14.dp),
                    ) {
                        Bubble(p.name.take(1), 44.dp, background = tone.first, content = tone.second, ring = if (p.circle != null) c.ringc else null, fontSize = 19.sp)
                        Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                                Text(p.name, style = TextStyle(fontSize = 16.sp, fontWeight = FontWeight.Bold), color = c.ink)
                                if (p.onApp) {
                                    Icon(Icons.Outlined.Shield, contentDescription = stringResource(R.string.sb_uses_app_a11y), tint = c.accent, modifier = Modifier.size(14.dp))
                                }
                            }
                            Text(contactSub(p), style = TextStyle(fontSize = 13.sp), color = c.faint)
                        }
                    }
                }
            }
            if (groups.isEmpty()) {
                Body(stringResource(R.string.sb_no_results), 15.sp, color = c.faint, lineHeight = 1.5f, modifier = Modifier.padding(vertical = 18.dp, horizontal = 2.dp))
            }
        }

        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.padding(horizontal = 2.dp)) {
            Icon(Icons.Outlined.Shield, contentDescription = null, tint = c.accent, modifier = Modifier.size(14.dp))
            Text(stringResource(R.string.sb_uses_app), style = TextStyle(fontSize = 12.sp), color = c.faint)
        }
    }
}

@Composable
fun contactSub(p: DemoContact): String {
    val prefix = when {
        p.circle != null -> stringResource(R.string.sb_in_circle_prefix)
        p.relation != null -> stringResource(p.relation)
        else -> null
    }
    return if (prefix != null) "$prefix · ${p.number}" else p.number
}

@Composable
private fun toneFor(p: DemoContact): Pair<Color, Color> {
    val c = Spell.colors
    val tones = listOf(c.accentC to c.onAccentC, c.tert to c.onTert, c.surface2 to c.ink)
    return tones[DemoPeople.contacts.indexOf(p).coerceAtLeast(0) % 3]
}

@Composable
private fun SearchField(query: String, onQuery: (String) -> Unit) {
    val c = Spell.colors
    val shape = RoundedCornerShape(26.dp)
    Row(
        Modifier.fillMaxWidth().heightIn(min = 52.dp).clip(shape).background(c.card).border(1.dp, c.line, shape).padding(horizontal = 16.dp),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(10.dp),
    ) {
        Icon(Icons.Outlined.Search, contentDescription = null, tint = c.faint, modifier = Modifier.size(20.dp))
        val hint = stringResource(R.string.sb_search_hint)
        Box(Modifier.weight(1f)) {
            if (query.isEmpty()) Text(hint, style = TextStyle(fontSize = 16.sp), color = c.faint)
            BasicTextField(
                value = query,
                onValueChange = onQuery,
                singleLine = true,
                textStyle = TextStyle(fontSize = 16.sp, color = c.ink),
                cursorBrush = SolidColor(c.accent),
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Text, imeAction = ImeAction.Search),
                modifier = Modifier.fillMaxWidth().semantics { contentDescription = hint },
            )
        }
    }
}

@Composable
private fun CircleStripItem(name: String, initial: String, bg: Color, fg: Color, badge: Boolean, add: Boolean = false, onClick: () -> Unit) {
    val c = Spell.colors
    val label = if (add) stringResource(R.string.sb_add_circle_a11y) else stringResource(R.string.sb_circle_a11y, name)
    Column(
        Modifier.width(68.dp).press(onClick, label = label).semantics(mergeDescendants = true) { contentDescription = label },
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(6.dp),
    ) {
        Box {
            Bubble(initial, 58.dp, background = bg, content = fg, dashed = add, ring = if (add) null else if (badge) c.end else c.ringc)
            if (badge) {
                GuardianBlob(Blob.Burst, Modifier.size(20.dp).align(Alignment.TopEnd).offset(3.dp, (-3).dp), radius = 80f, color = c.end, stroke = c.bg, strokeUnits = 14f, spin = Spin.Fast)
            }
        }
        Text(name, style = TextStyle(fontSize = 12.sp, fontWeight = FontWeight.Bold), color = c.ink)
    }
}

// ---------- Your circle ----------

/** Who is picked on the circle: a person's id, or one of the two empty "add" slots. */
object CircleSel {
    const val AddIn = "addIn"
    const val AddOut = "addOut"
}

private data class Orbit(val id: String, val name: String, val role: Int, val r: Float, val a: Float, val initial: String, val add: Boolean, val badge: Boolean)

private val orbits = listOf(
    Orbit(DemoPeople.TRUSTED_ID, "Arjun", R.string.sb_role_brother, 96f, -55f, "A", add = false, badge = false),
    Orbit(CircleSel.AddIn, "", R.string.sb_role_to_tell, 96f, 150f, "+", add = true, badge = false),
    Orbit(DemoPeople.PROTECTED_ID, "Mum", R.string.sb_scam_check_on_short, 138f, 205f, "M", add = false, badge = true),
    Orbit(CircleSel.AddOut, "", R.string.sb_role_a_parent, 138f, 35f, "+", add = true, badge = false),
)

/** You at the centre; the people who look out for you inside, the people you look out for outside. */
@Composable
fun CircleScreen(selected: String, onSelect: (String) -> Unit, onBack: () -> Unit, onNotBuilt: () -> Unit) {
    val c = Spell.colors
    val brush = guardianBrush()
    val trusted = DemoPeople.trusted.name
    val protected = DemoPeople.protectedPerson.name
    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Row(
            Modifier.clip(RoundedCornerShape(999.dp)).background(c.surface2).press(onBack).heightIn(min = 38.dp).padding(start = 10.dp, end = 14.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(6.dp),
        ) {
            Icon(Icons.Outlined.ChevronLeft, contentDescription = null, tint = c.ink, modifier = Modifier.size(18.dp))
            Text(stringResource(R.string.sb_tab_contacts), style = TextStyle(fontSize = 14.sp, fontWeight = FontWeight.Bold), color = c.ink)
        }
        Display(stringResource(R.string.sb_circle_title, trusted, protected), 28f, lineHeight = 1.1f, modifier = Modifier.widthIn(max = 320.dp))

        // The orbit
        Box(Modifier.align(Alignment.CenterHorizontally).size(320.dp, 310.dp)) {
            val seconds = rememberSeconds()
            Canvas(Modifier.fillMaxSize().clearAndSetSemantics { }) {
                val u = size.width / 320f
                val centre = Offset(160f * u, 150f * u)
                drawCircle(c.ringc, 96f * u, centre, style = Stroke(1.5f * u))
                rotate((360f * seconds.value / 120f) % 360f, centre) {
                    drawCircle(c.ringc, 138f * u, centre, style = Stroke(1.5f * u, cap = StrokeCap.Round, pathEffect = PathEffect.dashPathEffect(floatArrayOf(2f * u, 8f * u))))
                }
                orbits.firstOrNull { it.id == selected }?.let { o ->
                    val rad = o.a * PI.toFloat() / 180f
                    val dir = Offset(cos(rad), sin(rad))
                    val bubble = if (o.add) 44f else 56f
                    drawLine(c.accent, centre + dir * (46f * u), centre + dir * ((o.r - bubble / 2f - 6f) * u), 2.5f * u, StrokeCap.Round)
                }
            }
            Box(Modifier.offset(116.dp, 106.dp).size(88.dp), contentAlignment = Alignment.Center) {
                GuardianBlob(Blob.Cookie, Modifier.fillMaxSize(), radius = 74f, fill = brush, breathe = true)
                Text(stringResource(R.string.sb_you), style = TextStyle(fontSize = 14.sp, fontWeight = FontWeight.ExtraBold, letterSpacing = 0.5.sp), color = c.onGuardian)
            }
            orbits.forEach { o ->
                val rad = o.a * PI.toFloat() / 180f
                val x = 160f + o.r * cos(rad)
                val y = 150f + o.r * sin(rad)
                val bubble = if (o.add) 44 else 56
                val picked = selected == o.id
                val scale by animateFloatAsState(if (picked) 1.08f else 1f, giveSpec(), label = "orbit")
                val name = when (o.id) {
                    CircleSel.AddIn -> stringResource(R.string.sb_add)
                    CircleSel.AddOut -> stringResource(R.string.sb_role_protect)
                    else -> o.name
                }
                val role = stringResource(o.role)
                val a11y = when (o.id) {
                    CircleSel.AddIn -> stringResource(R.string.sb_add_tell_title)
                    CircleSel.AddOut -> stringResource(R.string.sb_protect_title)
                    else -> "$name, $role"
                }
                Column(
                    Modifier
                        .offset((x - 44f).dp, (y - bubble / 2f).dp)
                        .width(88.dp)
                        .scale(scale)
                        .press({ onSelect(o.id) })
                        .semantics(mergeDescendants = true) {
                            contentDescription = a11y
                            this.selected = picked
                        },
                    horizontalAlignment = Alignment.CenterHorizontally,
                    verticalArrangement = Arrangement.spacedBy(2.dp),
                ) {
                    Box(Modifier.padding(bottom = 4.dp)) {
                        val tone = if (o.id == DemoPeople.TRUSTED_ID) c.tert to c.onTert else c.accentC to c.onAccentC
                        Bubble(o.initial, bubble.dp, background = tone.first, content = tone.second, dashed = o.add, ring = if (picked) c.accent else null)
                        if (o.badge) {
                            GuardianBlob(Blob.Burst, Modifier.size(20.dp).align(Alignment.TopEnd).offset(4.dp, (-4).dp), radius = 80f, color = c.end, stroke = c.bg, strokeUnits = 14f, spin = Spin.Fast)
                        }
                    }
                    Text(name, style = TextStyle(fontSize = 13.sp, fontWeight = FontWeight.ExtraBold, lineHeight = 15.6.sp), color = c.ink)
                    Text(role, style = TextStyle(fontSize = 11.sp, lineHeight = 13.sp), color = c.faint)
                }
            }
        }

        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(16.dp, Alignment.CenterHorizontally)) {
            Legend(dashed = false, label = stringResource(R.string.sb_told_about))
            Legend(dashed = true, label = stringResource(R.string.sb_look_out_for))
        }

        // The person you picked
        Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
            Hairline()
            Eyebrow(
                stringResource(
                    when (selected) {
                        DemoPeople.PROTECTED_ID -> R.string.sb_circ_eyebrow_mum
                        DemoPeople.TRUSTED_ID -> R.string.sb_rel_told
                        CircleSel.AddIn -> R.string.sb_circ_eyebrow_in
                        else -> R.string.sb_circ_eyebrow_out
                    }
                ),
                modifier = Modifier.padding(top = 6.dp),
            )
            when (selected) {
                DemoPeople.PROTECTED_ID -> {
                    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                        Display(protected, 30f, lineHeight = 1f)
                        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                            LiveDot(active = true)
                            Text(stringResource(R.string.sb_scam_check_on_short), style = TextStyle(fontSize = 13.sp, fontWeight = FontWeight.Bold), color = c.faint)
                        }
                    }
                    Text(stringResource(R.string.sb_mum_story), style = TextStyle(fontSize = 17.sp, lineHeight = 23.sp, fontWeight = FontWeight.Bold), color = c.head)
                    Fuse(0.47f)
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                        Text(stringResource(R.string.sb_mum_fuse_left), style = TextStyle(fontSize = 12.sp, fontWeight = FontWeight.SemiBold), color = c.faint)
                        Text(stringResource(R.string.sb_mum_fuse_right), style = TextStyle(fontSize = 12.sp, fontWeight = FontWeight.SemiBold), color = c.head)
                    }
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.padding(top = 4.dp)) {
                        SpellButton(stringResource(R.string.sb_call_name, protected), onNotBuilt, height = 46.dp, radius = 16.dp, fontSize = 15.sp)
                        SpellButton(stringResource(R.string.sb_her_week), onNotBuilt, background = c.surface2, content = c.ink, height = 46.dp, radius = 16.dp, fontSize = 15.sp)
                    }
                }
                DemoPeople.TRUSTED_ID -> {
                    Display(trusted, 30f, lineHeight = 1f)
                    Body(stringResource(R.string.sb_arjun_body), 15.sp)
                    Column(
                        Modifier.widthIn(max = 300.dp).clip(RoundedCornerShape(20.dp, 20.dp, 20.dp, 6.dp)).background(c.surface2).padding(horizontal = 14.dp, vertical = 12.dp),
                        verticalArrangement = Arrangement.spacedBy(4.dp),
                    ) {
                        Eyebrow(stringResource(R.string.sb_would_get, trusted), color = c.faint)
                        Body(stringResource(R.string.sb_arjun_text), 14.sp, color = c.ink)
                    }
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.padding(top = 4.dp)) {
                        SpellButton(stringResource(R.string.sb_send_test), onNotBuilt, height = 46.dp, radius = 16.dp, fontSize = 15.sp)
                        SpellButton(stringResource(R.string.sb_remove), onNotBuilt, background = c.surface2, content = c.ink, height = 46.dp, radius = 16.dp, fontSize = 15.sp)
                    }
                }
                CircleSel.AddIn -> {
                    Display(stringResource(R.string.sb_add_tell_title), 26f, lineHeight = 1.1f)
                    Body(stringResource(R.string.sb_add_tell_body), 15.sp)
                    SpellButton(stringResource(R.string.sb_choose_contact), onNotBuilt, height = 46.dp, radius = 16.dp, fontSize = 15.sp)
                }
                else -> {
                    Display(stringResource(R.string.sb_protect_title), 26f, lineHeight = 1.1f)
                    Body(stringResource(R.string.sb_protect_body), 15.sp)
                    SpellButton(stringResource(R.string.sb_show_code), onNotBuilt, height = 46.dp, radius = 16.dp, fontSize = 15.sp)
                }
            }
        }

        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp), modifier = Modifier.padding(start = 4.dp, end = 4.dp, top = 8.dp)) {
            Icon(Icons.Outlined.Lock, contentDescription = null, tint = c.faint, modifier = Modifier.size(18.dp))
            Body(stringResource(R.string.sb_circle_privacy), 13.sp, color = c.faint, lineHeight = 1.4f)
        }
    }
}

@Composable
private fun Legend(dashed: Boolean, label: String) {
    val c = Spell.colors
    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.dp)) {
        Canvas(Modifier.size(18.dp, 2.dp)) {
            drawLine(
                c.ringc, Offset(0f, size.height / 2), Offset(size.width, size.height / 2), 1.5.dp.toPx(),
                pathEffect = if (dashed) PathEffect.dashPathEffect(floatArrayOf(3.dp.toPx(), 2.dp.toPx())) else null,
            )
        }
        Text(label, style = TextStyle(fontSize = 12.sp), color = c.faint)
    }
}

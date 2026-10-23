package com.edgerunners.scamcheck.ui.spell

import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.safeDrawingPadding
import androidx.compose.animation.animateColorAsState
import androidx.compose.animation.core.Animatable
import androidx.compose.animation.core.CubicBezierEasing
import androidx.compose.animation.core.animateDpAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.selection.selectable
import androidx.compose.foundation.selection.selectableGroup
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.Dialpad
import androidx.compose.material.icons.outlined.PersonOutline
import androidx.compose.material.icons.outlined.Schedule
import androidx.compose.material.icons.outlined.Shield
import androidx.compose.material.icons.outlined.Tune
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.key
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.clearAndSetSemantics
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.edgerunners.scamcheck.R
import com.edgerunners.scamcheck.ui.theme.LocalReduceMotion
import com.edgerunners.scamcheck.ui.theme.Spell
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlin.math.hypot
import kotlin.math.max

/** Three tabs, one job each. Order matches the nav bar. */
enum class Tab { Recents, Home, Contacts }

private val WipeEasing = CubicBezierEasing(0.4f, 0f, 0.2f, 1f)
private val NavEasing = CubicBezierEasing(0.3f, 1.25f, 0.5f, 1f)

/**
 * The tabbed part of the app: the protection field behind everything, a title bar with
 * settings, the tab's content, and the floating nav bar. Switching tabs bursts the new tab's
 * colour out of the tapped button, swaps the tab under it, then fades.
 */
@Composable
fun TabsScreen(
    tab: Tab,
    circleOpen: Boolean,
    onTab: (Tab) -> Unit,
    onSettings: () -> Unit,
    onKeypad: () -> Unit,
    content: @Composable (Tab) -> Unit,
) {
    val c = Spell.colors
    val reduce = LocalReduceMotion.current
    var wipeTarget by remember { mutableStateOf<Tab?>(null) }
    var wipeRun by remember { mutableIntStateOf(0) }
    val wipe = remember { Animatable(0f) }
    LaunchedEffect(wipeRun) {
        val target = wipeTarget ?: return@LaunchedEffect
        wipe.snapTo(0f)
        launch {
            delay(320)
            onTab(target)
        }
        wipe.animateTo(1f, tween(740, easing = WipeEasing))
        wipeTarget = null
    }
    val shownTab = wipeTarget ?: tab
    val select: (Tab) -> Unit = { target ->
        when {
            wipeTarget != null -> Unit
            target == tab && !circleOpen -> Unit
            target == tab || reduce -> onTab(target)
            else -> {
                wipeTarget = target
                wipeRun++
            }
        }
    }
    val title = when {
        circleOpen -> stringResource(R.string.sb_your_circle)
        tab == Tab.Recents -> stringResource(R.string.sb_tab_recents)
        tab == Tab.Contacts -> stringResource(R.string.sb_tab_contacts)
        else -> stringResource(R.string.app_name)
    }

    Box(Modifier.fillMaxSize().background(c.bg)) {
        ProtectionField(
            when (shownTab) {
                Tab.Home -> Offset(195f, 346f)
                Tab.Recents -> Offset(380f, 60f)
                Tab.Contacts -> Offset(10f, 230f)
            },
            Modifier.fillMaxSize(),
        )
        GlowBackground(c.glow, Modifier.fillMaxSize())

        key(tab, circleOpen) {
            Column(
                Modifier.fillMaxSize().safeDrawingPadding().verticalScroll(rememberScrollState()).padding(start = 18.dp, end = 18.dp, top = 18.dp, bottom = 104.dp),
                verticalArrangement = Arrangement.spacedBy(14.dp),
            ) {
                Row(Modifier.fillMaxWidth().heightIn(min = 48.dp), verticalAlignment = Alignment.CenterVertically) {
                    Row(Modifier.weight(1f), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                        Display(title, 24f, lineHeight = 1.1f)
                        if (c.premium && tab == Tab.Home && !circleOpen) {
                            Text(
                                stringResource(R.string.sb_premium),
                                style = TextStyle(fontSize = 10.sp, fontWeight = FontWeight.Bold, letterSpacing = 2.2.sp),
                                color = c.eyebrow,
                                modifier = Modifier.border(1.dp, c.eyebrow.copy(alpha = 0.5f), RoundedCornerShape(999.dp)).padding(horizontal = 8.dp, vertical = 4.dp),
                            )
                        }
                    }
                    Box(
                        Modifier.size(48.dp).clip(RoundedCornerShape(16.dp)).background(c.surface2).border(1.dp, c.line, RoundedCornerShape(16.dp))
                            .press(onSettings, label = stringResource(R.string.sb_settings)),
                        contentAlignment = Alignment.Center,
                    ) { Icon(Icons.Outlined.Tune, contentDescription = stringResource(R.string.sb_settings), tint = c.ink, modifier = Modifier.size(22.dp)) }
                }
                content(tab)
            }
        }

        if (tab != Tab.Home) {
            Box(
                Modifier
                    .align(Alignment.BottomEnd)
                    .navigationBarsPadding()
                    .padding(end = 18.dp, bottom = 102.dp)
                    .drawBehind { drawRoundRect(c.shadow, topLeft = Offset(0f, 12.dp.toPx()), size = size, cornerRadius = androidx.compose.ui.geometry.CornerRadius(22.dp.toPx())) }
                    .size(64.dp)
                    .clip(RoundedCornerShape(22.dp))
                    .background(c.accent)
                    .press(onKeypad, label = stringResource(R.string.sb_keypad)),
                contentAlignment = Alignment.Center,
            ) { Icon(Icons.Outlined.Dialpad, contentDescription = stringResource(R.string.sb_keypad), tint = c.onAccent, modifier = Modifier.size(26.dp)) }
        }

        // The colour burst between tabs
        wipeTarget?.let { target -> WipeOverlay(target, wipe.value) }

        NavBar(shownTab, select, Modifier.align(Alignment.BottomCenter))
    }
}

@Composable
private fun WipeOverlay(target: Tab, p: Float) {
    val c = Spell.colors
    val i = target.ordinal
    val color = c.wipe[i]
    val title = stringResource(
        when (target) {
            Tab.Recents -> R.string.sb_tab_recents
            Tab.Home -> R.string.sb_tab_home
            Tab.Contacts -> R.string.sb_tab_contacts
        }
    )
    val overlayAlpha = if (p < 0.62f) 1f else 1f - (p - 0.62f) / 0.38f
    val titleAlpha = when {
        p < 0.26f -> 0f
        p < 0.46f -> (p - 0.26f) / 0.2f
        p < 0.64f -> 1f
        else -> 1f - (p - 0.64f) / 0.36f
    }
    Box(
        Modifier
            .fillMaxSize()
            .clearAndSetSemantics { }
            .graphicsLayer { alpha = overlayAlpha }
            .drawBehind {
                val navInset = 14.dp.toPx() + 6.dp.toPx()
                val cell = (size.width - 2 * navInset) / 3f
                val centre = Offset(navInset + cell * (i + 0.5f), size.height - 14.dp.toPx() - 32.dp.toPx())
                val far = max(hypot(centre.x, centre.y), hypot(size.width - centre.x, centre.y))
                val r = far * (p / 0.44f).coerceAtMost(1f)
                drawCircle(color, r, centre)
            },
        contentAlignment = Alignment.Center,
    ) {
        Display(
            title, 44f, color = c.wipeTitle[i], lineHeight = 1f,
            modifier = Modifier.graphicsLayer {
                alpha = titleAlpha
                val rise = if (p < 0.46f) 12f * (1f - titleAlpha) else if (p > 0.64f) -8f * (1f - titleAlpha) else 0f
                translationY = rise * density
                val s = if (p < 0.46f) 0.96f + 0.04f * titleAlpha else 1f
                scaleX = s
                scaleY = s
            },
        )
    }
}

/** The floating nav bar. A liquid pill slides to the chosen tab: the leading edge first. */
@Composable
private fun NavBar(selected: Tab, onSelect: (Tab) -> Unit, modifier: Modifier = Modifier) {
    val c = Spell.colors
    val reduce = LocalReduceMotion.current
    val index = selected.ordinal
    var previous by remember { mutableIntStateOf(index) }
    val movingRight = index > previous
    val movingLeft = index < previous
    LaunchedEffect(index) {
        delay(520)
        previous = index
    }
    val shape = RoundedCornerShape(26.dp)
    BoxWithConstraints(
        modifier
            .navigationBarsPadding()
            .padding(14.dp)
            .fillMaxWidth()
            .height(64.dp)
            .drawBehind { drawRoundRect(c.shadow.copy(alpha = c.shadow.alpha * 0.6f), topLeft = Offset(0f, 14.dp.toPx()), size = size, cornerRadius = androidx.compose.ui.geometry.CornerRadius(26.dp.toPx())) }
            .clip(shape)
            .background(c.navBg)
            .border(1.dp, c.line, shape)
            .padding(horizontal = 6.dp, vertical = 4.dp),
    ) {
        val cell = maxWidth / 3
        val left by animateDpAsState(cell * index, if (reduce) tween(0) else tween(420, delayMillis = if (movingRight) 100 else 0, easing = NavEasing), label = "navLeft")
        val right by animateDpAsState(cell * (index + 1), if (reduce) tween(0) else tween(420, delayMillis = if (movingLeft) 100 else 0, easing = NavEasing), label = "navRight")
        val pill by animateColorAsState(c.indicator[index], tween(350), label = "navColor")
        Box(
            Modifier
                .offset(x = left)
                .width((right - left).coerceAtLeast(0.dp))
                .fillMaxHeight()
                .clip(RoundedCornerShape(21.dp))
                .background(pill)
        )
        Row(Modifier.fillMaxSize().selectableGroup()) {
            NavItem(Icons.Outlined.Schedule, stringResource(R.string.sb_tab_recents), selected == Tab.Recents, c.onIndicator[index]) { onSelect(Tab.Recents) }
            NavItem(Icons.Outlined.Shield, stringResource(R.string.sb_tab_home), selected == Tab.Home, c.onIndicator[index]) { onSelect(Tab.Home) }
            NavItem(Icons.Outlined.PersonOutline, stringResource(R.string.sb_tab_contacts), selected == Tab.Contacts, c.onIndicator[index]) { onSelect(Tab.Contacts) }
        }
    }
}

@Composable
private fun androidx.compose.foundation.layout.RowScope.NavItem(icon: ImageVector, label: String, on: Boolean, onColor: androidx.compose.ui.graphics.Color, onClick: () -> Unit) {
    val c = Spell.colors
    val reduce = LocalReduceMotion.current
    val tint by animateColorAsState(if (on) onColor else c.faint, tween(300), label = "navTint")
    val pop = remember { Animatable(1f) }
    LaunchedEffect(on) {
        if (on && !reduce) {
            pop.snapTo(0.72f)
            pop.animateTo(1.12f, tween(300))
            pop.animateTo(1f, tween(200))
        }
    }
    Column(
        Modifier
            .weight(1f)
            .fillMaxHeight()
            .selectable(selected = on, role = Role.Tab, onClick = onClick),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(2.dp, Alignment.CenterVertically),
    ) {
        Icon(icon, contentDescription = null, tint = tint, modifier = Modifier.size(22.dp).graphicsLayer { scaleX = pop.value; scaleY = pop.value })
        Text(label, style = TextStyle(fontSize = 11.5.sp, fontWeight = FontWeight.Bold), color = tint)
    }
}

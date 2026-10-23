package com.edgerunners.scamcheck

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.edgerunners.scamcheck.ui.AppRoot
import com.edgerunners.scamcheck.ui.theme.EdgerunnersTheme
import com.edgerunners.scamcheck.ui.theme.editionFrom

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val controller = (application as EdgerunnersApp).container.controller
        setContent {
            val state = controller.state.collectAsStateWithLifecycle().value
            EdgerunnersTheme(language = state.settings.language, edition = editionFrom(BuildConfig.UI_EDITION)) {
                AppRoot(state = state, controller = controller)
            }
        }
    }
}

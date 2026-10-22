package dev.edgerunners.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import dev.edgerunners.contracts.RequestType
import dev.edgerunners.contracts.WarningEvent

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent { MaterialTheme { CallScreen() } }
    }
}

@Composable
private fun CallScreen(event: WarningEvent? = null) {
    Surface(modifier = Modifier.fillMaxSize()) {
        Column(
            modifier = Modifier.padding(24.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            Text(stringResource(R.string.app_name), style = MaterialTheme.typography.headlineLarge)
            Text(stringResource(R.string.protection_unavailable))
            Text(stringResource(R.string.setup_required))
            if (event != null) {
                val warning = when (event.request_type) {
                    RequestType.OTP_SHARE -> R.string.warning_otp
                    RequestType.PIN_RECEIVE -> R.string.warning_pin
                    RequestType.QR_RECEIVE -> R.string.warning_qr
                    RequestType.NONE -> null
                }
                if (warning != null) Text(stringResource(warning))
            }
        }
    }
}

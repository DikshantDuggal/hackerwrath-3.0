import java.util.Properties

plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.android)
    alias(libs.plugins.kotlin.compose)
    alias(libs.plugins.kotlin.serialization)
}

val localProps = Properties().apply {
    val file = rootProject.file("local.properties")
    if (file.exists()) file.inputStream().use { load(it) }
}

fun localProp(name: String, default: String = ""): String = localProps.getProperty(name)?.trim() ?: default

android {
    namespace = "com.edgerunners.scamcheck"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.edgerunners.scamcheck"
        minSdk = 25
        targetSdk = 35
        versionCode = 1
        versionName = "0.1.0"

        buildConfigField("String", "API_BASE_URL", "\"${localProp("api.baseUrl", "http://10.0.2.2:8000")}\"")
        buildConfigField("boolean", "DEMO_ENABLED", localProp("demo.enabled", "true"))
        buildConfigField("String", "UI_EDITION", "\"${localProp("ui.edition", "standard")}\"")
        buildConfigField("String", "FIREBASE_APP_ID", "\"${localProp("firebase.appId")}\"")
        buildConfigField("String", "FIREBASE_API_KEY", "\"${localProp("firebase.apiKey")}\"")
        buildConfigField("String", "FIREBASE_PROJECT_ID", "\"${localProp("firebase.projectId")}\"")
        buildConfigField("String", "FIREBASE_SENDER_ID", "\"${localProp("firebase.senderId")}\"")
    }

    buildTypes {
        debug {
            manifestPlaceholders["usesCleartextTraffic"] = "true"
        }
        release {
            isMinifyEnabled = false
            manifestPlaceholders["usesCleartextTraffic"] = "false"
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions {
        jvmTarget = "17"
    }
    buildFeatures {
        compose = true
        buildConfig = true
    }
}

dependencies {
    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.lifecycle.runtime.compose)
    implementation(libs.androidx.lifecycle.process)
    implementation(libs.androidx.activity.compose)

    implementation(platform(libs.compose.bom))
    implementation(libs.compose.ui)
    implementation(libs.compose.foundation)
    implementation(libs.compose.animation)
    implementation(libs.compose.material3)
    implementation(libs.compose.material.icons.extended)
    implementation(libs.compose.ui.tooling.preview)
    debugImplementation(libs.compose.ui.tooling)

    implementation(libs.okhttp)
    implementation(libs.kotlinx.serialization.json)
    implementation(libs.kotlinx.coroutines.android)

    implementation(libs.twilio.voice)
    implementation(libs.livekit.android)
    implementation(libs.firebase.messaging)

    testImplementation(libs.junit)
}

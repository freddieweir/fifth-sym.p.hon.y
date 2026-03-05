"""
Orchestrator Modules
Core functionality for the Python Orchestrator
"""

__all__ = [
    "AudioTTS",
    "AudioTTSError",
    "OnePasswordManager",
    "VoiceHandler",
    "VoiceListener",
    "VoiceListenerError",
    "ScriptRunner",
    "OutputTranslator",
    "ReminderSystem",
    # YouTube Subscriptions
    "YouTubeAuth",
    "SubscriptionFetcher",
    "CategoryMapper",
    "GlanceConfigGenerator",
    "InvidiousClient",
    "Channel",
    "CategoryGroup",
    "GlancePage",
    "InvidiousSyncResult",
]

_LAZY_IMPORTS: dict[str, tuple[str, str]] = {
    "AudioTTS": (".audio_tts", "AudioTTS"),
    "AudioTTSError": (".audio_tts", "AudioTTSError"),
    "OnePasswordManager": (".onepassword_manager", "OnePasswordManager"),
    "OutputTranslator": (".output_translator", "OutputTranslator"),
    "ReminderSystem": (".reminder_system", "ReminderSystem"),
    "ScriptRunner": (".script_runner", "ScriptRunner"),
    "VoiceHandler": (".voice_handler", "VoiceHandler"),
    "VoiceListener": (".voice_listener", "VoiceListener"),
    "VoiceListenerError": (".voice_listener", "VoiceListenerError"),
    "Channel": (".youtube_models", "Channel"),
    "CategoryGroup": (".youtube_models", "CategoryGroup"),
    "GlancePage": (".youtube_models", "GlancePage"),
    "CategoryMapper": (".youtube_subscriptions", "CategoryMapper"),
    "GlanceConfigGenerator": (".youtube_subscriptions", "GlanceConfigGenerator"),
    "InvidiousClient": (".youtube_subscriptions", "InvidiousClient"),
    "SubscriptionFetcher": (".youtube_subscriptions", "SubscriptionFetcher"),
    "YouTubeAuth": (".youtube_subscriptions", "YouTubeAuth"),
    "InvidiousSyncResult": (".youtube_models", "InvidiousSyncResult"),
}


def __getattr__(name: str):
    if name in _LAZY_IMPORTS:
        module_path, attr = _LAZY_IMPORTS[name]
        from importlib import import_module

        module = import_module(module_path, __package__)
        value = getattr(module, attr)
        globals()[name] = value  # cache for subsequent access
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

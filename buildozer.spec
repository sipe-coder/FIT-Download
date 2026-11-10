[app]
title = FIT Download
package.name = fitdownload
package.domain = org
source.dir = .
source.include_exts = py,png,jpg,kv,atlas
source.include_patterns = *
version = 1.0
requirements = hostpython3==3.11.5,python3==3.11.5,kivy==2.3.0,pyjnius,android,requests,urllib3,idna,certifi,charset-normalizer,yt-dlp
orientation = portrait
fullscreen = 0
android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE,POST_NOTIFICATIONS
android.api = 33
android.minapi = 21
android.ndk_api = 21
android.ndk = 25b
android.accept_sdk_license = True
android.request_legacy_external_storage = True
android.app_name = FIT Download
android.enable_androidx = False

[buildozer]
log_level = 2
warn_on_root = 1
